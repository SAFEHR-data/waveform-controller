from pathlib import Path

WAVEFORM_EXPORT_BASE = Path("/waveform-export")
WAVEFORM_ORIGINAL_CSV = WAVEFORM_EXPORT_BASE / "original-csv"
WAVEFORM_ORIGINAL_PARQUET = WAVEFORM_EXPORT_BASE / "original-parquet"
WAVEFORM_PSEUDONYMISED_PARQUET = WAVEFORM_EXPORT_BASE / "pseudonymised"
WAVEFORM_SNAKEMAKE_LOGS = WAVEFORM_EXPORT_BASE / "snakemake-logs"
WAVEFORM_FTPS_LOGS = WAVEFORM_EXPORT_BASE / "ftps-logs"


# file patterns
FILE_STEM_PATTERN = "{date}.{csn}.{variable_id}.{channel_id}.{units}"
FILE_STEM_PATTERN_HASHED = "{date}.{hashed_csn}.{variable_id}.{channel_id}.{units}"
CSV_PATTERN = WAVEFORM_ORIGINAL_CSV / (FILE_STEM_PATTERN + ".csv")
ORIGINAL_PARQUET_PATTERN = WAVEFORM_ORIGINAL_PARQUET / (FILE_STEM_PATTERN + ".parquet")
PSEUDONYMISED_PARQUET_PATTERN = WAVEFORM_PSEUDONYMISED_PARQUET / (
    FILE_STEM_PATTERN_HASHED + ".parquet"
)


def make_file_name(template: str, subs: dict[str, str]):
    # Don't allow the string "None" to appear in the file name if the channel is None,
    # because it just looks broken.
    channel_id_key = "channel_id"
    if channel_id_key in subs and subs.get(channel_id_key) is None:
        subs[channel_id_key] = "noCh"
    return template.format(**subs)
