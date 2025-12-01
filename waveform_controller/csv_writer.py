"""Writes a frame of waveform data to a csv file."""

import csv
from datetime import datetime


def create_file_name(
    sourceSystem: str, observationTime: datetime, csn: str, units: str
) -> str:
    """Create a unique file name based on the patient contact serial number
    (csn) the date, and the source system."""
    datestring = observationTime.strftime("%Y-%m-%d")
    return f"waveform_data/{datestring}.{csn}.{sourceSystem}.{units}.csv"


def write_frame(waveform_message: dict, csn: str, mrn: str) -> bool:
    """Appends a frame of waveform data to a csv file (creates file if it
    doesn't exist.

    :return: True if write was successful.
    """
    sourceSystem = waveform_message.get("sourceSystem", None)
    observationTime = waveform_message.get("observationTime", False)

    if not observationTime:
        raise ValueError("waveform_message is missing observationTime")

    observation_datetime = datetime.fromtimestamp(observationTime)
    units = waveform_message.get("unit", "None")

    filename = create_file_name(sourceSystem, observation_datetime, csn, units)
    with open(filename, "a") as fileout:
        wv_writer = csv.writer(fileout, delimiter=",")
        wv_writer.writerow(
            [
                csn,
                mrn,
                units,
                waveform_message.get("samplingRate", "None"),
                observationTime,
                waveform_message.get("numericValues", "NaN").get("value", "NaN"),
            ]
        )

    # TODO Check write success, and clear queue if OK.

    return False
