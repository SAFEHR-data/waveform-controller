"""Writes a frame of waveform data to a csv file."""

import csv
from datetime import datetime
from typing import Optional

from locations import WAVEFORM_ORIGINAL_CSV, make_file_name, FILE_STEM_PATTERN


def create_file_name(
    source_variable_id: str,
    source_channel_id: str,
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
    waveform_data: Optional[str] = None,
    single_value_str: Optional[str] = None,
    single_value_numeric: Optional[float] = None,
    source_variable_id: str,
    source_channel_id: str,
    observation_timestamp: float,
    units: str,
    sampling_rate: int,
    mapped_location_string: str,
    csn: str,
    mrn: str,
) -> bool:
    """Appends a frame of waveform data to a csv file (creates file if it doesn't
    exist). Exactly ONE of waveform_data, single_value_str, single_value_numeric must
    contain a non-None value. :param waveform_data: The waveform data to write, as a
    JSON value string of comma-separated numerics. Ie. as it comes straight out of the
    interchange message. :single_value_str: The single value string of the waveform
    data. :single_value_numeric: The single value string of the waveform data.

    :return: True if write was successful.
    """
    num_non_nones = sum(
        1
        for x in (waveform_data, single_value_str, single_value_numeric)
        if x is not None
    )
    if num_non_nones != 1:
        raise ValueError(
            "Exactly ONE of waveform_data, single_value_str, single_value_numeric must be not None"
        )
    observation_datetime = datetime.fromtimestamp(observation_timestamp)

    filename = WAVEFORM_ORIGINAL_CSV / create_file_name(
        source_variable_id, source_channel_id, observation_datetime, csn, units
    )
    filename.parent.mkdir(exist_ok=True, parents=True)

    # write header if is new file
    if not filename.exists():
        with open(filename, "w") as fileout:
            fileout.write(
                "csn,mrn,source_variable_id,source_channel_id,units,sampling_rate,timestamp,location,values\n"
            )

    with open(filename, "a") as fileout:
        wv_writer = csv.writer(fileout, delimiter=",")

        wv_writer.writerow(
            [
                csn,
                mrn,
                source_variable_id,
                source_channel_id,
                units,
                sampling_rate,
                observation_timestamp,
                mapped_location_string,
                waveform_data,
            ]
        )

    return True
