from datetime import timedelta, datetime
from pathlib import Path

import pytest
import locations

import src.pipeline.utils as utils

from tests.helpers import TestFileDescription


def mock_do_hash(csn: str):
    return "no-hash"


def _make_test_input_csv(tmp_path):
    files = []
    # today
    files.append(
        TestFileDescription(
            datetime.strftime(datetime.now(), "%Y-%m-%d"),
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

    # yesterday
    files.append(
        TestFileDescription(
            datetime.strftime(datetime.now() - timedelta(1), "%Y-%m-%d"),
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
    # two days ago, first CSN again
    files.append(
        TestFileDescription(
            datetime.strftime(datetime.now() - timedelta(2), "%Y-%m-%d"),
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
        original_csv_dir = tmp_path / "waveform-export/original-csv"
        csv_path = original_csv_dir / t.get_orig_csv()
        csv_path.parent.mkdir(parents=True, exist_ok=True)
        with open(csv_path, "w") as f:
            # for this test doesn't use the contents of the files, only their
            # filenames, so we'll save some processing by creating empty files.
            f.write("")


def test_determine_eventual_outputs(tmp_path: Path, monkeypatch):
    _make_test_input_csv(tmp_path)
    original_csv_dir = tmp_path / locations.WAVEFORM_ORIGINAL_CSV.relative_to("/")
    monkeypatch.setattr(
        utils,
        "CSV_PATTERN",
        original_csv_dir / "{date}/{date}.{csn}.{variable_id}.{channel_id}.{units}.csv",
    )
    monkeypatch.setattr("src.pipeline.utils.hash_csn", mock_do_hash)
    csv_wait_time = timedelta(0)
    files, hash_to_csn = utils.determine_eventual_outputs(csv_wait_time, True)
    assert len(files) == 1
    files, hash_to_csn = utils.determine_eventual_outputs(csv_wait_time, False)
    assert len(files) == 3
