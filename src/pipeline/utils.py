import time
import telemetry
from datetime import datetime, timedelta, timezone
from pathlib import Path
import re

from snakemake.io import glob_wildcards

from pseudon.hashing import do_hash
from locations import (
    WAVEFORM_PSEUDONYMISED_PARQUET,
    WAVEFORM_PSEUDONYMISED_EHR,
    WAVEFORM_FTPS_LOGS,
    HASH_LOOKUP_JSON,
    ORIGINAL_PARQUET_PATTERN,
    FILE_STEM_PATTERN_HASHED,
    EHR_STEM_PATTERN_HASHED,
    CSV_PATTERN,
    make_file_name,
)


def config_bool(value):
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
    day + variable + channel combination (ie.

    one "original CSV" file). These files are glued together by the Snakemake rules.
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

    def get_ftps_uploaded_file(self) -> Path:
        final_stem = make_file_name(FILE_STEM_PATTERN_HASHED, self._subs_dict)
        return WAVEFORM_FTPS_LOGS / (final_stem + ".ftps.uploaded.json")

    def get_daily_hash_lookup(self) -> Path:
        return Path(make_file_name(str(HASH_LOOKUP_JSON), self._subs_dict))

    def get_ehr_lookup(self) -> Path:
        final_stem = make_file_name(EHR_STEM_PATTERN_HASHED, self._subs_dict)
        return WAVEFORM_PSEUDONYMISED_EHR / f"{final_stem}_ehr.csv"


def get_file_age(file_path: Path) -> timedelta:
    # need to use UTC to avoid DST issues
    file_time_utc = datetime.fromtimestamp(file_path.stat().st_mtime, timezone.utc)
    now_utc = datetime.now(timezone.utc)
    return now_utc - file_time_utc


def determine_eventual_outputs(
    csv_wait_time: timedelta, process_only_yesterday: bool, process_datestring: str
):
    """
    :param csv_wait_time: only process files older than this
    :param process_only_yesterday: if false we process all dates, true only from yesterday
    :param process_datestring: a regular expression to match datestrings. Has no effect if
    process_only_yesterday is true
    :returns: A list of InputCsvFile and a dictionary containing the hash and csn values.
    """
    # Discover all CSVs using the basic file name pattern
    before = time.perf_counter()
    all_wc = glob_wildcards(CSV_PATTERN)

    # all_wc.date, all_wc.csn, all_wc.streamId, all_wc.units are parallel lists
    # e.g. all_wc.csn[0] corresponds to all_wc.date[0], etc.

    # Build reverse lookup using named wildcards
    _hash_to_csn: dict[str, str] = {}

    if process_only_yesterday:
        process_datestring = (
            datetime.now(tz=timezone.utc).date() - timedelta(days=1)
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
        if re.search(process_datestring, date) is None:
            print(f"Skipping file not from {process_datestring} {orig_file}")
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


def report_ftp_upload():
    telemetry.ftps_uploaded.add(1)
