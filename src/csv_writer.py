"""Writes a frame of waveform data to a csv file."""

import csv
from datetime import datetime
from locations import WAVEFORM_ORIGINAL_CSV
from pathlib import Path


def create_file_name(
    sourceStreamId: str, observationTime: datetime, csn: str, units: str
) -> str:
    """Create a unique file name based on the patient contact serial number
    (csn) the date, and the source system."""
    datestring = observationTime.strftime("%Y-%m-%d")
    units = units.replace("/", "p")
    units = units.replace("%", "percent")
    return f"{datestring}.{csn}.{sourceStreamId}.{units}.csv"


def write_frame(waveform_message: dict, csn: str, mrn: str) -> bool:
    """Appends a frame of waveform data to a csv file (creates file if it
    doesn't exist.

    :return: True if write was successful.
    """
    sourceStreamId = waveform_message.get("sourceStreamId", None)
    observationTime = waveform_message.get("observationTime", False)

    if not observationTime:
        raise ValueError("waveform_message is missing observationTime")

    observation_datetime = datetime.fromtimestamp(observationTime)
    units = waveform_message.get("unit", "")

    WAVEFORM_ORIGINAL_CSV.mkdir(exist_ok=True, parents=False)

    filename = WAVEFORM_ORIGINAL_CSV / create_file_name(
        sourceStreamId, observation_datetime, csn, units
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
                sourceStreamId,
                units,
                waveform_message.get("samplingRate", ""),
                observationTime,
                waveform_message.get("mappedLocationString", ""),
                waveform_data,
            ]
        )

    return True
