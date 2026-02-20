import json
import logging

from exporter.parquet import parquet_min_max_value

logger = logging.getLogger(__name__)


def make_daily_hash_summary(daily_files, out_json_file):
    min_timestamp_key = "min_timestamp"
    max_timestamp_key = "max_timestamp"
    hash_summary_by_csn = {}
    for daily_file in daily_files:
        entry = {}
        original_parquet = daily_file.get_original_parquet_path()
        entry["csn"] = daily_file.csn
        entry["hashed_csn"] = daily_file.hashed_csn
        min_timestamp, max_timestamp = parquet_min_max_value(
            original_parquet, "timestamp"
        )
        if min_timestamp is None or max_timestamp is None:
            # do not contribute to stats
            logger.warning(
                f"Parquet does not have a min/max value, assumed to be empty: {original_parquet}"
            )
            break
        entry[min_timestamp_key] = min_timestamp
        entry[max_timestamp_key] = max_timestamp
        existing_entry = hash_summary_by_csn.get(daily_file.csn)
        if existing_entry is None:
            hash_summary_by_csn[daily_file.csn] = entry
        else:
            # update the limits (there can be multiple files for the same CSN because each variable/channel
            # is in its own file)
            existing_entry[min_timestamp_key] = min(
                min_timestamp, existing_entry[min_timestamp_key]
            )
            existing_entry[max_timestamp_key] = max(
                max_timestamp, existing_entry[max_timestamp_key]
            )

    hash_summary = list(hash_summary_by_csn.values())

    with open(out_json_file, "w") as fh:
        json.dump(hash_summary, fh, indent=0)
    logger.info(f"Wrote {len(hash_summary)} entries to {out_json_file}")
