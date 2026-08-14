"""Writes a frame of waveform data to a csv file."""

import csv
from datetime import datetime
from typing import Optional

from locations import WAVEFORM_ORIGINAL_CSV, make_file_name, FILE_STEM_PATTERN


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
    values: Optional[str] = None,
    string_value: Optional[str] = None,
    numeric_value: Optional[float] = None,
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
    exist). Exactly ONE of values, string_value, numeric_value must contain a non-None
    value. :param values: The waveform data to write, as a JSON value string of comma-
    separated numerics. Ie. as it comes straight out of the interchange message.
    :string_value: The single value string of the waveform data. :numeric_value: The
    single value string of the waveform data.

    :return: True if write was successful.
    """
    num_non_nones = sum(
        1 for x in (values, string_value, numeric_value) if x is not None
    )
    if num_non_nones != 1:
        raise ValueError(
            "Exactly ONE of values, string_value, numeric_value must be not None"
        )
    observation_datetime = datetime.fromtimestamp(observation_timestamp)

    filename = WAVEFORM_ORIGINAL_CSV / create_file_name(
        source_variable_id, source_channel_id, observation_datetime, csn, units
    )
    filename.parent.mkdir(exist_ok=True, parents=True)

    if values is not None:
        # HF
        csv_header = "csn,mrn,source_variable_id,source_channel_id,units,sampling_rate,timestamp,location,values\n"
    else:
        # LF
        csv_header = "csn,mrn,source_variable_id,units,timestamp,location,string_value,numeric_value\n"
    # write header if is new file
    if not filename.exists():
        with open(filename, "w") as fileout:
            fileout.write(csv_header)

    with open(filename, "a") as fileout:
        # predictable quoting makes testing easier
        wv_writer = csv.writer(fileout, delimiter=",", quoting=csv.QUOTE_ALL)

        if values is not None:
            # HF
            row_array = [
                csn,
                mrn,
                source_variable_id,
                source_channel_id,
                units,
                sampling_rate,
                observation_timestamp,
                mapped_location_string,
                values,
            ]
        else:
            row_array = [
                csn,
                mrn,
                source_variable_id,
                units,
                observation_timestamp,
                mapped_location_string,
                string_value if string_value is not None else "",
                numeric_value if numeric_value is not None else "",
            ]

        wv_writer.writerow(row_array)

    return True
