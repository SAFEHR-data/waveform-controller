import os
from typing import Optional

import pytest

from src import csv_writer
from datetime import datetime, timezone
import locations


@pytest.mark.parametrize(
    "units, variable_id, values, expected_filenames",
    [
        # categorical, will have been mapped to string
        (
            ["unitless"],
            "584",
            ["Pressure Support / CPAP (PS)"],
            ["2025-01-01/2025-01-01.12345678.584.noCh.unitless.csv"],
        ),
        # string value
        (
            ["unitless"],
            "1190",
            ["1:2"],
            ["2025-01-01/2025-01-01.12345678.1190.noCh.unitless.csv"],
        ),
        # numerical, and also a variable with more than one unit at the same time
        (
            ["%", "s"],
            "1408",
            [5, 0.2],
            # units should probably be removed from the filename altogether,
            # as it will create a separate file for each
            [
                "2025-01-01/2025-01-01.12345678.1408.noCh.percent.csv",
                "2025-01-01/2025-01-01.12345678.1408.noCh.s.csv",
            ],
        ),
    ],
)
def test_create_csv_low_freq(
    monkeypatch,
    tmp_path,
    units: list[str],
    variable_id: str,
    values: list,
    expected_filenames,
):
    """
    :param values: one value per line to write!
    """
    # check test is valid
    assert len(units) == len(values) == len(expected_filenames)

    _setup_write_csv(monkeypatch, tmp_path)

    observation_time = datetime(2025, 1, 1, 10, 10, 10, tzinfo=timezone.utc)
    csn = "12345678"
    mrn = "whatever"

    # it creates a separate file for each unit, so we needs an expected text for each unit
    expected_header = "csn,mrn,source_variable_id,source_channel_id,units,sampling_rate,timestamp,location,numeric_values,string_values\n"
    expected_texts = dict.fromkeys(units, expected_header)
    for idx, u in enumerate(units):
        v = values[idx]
        string_values = numeric_values = None
        if type(v) is str:
            string_values = [v]
            expected_v_str = f"['{v}']"
            expected_v_num = ""
        elif type(v) is float or type(v) is int:
            numeric_values = [v]
            expected_v_str = ""
            expected_v_num = f"[{v}]"
        else:
            raise ValueError(v)

        csv_writer.write_frame(
            string_values=string_values,
            numeric_values=numeric_values,
            source_variable_id=variable_id,
            observation_timestamp=observation_time.timestamp(),
            units=u,
            mapped_location_string="mapped loc",
            csn=csn,
            mrn=mrn,
        )
        expected_line = f'"12345678","whatever","{variable_id}","","{u}","","1735726210.0","mapped loc","{expected_v_num}","{expected_v_str}"\n'
        expected_texts[u] += expected_line
    # need to check multiple files for multiple units
    for idx, ef in enumerate(expected_filenames):
        _check_written_csv(ef, expected_texts[units[idx]])


@pytest.mark.parametrize(
    "units, variable_id, channel_id, expected_filename",
    [
        ("uV", "11", "3", "2025-01-01/2025-01-01.12345678.11.3.uV.csv"),
        ("uV", "12", None, "2025-01-01/2025-01-01.12345678.12.noCh.uV.csv"),
        ("mL/s", "11", "3", "2025-01-01/2025-01-01.12345678.11.3.mLps.csv"),
        ("%", "11", "3", "2025-01-01/2025-01-01.12345678.11.3.percent.csv"),
    ],
)
def test_create_csv_high_freq(
    monkeypatch,
    units: str,
    variable_id: str,
    channel_id: Optional[str],
    expected_filename: str,
    tmp_path,
):
    _setup_write_csv(monkeypatch, tmp_path)

    observation_time = datetime(2025, 1, 1, 10, 10, 10, tzinfo=timezone.utc)
    csn = "12345678"
    mrn = "whatever"

    csv_writer.write_frame(
        numeric_values=[1, 2, 3.0],
        source_variable_id=variable_id,
        source_channel_id=channel_id,
        observation_timestamp=observation_time.timestamp(),
        units=units,
        sampling_rate=50,
        mapped_location_string="mapped loc",
        csn=csn,
        mrn=mrn,
    )

    expected_text = (
        'csn,mrn,source_variable_id,source_channel_id,units,sampling_rate,timestamp,location,numeric_values,string_values\n'
        f'"12345678","whatever","{variable_id}","{channel_id or ""}","{units}","50","1735726210.0","mapped loc","[1, 2, 3.0]",""\n'
    )
    _check_written_csv(expected_filename, expected_text)


def _setup_write_csv(monkeypatch, tmp_path):
    # treat the normal absolute path as if it were a relative path, so we can put
    # a prefix on it (this code is usually run in a container)
    original_csv_dir = tmp_path / locations.WAVEFORM_ORIGINAL_CSV.relative_to("/")
    monkeypatch.setattr(csv_writer, "WAVEFORM_ORIGINAL_CSV", original_csv_dir)
    monkeypatch.setattr(locations, "WAVEFORM_ORIGINAL_CSV", original_csv_dir)

    # the only precondition is that the base dir must exist
    original_csv_dir.parent.mkdir(parents=True, exist_ok=True)


def _check_written_csv(expected_filename, expected_text):
    # check that we can find the data again in its expected place
    expected_csv_path = locations.WAVEFORM_ORIGINAL_CSV / expected_filename
    assert os.path.exists(expected_csv_path)
    actual_text = expected_csv_path.read_text()
    assert actual_text == expected_text
