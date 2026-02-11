from datetime import timedelta
from pathlib import Path

import pytest
import locations

import src.pipeline.utils as utils

from tests.helpers import TestFileDescription


def mock_do_hash(csn: str):
    return "no-hash"


def _make_test_input_csv(tmp_path):
    files = []
    files.append(
        TestFileDescription(
            "2025-01-01",
            1735740783.0,
            "SECRET_CSN_1235",
            "SECRET_MRN_12346",
            "SECRET_LOCATION_123",
            "27",
            "noCh",
            50,
            "uV",
            4,
        )
    )
    # new day, first CSN again
    files.append(
        TestFileDescription(
            "2025-01-02",
            1735801965.0,
            "SECRET_CSN_1234",
            "SECRET_MRN_12345",
            "SECRET_LOCATION_123",
            "27",
            "noCh",
            50,
            "uV",
            5,
        )
    )

    for t in files:
        original_csv_dir = tmp_path / "original-csv"
        csv_path = original_csv_dir / t.get_orig_csv()
        csv_path.parent.mkdir(parents=True, exist_ok=True)
        with open(csv_path, "w") as f:
            f.write("")


def test_determine_eventual_outputs(tmp_path: Path, monkeypatch):
    _make_test_input_csv(tmp_path)
    original_csv_dir = tmp_path / locations.WAVEFORM_ORIGINAL_CSV.relative_to("/")
    monkeypatch.setattr(
        utils,
        "CSV_PATTERN",
        original_csv_dir / "{date}.{csn}.{variable_id}.{channel_id}.{units}.csv",
    )
    monkeypatch.setattr("src.pipeline.utils.hash_csn", mock_do_hash)
    csv_wait_time = timedelta(minutes=5)
    print(utils.determine_eventual_outputs(csv_wait_time))
    assert False
