import os

import pytest

from src import csv_writer
from datetime import datetime, timezone
import locations


@pytest.mark.parametrize(
    "units, variable_id, channel_id, expected_filename",
    [
        ("uV", "11", "3", "2025-01-01/2025-01-01.12345678.11.3.uV.csv"),
        ("uV", "12", None, "2025-01-01/2025-01-01.12345678.12.noCh.uV.csv"),
        ("mL/s", "11", "3", "2025-01-01/2025-01-01.12345678.11.3.mLps.csv"),
        ("%", "11", "3", "2025-01-01/2025-01-01.12345678.11.3.percent.csv"),
    ],
)
def test_create_file_name_handles_units(
    monkeypatch, units, variable_id, channel_id, expected_filename, tmp_path
):
    # treat the normal absolute path as if it were a relative path, so we can put
    # a prefix on it (this code is usually run in a container)
    original_csv_dir = tmp_path / locations.WAVEFORM_ORIGINAL_CSV.relative_to("/")
    monkeypatch.setattr(csv_writer, "WAVEFORM_ORIGINAL_CSV", original_csv_dir)
    monkeypatch.setattr(locations, "WAVEFORM_ORIGINAL_CSV", original_csv_dir)

    # the only precondition is that the base dir must exist
    original_csv_dir.parent.mkdir(parents=True, exist_ok=True)

    observation_time = datetime(2025, 1, 1, 10, 10, 10, tzinfo=timezone.utc)
    csn = "12345678"
    mrn = "whatever"

    csv_writer.write_frame(
        {"value": "[1,2,3]"},
        variable_id,
        channel_id,
        observation_time.timestamp(),
        units,
        50,
        "mapped loc",
        csn,
        mrn,
    )

    # check that we can find the data again in its expected place
    expected_csv_path = locations.WAVEFORM_ORIGINAL_CSV / expected_filename
    assert os.path.exists(expected_csv_path)
