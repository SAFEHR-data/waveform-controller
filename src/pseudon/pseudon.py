import argparse
import functools
import logging
from decimal import Decimal
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from locations import (
    WAVEFORM_ORIGINAL_PARQUET,
    WAVEFORM_PSEUDONYMISED_PARQUET,
    CSV_PATTERN,
    PSEUDONYMISED_PARQUET_PATTERN,
)
from .hashing import do_hash


def pseudon_cli():
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument("--csv", type=Path)
    args = arg_parser.parse_args()
    csv_to_parquets(args.csv)


def csv_to_parquets(
    *, date_str: str, original_csn: str, hashed_csn: str, variable_id: str, channel_id: str, units: str
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
            date=date_str, csn=original_csn, variable_id=variable_id, channel_id=channel_id, units=units
        )
    )
    # it's in the csv_path, but at least nowhere else!
    del original_csn

    logger.info("Turning CSV %s to parquets", csv_path)
    WAVEFORM_ORIGINAL_PARQUET.mkdir(parents=False, exist_ok=True)
    WAVEFORM_PSEUDONYMISED_PARQUET.mkdir(parents=False, exist_ok=True)
    df = pd.read_csv(
        str(csv_path),
        dtype={
            "csn": str,
            "mrn": str,
            "source_variable_id": str,
            "source_channel_id": str,
            "units": str,
            "sampling_rate": int,
            "timestamp": float,
            "location": str,
            "values": str,
        },
        header=0,  # the first line is always the header
    )

    def parse_array(x):
        # Not sure if this is the most efficient way. Might be able to do something with DecimalArray?
        # return [pa.decimal128(i) for i in x.replace(' ', '').split(',')]
        return [Decimal(i) for i in x.strip().strip("[]").replace(" ", "").split(",")]

    df["values"] = df["values"].apply(parse_array)

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
            ("values", pa.list_(pa.decimal128(9, 4))),
        ]
    )
    table = pa.Table.from_pandas(df, schema=schema, preserve_index=True)

    original_parquet_path = WAVEFORM_ORIGINAL_PARQUET / (csv_path.stem + ".parquet")
    pq.write_table(
        table,
        str(original_parquet_path),
        # valid values: {‘NONE’, ‘SNAPPY’, ‘GZIP’, ‘BROTLI’, ‘LZ4’, ‘ZSTD’}
        compression="zstd",
        use_dictionary=True,
        write_statistics=True,  # enable indexes/statistics
        flavor="spark",
    )
    logger.info(
        "Done turning CSV %s to original parquet %s", csv_path, original_parquet_path
    )

    df = pseudonymise_relevant_columns(df)
    pseudon_table = pa.Table.from_pandas(df, schema=schema, preserve_index=True)

    hashed_path = Path(
        str(PSEUDONYMISED_PARQUET_PATTERN).format(
            date=date_str, hashed_csn=hashed_csn, variable_id=variable_id, channel_id=channel_id, units=units
        )
    )
    pq.write_table(
        pseudon_table,
        str(hashed_path),
        compression="zstd",
        use_dictionary=True,
        write_statistics=True,  # enable indexes/statistics
        flavor="spark",
    )
    logger.info(
        "Done turning CSV %s to pseudonymised parquet %s", csv_path, hashed_path
    )


SAFE_COLUMNS = ["sampling_rate", "source_variable_id", "source_channel_id", "timestamp", "units", "values"]


def pseudonymise_relevant_columns(df: pd.DataFrame):
    """ "csn", "mrn", "location" are examples of columns that must be pseudonymised.

    However, it's safer to list which columns *don't* need to be pseudonymised. Eg. you
    add a column but forget to consider whether it's sensitive, OR you rename one of the
    known sensitive columns and forget that this will cause privacy to break. This means
    that when you add a new column, you have to add it here if you don't want it to be
    hashed.
    """
    for col in df.columns:
        if col not in SAFE_COLUMNS:
            df[col] = df[col].apply(functools.partial(do_hash, col))
    return df
