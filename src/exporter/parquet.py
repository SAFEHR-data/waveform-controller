from pathlib import Path

from pyarrow import parquet as pq


def parquet_min_max_value(parquet_path: Path, column_name):
    """By the magic of parquet files we can get the min/max timestamps without loading
    it all into memory or even reading every row."""
    parquet_file = pq.ParquetFile(parquet_path)
    column_index = parquet_file.schema_arrow.get_field_index(column_name)
    if column_index == -1:
        raise ValueError(f"Column '{column_name}' not found in {parquet_path}")

    lowest_min = None
    highest_max = None

    metadata = parquet_file.metadata
    if metadata.num_rows == 0:
        return None, None

    # each row group will have its own min/max, so take the min of mins and the max of maxes
    for row_group_index in range(metadata.num_row_groups):
        column_meta = metadata.row_group(row_group_index).column(column_index)
        column_stats = column_meta.statistics
        # We created the parquets so we know they have up-to-date statistics.
        # We have already checked the file is not empty (which causes empty stats), so treat missing
        # statistics as an invalid file.
        if column_stats is None or not column_stats.has_min_max:
            raise ValueError(
                f"columns stats missing or min_max missing: {column_stats}"
            )
        if lowest_min is None or column_stats.min < lowest_min:
            lowest_min = column_stats.min
        if highest_max is None or column_stats.max > highest_max:
            highest_max = column_stats.max

    return lowest_min, highest_max
