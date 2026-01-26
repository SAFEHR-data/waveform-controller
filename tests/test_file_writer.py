import pytest
from src.csv_writer import create_file_name
from datetime import datetime, timezone


@pytest.mark.parametrize(
    "units, expected_filename",
    [
        ("uV", "2025-01-01.12345678.11.3.uV.csv"),
        ("mL/s", "2025-01-01.12345678.11.3.mLps.csv"),
        ("%", "2025-01-01.12345678.11.3.percent.csv"),
    ],
)
def test_create_file_name_handles_units(units, expected_filename, tmp_path):
    source_variable_id = "11"
    source_channel_id = "3"
    observationTime = datetime(2025, 1, 1, 10, 10, 10, tzinfo=timezone.utc)
    csn = "12345678"

    filename = create_file_name(source_variable_id, source_channel_id, observationTime, csn, units)

    assert filename == expected_filename

    # check we can write to it
    with open(f"{tmp_path}/{filename}", "w") as fileout:
        fileout.write("Test string")
