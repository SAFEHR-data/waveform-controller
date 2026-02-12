from datetime import timedelta, datetime, timezone
from pathlib import Path

import pytest

import locations

import src.pipeline.utils as utils

from tests.helpers import TestFileDescription


def mock_do_hash(csn: str):
    return "no-hash"


def _make_test_input_csv(csv_dir: Path):
    files = []
    # today
    today = datetime.now(tz=timezone.utc).date()
    files.append(
        TestFileDescription(
            today.isoformat(),
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
            (today - timedelta(days=1)).isoformat(),
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
            (today - timedelta(days=2)).isoformat(),
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
            (today - timedelta(days=2)).isoformat(),
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
        csv_path = csv_dir / t.get_orig_csv()
        csv_path.parent.mkdir(parents=True, exist_ok=True)
        with open(csv_path, "w") as f:
            # for this test doesn't use the contents of the files, only their
            # filenames, so we'll save some processing by creating empty files.
            f.write("")
    return [f.get_orig_csv() for f in files]


@pytest.mark.parametrize(
    "process_only_yesterday, process_datestring, expected_file_indexes",
    [
        # with process only yesterday true we should return only the single file from yesterday
        (True, "", [1]),
        # with process only yesterday false and an empty process_datestring we should return all 4 files.
        (False, "", [0, 1, 2, 3]),
        # with process only yesterday false and process_datestring set to two days ago we should return the two files from two days ago
        (
            False,
            (datetime.now(tz=timezone.utc).date() - timedelta(days=2)).isoformat(),
            [2, 3],
        ),
    ],
)
def test_determine_eventual_outputs(
    tmp_path: Path,
    monkeypatch,
    process_only_yesterday,
    process_datestring,
    expected_file_indexes,
):
    original_csv_dir = tmp_path / locations.WAVEFORM_ORIGINAL_CSV.relative_to("/")
    expected_paths = _make_test_input_csv(original_csv_dir)
    monkeypatch.setattr(
        utils, "CSV_PATTERN", original_csv_dir / (locations.FILE_STEM_PATTERN + ".csv")
    )
    monkeypatch.setattr("src.pipeline.utils.hash_csn", mock_do_hash)
    csv_wait_time = timedelta(0)

    files, hash_to_csn = utils.determine_eventual_outputs(
        csv_wait_time, process_only_yesterday, process_datestring
    )
    assert {
        str(f.get_original_csv_path().relative_to(original_csv_dir)) for f in files
    } == {expected_paths[ex_i] for ex_i in expected_file_indexes}
