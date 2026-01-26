"""Writes a frame of waveform data to a csv file."""

import csv
from datetime import datetime

from locations import WAVEFORM_ORIGINAL_CSV, make_file_name, FILE_STEM_PATTERN


def create_file_name(
        source_variable_id: str, source_channel_id: str,
        observation_time: datetime, csn: str, units: str
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
    waveform_data: dict,
    source_variable_id: str,
    source_channel_id: str,
    observation_timestamp: float,
    units: str,
    sampling_rate: int,
    mapped_location_string: str,
    csn: str,
    mrn: str,
) -> bool:
    """Appends a frame of waveform data to a csv file (creates file if it doesn't exist.

    :return: True if write was successful.
    """
    observation_datetime = datetime.fromtimestamp(observation_timestamp)

    WAVEFORM_ORIGINAL_CSV.mkdir(exist_ok=True, parents=False)

    filename = WAVEFORM_ORIGINAL_CSV / create_file_name(
        source_variable_id, source_channel_id, observation_datetime, csn, units
    )

    # write header if is new file
    if not filename.exists():
        with open(filename, "w") as fileout:
            fileout.write(
                "csn,mrn,source_variable_id,source_channel_id,units,sampling_rate,timestamp,location,values\n"
            )

    with open(filename, "a") as fileout:
        wv_writer = csv.writer(fileout, delimiter=",")
        waveform_data = waveform_data.get("value", "")

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
