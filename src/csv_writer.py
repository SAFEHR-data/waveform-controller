"""Writes a frame of waveform data to a csv file."""

import csv
import json
from datetime import datetime
import pandas as pd
from typing import Optional

from locations import (
    WAVEFORM_ORIGINAL_CSV,
    WAVEFORM_PSEUDONYMISED_EHR,
    make_file_name,
    FILE_STEM_PATTERN,
    EHR_STEM_PATTERN_HASHED,
)


def create_file_name(
    source_variable_id: str,
    source_channel_id: Optional[str],
    observation_time: datetime,
    csn: str,
    units: str,
) -> str:
    """Create a unique file name based on the patient contact serial number (csn) the
    date, and the source system."""
    datestring = observation_time.strftime("%Y-%m-%d")
    units = units.replace("/", "p")
    units = units.replace("%", "percent")
    subs_dict = dict(
        date=datestring,
        csn=csn,
        variable_id=source_variable_id,
        channel_id=source_channel_id,
        units=units,
    )
    stem = make_file_name(FILE_STEM_PATTERN, subs_dict)
    return f"{stem}.csv"


def write_frame(
    *,
    numeric_values: Optional[list[float]] = None,
    string_values: Optional[list[str]] = None,
    source_variable_id: str,
    source_channel_id: Optional[str] = None,
    observation_timestamp: float,
    units: str,
    sampling_rate: Optional[int] = None,
    mapped_location_string: str,
    csn: str,
    mrn: str,
) -> bool:
    """Appends a frame of waveform data to a csv file (creates file if it doesn't
    exist). Exactly ONE of string_values, numeric_values must contain a non-None value.

    :return: True if write was successful.
    """
    num_non_nones = sum(1 for x in (string_values, numeric_values) if x is not None)
    if num_non_nones != 1:
        raise ValueError(
            "Exactly ONE of string_values, numeric_values must be not None"
        )
    observation_datetime = datetime.fromtimestamp(observation_timestamp)

    filename = WAVEFORM_ORIGINAL_CSV / create_file_name(
        source_variable_id, source_channel_id, observation_datetime, csn, units
    )
    filename.parent.mkdir(exist_ok=True, parents=True)

    # The CSV fields are the same regardless of HF vs LF, to keep downstream
    # processing simpler. Some fields may be nulled out, however.
    # Single values will be wrapped in an array of length 1, if necessary.
    csv_header = "csn,mrn,source_variable_id,source_channel_id,units,sampling_rate,timestamp,location,numeric_values,string_values\n"
    # write header if is new file
    if not filename.exists():
        with open(filename, "w", newline="") as fileout:
            fileout.write(csv_header)

    # open with newline="" as per csv.writer docs
    with open(filename, "a", newline="") as fileout:
        # predictable quoting makes testing easier
        wv_writer = csv.writer(
            fileout, delimiter=",", quoting=csv.QUOTE_ALL, lineterminator="\n"
        )

        # Encode value lists as JSON so parquet conversion can use json.loads
        # (Python list repr breaks on commas / quotes in string values).
        row_array = [
            csn,
            mrn,
            source_variable_id,
            source_channel_id if source_channel_id is not None else "",
            units,
            sampling_rate if sampling_rate is not None else "",
            observation_timestamp,
            mapped_location_string,
            json.dumps(numeric_values) if numeric_values is not None else "",
            json.dumps(string_values) if string_values is not None else "",
        ]

        wv_writer.writerow(row_array)

    return True


def write_ehr(
    df: pd.DataFrame,
    date_str: str,
    hashed_csn: str,
) -> bool:
    """Writes a frame of electronic healthcare data to a csv file.

    :return: True if write was successful.
    """
    subs_dict = dict(date=date_str, hashed_csn=hashed_csn)
    stem = make_file_name(EHR_STEM_PATTERN_HASHED, subs_dict)
    filename = WAVEFORM_PSEUDONYMISED_EHR / f"{stem}_ehr.csv"
    filename.parent.mkdir(exist_ok=True, parents=True)

    df.to_csv(filename, index=False)

    return True
