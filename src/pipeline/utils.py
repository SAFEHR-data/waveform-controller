import time

from datetime import datetime, timedelta, timezone
from pathlib import Path
import re
from typing import Optional

from snakemake.io import glob_wildcards

from pseudon.hashing import do_hash
from locations import (
    WAVEFORM_PSEUDONYMISED_PARQUET,
    HASH_LOOKUP_JSON,
    ORIGINAL_PARQUET_PATTERN,
    FILE_STEM_PATTERN_HASHED,
    EHR_FILE_PATTERN_HASHED,
    CSV_PATTERN,
    make_file_name,
    ALL_UPLOADED_JSON,
)

# Snakemake seems to like guessing the types of env vars, so
# here are some methods to force them to the type they're supposed to be.


def config_str(value) -> Optional[str]:
    """Convert a config value from env/CLI to a string."""
    if value is None:
        return None
    return str(value).strip()


def config_int(value) -> Optional[int]:
    """Convert a config value from env/CLI to an int.

    :raises ValueError: if the string cannot be interpreted as an int (including if it
        has a decimal point).
    """
    if value is None:
        return None
    s = str(value).strip()
    if not s:
        return None
    return int(s)


def config_bool(value) -> bool:
    """Convert a config value from env/CLI to a bool."""
    s = str(value).strip().lower()
    if s in {"", "0", "false"}:
        return False
    if s in {"1", "true"}:
        return True
    raise ValueError(f'Can\'t interpret value "{value}" as a boolean')


def hash_csn(csn: str) -> str:
    return do_hash("csn", csn)


class InputCsvFile:
    """Represent the different files in the pipeline from the point of view of one csn +
    day + variable + channel combination (ie one "original CSV" file). These files are
    glued together by the Snakemake rules.

    Note that there is a many to one relationship between a CSV file and some of the
    files described here.
    """

    def __init__(
        self, date: str, csn: str, variable_id: str, channel_id: str, units: str
    ):
        self.date = date
        self.csn = csn
        self.hashed_csn = hash_csn(csn)
        self.variable_id = variable_id
        self.channel_id = channel_id
        self.units = units
        self._subs_dict = dict(
            date=self.date,
            csn=self.csn,
            hashed_csn=self.hashed_csn,
            variable_id=self.variable_id,
            channel_id=self.channel_id,
            units=self.units,
        )

    def get_original_csv_path(self) -> Path:
        return Path(make_file_name(str(CSV_PATTERN), self._subs_dict))

    def get_original_parquet_path(self) -> Path:
        return Path(make_file_name(str(ORIGINAL_PARQUET_PATTERN), self._subs_dict))

    def get_pseudonymised_parquet_path(self) -> Path:
        final_stem = make_file_name(FILE_STEM_PATTERN_HASHED, self._subs_dict)
        return WAVEFORM_PSEUDONYMISED_PARQUET / f"{final_stem}.parquet"

    def get_ftps_uploaded_all_file(self) -> Path:
        return Path(make_file_name(str(ALL_UPLOADED_JSON), self._subs_dict))

    def get_daily_hash_lookup(self) -> Path:
        return Path(make_file_name(str(HASH_LOOKUP_JSON), self._subs_dict))

    def get_ehr_lookup(self) -> Path:
        rel_file_path = make_file_name(EHR_FILE_PATTERN_HASHED, self._subs_dict)
        return WAVEFORM_PSEUDONYMISED_PARQUET / rel_file_path


def get_file_age(file_path: Path) -> timedelta:
    # need to use UTC to avoid DST issues
    file_time_utc = datetime.fromtimestamp(file_path.stat().st_mtime, timezone.utc)
    now_utc = datetime.now(timezone.utc)
    return now_utc - file_time_utc


def timestamp_for_paths() -> str:
    """A now timestamp that is safe for being in file paths on all OSes we are using."""
    now = datetime.now(timezone.utc)
    return now.strftime("%Y-%m-%dT%H%M%SZ")


def determine_eventual_outputs(
    csv_wait_time: timedelta,
    process_only_n_days_ago: Optional[int] = None,
    process_dates_regex: Optional[str] = None,
):
    """
    :param csv_wait_time: only process files older than this
    :param process_only_n_days_ago: if None, process all dates,
                                    if >=1 only from that many days ago (1 = yesterday),
                                    else raise ValueError
    :param process_dates_regex: Only has effect if process_only_n_days_ago is None.
                                if process_dates_regex is None, all datestrings are included,
                                 otherwise it is treated as a regular expression that must match datestrings
                                 if they are to be included
    :returns: A list of InputCsvFile and a dictionary containing the hashed csn -> csn mappings, according to the filtering rules.
    """
    # Discover all CSVs using the basic file name pattern
    before = time.perf_counter()
    all_wc = glob_wildcards(CSV_PATTERN)

    # all_wc.date, all_wc.csn, all_wc.streamId, all_wc.units are parallel lists
    # e.g. all_wc.csn[0] corresponds to all_wc.date[0], etc.

    # Build reverse lookup using named wildcards
    _hash_to_csn: dict[str, str] = {}

    if process_only_n_days_ago is not None:
        if process_only_n_days_ago < 1:
            raise ValueError("process_only_n_days_ago must be >= 1")
        process_dates_regex = (
            datetime.now(tz=timezone.utc).date()
            - timedelta(days=process_only_n_days_ago)
        ).isoformat()

    for csn in all_wc.csn:
        _hash_to_csn[hash_csn(csn)] = csn
    # Apply all_wc to FILE_STEM_PATTERN_HASHED to generate the output stems
    _all_outputs = []
    for date, csn, variable_id, channel_id, units in zip(
        all_wc.date, all_wc.csn, all_wc.variable_id, all_wc.channel_id, all_wc.units
    ):
        input_file_obj = InputCsvFile(date, csn, variable_id, channel_id, units)
        orig_file = input_file_obj.get_original_csv_path()
        if (
            process_dates_regex is not None
            and re.search(process_dates_regex, date) is None
        ):
            print(f"Skipping file not from {process_dates_regex} {orig_file}")
            continue
        if csn == "unmatched_csn":
            print(f"Skipping file with unmatched CSN: {orig_file}")
            continue
        file_age = get_file_age(orig_file)
        if file_age < csv_wait_time:
            print(f"File too new (age={file_age}): {orig_file}")
            continue
        _all_outputs.append(input_file_obj)
    after = time.perf_counter()
    print(
        f"Calculated output files using newness threshold {csv_wait_time} in {after - before} seconds"
    )
    return _all_outputs, _hash_to_csn
