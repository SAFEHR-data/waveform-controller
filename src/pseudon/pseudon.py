import argparse
from pathlib import Path
from decimal import Decimal

from locations import WAVEFORM_ORIGINAL_CSV, WAVEFORM_ORIGINAL_PARQUET, WAVEFORM_PSEUDONYMISED
from pyarrow import timestamp


def main():
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument('--csv', type=Path)
    args = arg_parser.parse_args()
    csv_to_parquets(args.csv)


# convert CSV data (with full identifiers) to two versions in parquet format:
# - full identifiers (intended for debugging, NOT to be exported to DSH)
# - pseudonymised identifiers (for export to DSH)
def csv_to_parquets(csv_path: Path):
    import pandas as pd
    import pyarrow as pa
    import pyarrow.parquet as pq

    WAVEFORM_ORIGINAL_PARQUET.mkdir(parents=False, exist_ok=True)
    # Read the CSV with two string columns and one array numeric column
    # Assume col1, col2 are strings, col3 is array of numbers in string format, e.g. "[1,2,3]"
    df = pd.read_csv(csv_path,
                     dtype={'csn': str, 'mrn': str, 'stream': str, 'units': str,
                            'timestamp': float, 'location': str, 'values': str},
                     keep_default_na=True,
                     na_values=["", "NaN", "nan", "None"])

    def parse_array(x):
        # Not sure if this is the most efficient way. Might be able to do something with DecimalArray?
        # return [pa.decimal128(i) for i in x.replace(' ', '').split(',')]
        return [Decimal(i) for i in x.strip().strip('[]').replace(' ', '').split(',')]

    df['values'] = df['values'].apply(parse_array)

    # Convert pandas DataFrame to pyarrow Table with proper types
    schema = pa.schema([
        ('csn', pa.string()),
        ('mrn', pa.string()),
        ('stream', pa.string()),
        ('units', pa.string()),
        ('timestamp', pa.float64()),
        ('location', pa.string()),
        # decimal32 can have a maximum of 9 significant digits.
        # We can go to 64 if needed but let's try and keep it compact.
        # But they're not exposed?? Use 128 instead.
        ('values', pa.list_(pa.decimal128(9,4))),
    ])
    table = pa.Table.from_pandas(df, schema=schema, preserve_index=True)

    pq.write_table(
        table,
        str(WAVEFORM_ORIGINAL_PARQUET / (csv_path.stem + '.parquet')),
        # valid values: {‘NONE’, ‘SNAPPY’, ‘GZIP’, ‘BROTLI’, ‘LZ4’, ‘ZSTD’}
        compression='zstd',
        use_dictionary=True,
        write_statistics=True,  # enable indexes/statistics
        flavor='spark'
    )


def call_hasher(identifier: str):
    return thingy(identifier)
