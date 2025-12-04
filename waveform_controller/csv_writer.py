"""Writes a frame of waveform data to a csv file."""

import csv
from datetime import datetime
from pathlib import Path


def create_file_name(
    sourceSystem: str, observationTime: datetime, csn: str, units: str
) -> str:
    """Create a unique file name based on the patient contact serial number
    (csn) the date, and the source system."""
    datestring = observationTime.strftime("%Y-%m-%d")
    return f"{datestring}.{csn}.{sourceSystem}.{units}.csv"


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
    units = waveform_message.get("unit", "")

    out_path = "waveform-export/"
    Path(out_path).mkdir(exist_ok=True)

    filename = out_path + create_file_name(
        sourceSystem, observation_datetime, csn, units
    )
    with open(filename, "a") as fileout:
        wv_writer = csv.writer(fileout, delimiter=",")
        waveform_data = waveform_message.get("numericValues", "")
        if waveform_data != "":
            waveform_data = waveform_data.get("value", "")

        wv_writer.writerow(
            [
                csn,
                mrn,
                units,
                waveform_message.get("samplingRate", ""),
                observationTime,
                waveform_data,
            ]
        )

    return True
