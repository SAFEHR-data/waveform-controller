import argparse
import functools
import json
import logging
from decimal import Decimal
from pathlib import Path
from typing import Any, Optional

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import settings

from locations import (
    CSV_PATTERN,
    ORIGINAL_PARQUET_PATTERN,
    PSEUDONYMISED_PARQUET_PATTERN,
)
from .hashing import do_hash


def _is_missing_csv_cell(x: Any) -> bool:
    return x is None or x == "" or pd.isna(x)


def parse_numeric_values(x: Any) -> Optional[list[Decimal]]:
    """Parse a JSON array of numbers from CSV into Decimals; empty cell -> None."""
    if _is_missing_csv_cell(x):
        return None
    # Not sure if this is the most efficient way. Might be able to do something with DecimalArray?
    return list(json.loads(x, parse_float=Decimal, parse_int=Decimal))


def parse_string_values(x: Any) -> Optional[list[str]]:
    """Parse a JSON array of strings from CSV; empty cell -> None."""
    if _is_missing_csv_cell(x):
        return None
    return [str(i) for i in json.loads(x)]


def pseudon_cli():
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument("--csv", type=Path)
    args = arg_parser.parse_args()
    csv_to_parquets(args.csv)


def csv_to_parquets(
    *,
    date_str: str,
    original_csn: str,
    hashed_csn: str,
    variable_id: str,
    channel_id: str,
    units: str,
) -> None:
    """Convert CSV data (with full identifiers) to two versions in parquet
    format:

    - full identifiers (intended for debugging, NOT to be exported to DSH)
    - pseudonymised identifiers (for export to DSH)

    This is a privacy-sensitive area of code. The two versions of the parquet file
    have different names (hashed vs unhashed CSN). Unhashed CSNs must not appear in
    the uploaded files.
    It might have been more convenient (esp for CLI usage) to pass in the CSV path directly,
    then parse out the sections here to generate both output file names,
    but that is going to be lead to fragile assumptions that eg. element "1" is always the CSN.

    Instead, pass in individual named components of the file path.
    """
    # will pick up the logger config defined in the snakemake job (ie. log to file)
    logger = logging.getLogger(__name__)

    csv_path = Path(
        str(CSV_PATTERN).format(
            date=date_str,
            csn=original_csn,
            variable_id=variable_id,
            channel_id=channel_id,
            units=units,
        )
    )
    original_parquet_path = Path(
        str(ORIGINAL_PARQUET_PATTERN).format(
            date=date_str,
            csn=original_csn,
            variable_id=variable_id,
            channel_id=channel_id,
            units=units,
        )
    )
    # it's in the csv_path and original_parquet_path, but at least nowhere else!
    del original_csn

    logger.info("Turning CSV %s to parquets", csv_path)
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    original_parquet_path.parent.mkdir(parents=True, exist_ok=True)
    # sampling_rate is null in low-frequency rows. Value columns are
    # JSON arrays; exactly one of numeric_values / string_values is populated per row.
    df = pd.read_csv(
        str(csv_path),
        dtype={
            "csn": str,
            "mrn": str,
            "source_variable_id": str,
            "source_channel_id": str,
            "units": str,
            "sampling_rate": "Int32",
            "timestamp": float,
            "location": str,
            "numeric_values": str,
            "string_values": str,
        },
        header=0,  # the first line is always the header
    )

    df["numeric_values"] = df["numeric_values"].apply(parse_numeric_values)
    df["string_values"] = df["string_values"].apply(parse_string_values)

    # CSV row order follows RabbitMQ arrival, which is not guaranteed chronological.
    df = df.sort_values("timestamp", kind="mergesort").reset_index(drop=True)

    # Convert pandas DataFrame to pyarrow Table with proper types
    schema = pa.schema(
        [
            ("csn", pa.string()),
            ("mrn", pa.string()),
            ("source_variable_id", pa.string()),
            ("source_channel_id", pa.string()),
            ("units", pa.string()),
            ("sampling_rate", pa.int32()),
            ("timestamp", pa.float64()),
            ("location", pa.string()),
            # As per requirements, compactness is important here.
            # decimal32 can have a maximum of 9 significant digits and should
            # satisfy our needs, but it only exists in pyarrow >= 19.
            # We are currently tied to 18.1 because of PIXL core.
            # So for now, use decimal128 instead.
            # Not yet tested whether the specified precision
            # and scale cause it to be equivalent in size to decimal32.
            # See issue #31.
            ("numeric_values", pa.list_(pa.decimal128(9, 4))),
            ("string_values", pa.list_(pa.string())),
        ]
    )
    table = pa.Table.from_pandas(df, schema=schema, preserve_index=True)

    # mark the parquet files themselves as production or not.
    our_metadata = {"instance_name": settings.INSTANCE_NAME}

    table = add_waveform_metadata_to_table(table, our_metadata)

    pq.write_table(
        table,
        str(original_parquet_path),
        # valid values: {‘NONE’, ‘SNAPPY’, ‘GZIP’, ‘BROTLI’, ‘LZ4’, ‘ZSTD’}
        compression="zstd",
        use_dictionary=True,
        write_statistics=True,
        write_page_index=True,
        flavor="spark",
    )
    logger.info(
        "Done turning CSV %s to original parquet %s", csv_path, original_parquet_path
    )

    safe_columns = [
        "sampling_rate",
        "source_variable_id",
        "source_channel_id",
        "timestamp",
        "units",
        "numeric_values",
        "string_values",
    ]

    df = pseudonymise_relevant_columns(df, safe_columns)
    pseudon_table = pa.Table.from_pandas(df, schema=schema, preserve_index=True)

    # Use same metadata for pseudon, must not contain identifiers!
    pseudon_table = add_waveform_metadata_to_table(pseudon_table, our_metadata)

    hashed_path = Path(
        str(PSEUDONYMISED_PARQUET_PATTERN).format(
            date=date_str,
            hashed_csn=hashed_csn,
            variable_id=variable_id,
            channel_id=channel_id,
            units=units,
        )
    )
    pq.write_table(
        pseudon_table,
        str(hashed_path),
        compression="zstd",
        use_dictionary=True,
        write_statistics=True,
        write_page_index=True,
        flavor="spark",
    )
    logger.info(
        "Done turning CSV %s to pseudonymised parquet %s", csv_path, hashed_path
    )


def add_waveform_metadata_to_table(
    existing_table: pa.Table, metadata: dict[str, Any]
) -> pa.Table:
    """Replace our metadata in its entirety, leaving untouched metadata we didn't
    set."""

    # Parquet footer metadata is a series of (byte string) key-value pairs.
    # Other users of metadata (eg. pandas) convert their metadata to JSON and store it under
    # a single key (a namespace, effectively), so we'll do the same under our own key.
    waveform_exporter_metadata_key = b"waveform_exporter"

    existing_metadata = existing_table.schema.metadata or {}
    json_byte_string = json.dumps(metadata).encode("utf-8")
    existing_table = existing_table.replace_schema_metadata(
        {**existing_metadata, waveform_exporter_metadata_key: json_byte_string}
    )
    return existing_table


def pseudonymise_relevant_columns(df: pd.DataFrame, safe_columns: list[str]):
    """ "csn", "mrn", "location" are examples of columns that must be pseudonymised.

    However, it's safer to list which columns *don't* need to be pseudonymised. Eg. you
    add a column but forget to consider whether it's sensitive, OR you rename one of the
    known sensitive columns and forget that this will cause privacy to break. This means
    that when you add a new column, you have to add it here if you don't want it to be
    hashed.
    """
    for col in df.columns:
        if col not in safe_columns:
            df[col] = df[col].apply(functools.partial(do_hash, col))
    return df
