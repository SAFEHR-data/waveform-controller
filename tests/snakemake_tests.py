from datetime import timedelta, datetime
from pathlib import Path

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

    # from yesterday
    files.append(
        TestFileDescription(
            datetime.strftime(datetime.now() - timedelta(1), "%Y-%m-%d"),
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
    # two files from 2 days ago
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
    files.append(
        TestFileDescription(
            datetime.strftime(datetime.now() - timedelta(2), "%Y-%m-%d"),
            1735801965.0,
            "SECRET_CSN_1234",
            "SECRET_MRN_12345",
            "SECRET_LOCATION_123",
            "27",
            "14",
            50,
            "uV",
            4,
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
    # with process only yesterday true we should return only the single file from yesterday
    process_only_yesterday = True
    process_datestring = ""
    files, hash_to_csn = utils.determine_eventual_outputs(
        csv_wait_time, process_only_yesterday, process_datestring
    )
    assert len(files) == 1
    # with process only yesterday false and an empty process_datestring we should return all 4 files.
    process_only_yesterday = False
    process_datestring = ""
    files, hash_to_csn = utils.determine_eventual_outputs(
        csv_wait_time, process_only_yesterday, process_datestring
    )
    assert len(files) == 4
    # with process only yesterday false and process_datestring set to two days ago we should return the two files from two days ago
    process_only_yesterday = False
    process_datestring = datetime.strftime(datetime.now() - timedelta(2), "%Y-%m-%d")
    files, hash_to_csn = utils.determine_eventual_outputs(
        csv_wait_time, process_only_yesterday, process_datestring
    )
    assert len(files) == 2
