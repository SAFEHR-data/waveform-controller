import pytest
from src.csv_writer import create_file_name
from datetime import datetime, timezone


@pytest.mark.parametrize(
    "units, variable_id, channel_id, expected_filename",
    [
        ("uV", "11", "3", "2025-01-01.12345678.11.3.uV.csv"),
        ("uV", "12", None, "2025-01-01.12345678.12.noCh.uV.csv"),
        ("mL/s", "11", "3", "2025-01-01.12345678.11.3.mLps.csv"),
        ("%", "11", "3", "2025-01-01.12345678.11.3.percent.csv"),
    ],
)
def test_create_file_name_handles_units(units, variable_id, channel_id, expected_filename, tmp_path):
    observationTime = datetime(2025, 1, 1, 10, 10, 10, tzinfo=timezone.utc)
    csn = "12345678"

    filename = create_file_name(variable_id, channel_id, observationTime, csn, units)

    assert filename == expected_filename

    # check we can write to it
    with open(f"{tmp_path}/{filename}", "w") as fileout:
        fileout.write("Test string")
