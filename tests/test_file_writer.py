import pytest
from src.csv_writer import create_file_name
from datetime import datetime, timezone


@pytest.mark.parametrize(
    "units, expected_filename",
    [
        ("uV", "2025-01-01.12345678.11.uV.csv"),
        ("mL/s", "2025-01-01.12345678.11.mLps.csv"),
        ("%", "2025-01-01.12345678.11.percent.csv"),
    ],
)
def test_create_file_name_handles_units(units, expected_filename, tmp_path):
    sourceSystem = "11"
    observationTime = datetime(2025, 1, 1, tzinfo=timezone.utc)
    csn = "12345678"

    filename = create_file_name(sourceSystem, observationTime, csn, units)

    assert filename == expected_filename

    # check we can write to it
    with open(f"{tmp_path}/{filename}", "w") as fileout:
        fileout.write("Test string")
