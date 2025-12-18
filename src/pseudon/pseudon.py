import argparse
import functools
from decimal import Decimal
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from locations import WAVEFORM_ORIGINAL_CSV, WAVEFORM_ORIGINAL_PARQUET, WAVEFORM_PSEUDONYMISED_PARQUET

from .hashing import do_hash


def main():
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument('--csv', type=Path)
    args = arg_parser.parse_args()
    csv_to_parquets(args.csv)


# convert CSV data (with full identifiers) to two versions in parquet format:
# - full identifiers (intended for debugging, NOT to be exported to DSH)
# - pseudonymised identifiers (for export to DSH)
def csv_to_parquets(csv_path: Path):

    WAVEFORM_ORIGINAL_PARQUET.mkdir(parents=False, exist_ok=True)
    WAVEFORM_PSEUDONYMISED_PARQUET.mkdir(parents=False, exist_ok=True)
    # Read the CSV with two string columns and one array numeric column
    # Assume col1, col2 are strings, col3 is array of numbers in string format, e.g. "[1,2,3]"
    df = pd.read_csv(str(csv_path),
                     dtype={'csn': str, 'mrn': str, 'sourceStreamId': str, 'units': str,
                            'samplingRate': int,
                            'timestamp': float, 'location': str, 'values': str},
                     header=0  # Explicitly specify that the first line is always the header
                     )

    def parse_array(x):
        # Not sure if this is the most efficient way. Might be able to do something with DecimalArray?
        # return [pa.decimal128(i) for i in x.replace(' ', '').split(',')]
        return [Decimal(i) for i in x.strip().strip('[]').replace(' ', '').split(',')]

    df['values'] = df['values'].apply(parse_array)

    # Convert pandas DataFrame to pyarrow Table with proper types
    schema = pa.schema([
        ('csn', pa.string()),
        ('mrn', pa.string()),
        ('sourceStreamId', pa.string()),
        ('units', pa.string()),
        ('samplingRate', pa.int32()),
        ('timestamp', pa.float64()),
        ('location', pa.string()),
        # decimal32 can have a maximum of 9 significant digits.
        # We can go to 64 if needed but let's try and keep it compact.
        # But they're not exposed?? Use 128 instead.
        ('values', pa.list_(pa.decimal128(9,4))),
    ])
    table = pa.Table.from_pandas(df, schema=schema, preserve_index=True)

    original_parquet_path = WAVEFORM_ORIGINAL_PARQUET / (csv_path.stem + '.parquet')
    pq.write_table(
        table,
        str(original_parquet_path),
        # valid values: {‘NONE’, ‘SNAPPY’, ‘GZIP’, ‘BROTLI’, ‘LZ4’, ‘ZSTD’}
        compression='zstd',
        use_dictionary=True,
        write_statistics=True,  # enable indexes/statistics
        flavor='spark'
    )

    df = pseudonymise_relevant_columns(df)
    pseudon_table = pa.Table.from_pandas(df, schema=schema, preserve_index=True)

    # XXX: The file path itself contains an identifier (the CSN). Need to fix.
    pseudon_parquet_path = WAVEFORM_PSEUDONYMISED_PARQUET / (csv_path.stem + '.parquet')
    pq.write_table(
        pseudon_table,
        str(pseudon_parquet_path),
        compression='zstd',
        use_dictionary=True,
        write_statistics=True,  # enable indexes/statistics
        flavor='spark'
    )

def pseudonymise_relevant_columns(df: pd.DataFrame):
    for col in ['csn', 'mrn', 'location']:
        df[col] = df[col].apply(functools.partial(do_hash, col))
    return df

