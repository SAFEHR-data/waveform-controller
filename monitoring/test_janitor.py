import logging
import os
from collections import namedtuple
from datetime import timezone, datetime, timedelta
from pathlib import Path

import pytest
from unittest.mock import Mock
import janitor

logger = logging.getLogger(__name__)
InputTestFile = namedtuple("InputTestFile", ["id", "base", "path", "mtime"])


@pytest.fixture(scope="module")
def maybe_stale_files():
    now = datetime.now(timezone.utc)
    test_files = [
        InputTestFile(
            id=10,
            base="saved",
            path=Path(
                "20240912T08/UCHT03ICURM06/UCHT03ICURM06_20240912T0815Z_blah1.hl7archive.bz2"
            ),
            mtime=(now - timedelta(days=2.49)).timestamp(),
        ),
        InputTestFile(
            id=11,
            base="saved",
            path=Path(
                "20240912T08/UCHT03ICURM06/UCHT03ICURM06_20240912T0815Z_blah2.hl7archive.bz2"
            ),
            mtime=(now - timedelta(days=2.51)).timestamp(),
        ),
        InputTestFile(
            id=20,
            base="exp",
            path=Path("original-csv/2024-09-12/foo.parquet"),
            mtime=(now - timedelta(days=5.99)).timestamp(),
        ),
        InputTestFile(
            id=21,
            base="exp",
            path=Path("original-csv/2024-10-12/foo.parquet"),
            mtime=(now - timedelta(days=6.01)).timestamp(),
        ),
        InputTestFile(
            id=30,
            base="exp",
            path=Path("original-parquet/2024-09-12/foo.parquet"),
            mtime=(now - timedelta(days=7.99)).timestamp(),
        ),
        InputTestFile(
            id=31,
            base="exp",
            path=Path("original-parquet/2024-10-12/foo.parquet"),
            mtime=(now - timedelta(days=8.01)).timestamp(),
        ),
        InputTestFile(
            id=40,
            base="exp",
            path=Path("pseudonymised/2024-09-25/foo.parquet"),
            mtime=(now - timedelta(days=11.99)).timestamp(),
        ),
        InputTestFile(
            id=41,
            base="exp",
            path=Path("pseudonymised/2024-10-25/foo.parquet"),
            mtime=(now - timedelta(days=12.01)).timestamp(),
        ),
    ]
    # check files are not overlapping
    all_ids = [f.id for f in test_files]
    all_paths = [(f.base, f.path) for f in test_files]
    assert len(set(all_ids)) == len(all_ids)
    assert len(set(all_paths)) == len(all_paths)
    return test_files


@pytest.mark.parametrize(
    "dry_run",
    [True, False],
)
@pytest.mark.parametrize(
    [
        "hl7_thresh",
        "csv_thresh",
        "original_pq_thresh",
        "pseudo_thresh",
        "expected_files",
    ],
    [
        ("2.5", "6", "8.0", "12", {10, 20, 30, 40}),
        # empty variable means do not clean up that directory
        ("", "6", "8.0", "12", {10, 11, 20, 30, 40}),
        ("2.5", "", "8.0", "12", {10, 20, 21, 30, 40}),
        ("2.5", "6", "", "12", {10, 20, 30, 31, 40}),
        ("2.5", "6", "8.0", "", {10, 20, 30, 40, 41}),
        ("", "", "", "", {10, 11, 20, 21, 30, 31, 40, 41}),
    ],
)
def test_janitor(
    tmp_path_factory,
    maybe_stale_files,
    monkeypatch,
    dry_run,
    hl7_thresh,
    csv_thresh,
    original_pq_thresh,
    pseudo_thresh,
    expected_files: set[int],
):
    # check that all IDs expected are real, otherwise the test is not well-formed,
    assert expected_files.issubset(set([f.id for f in maybe_stale_files]))

    # setup
    os.environ["OTEL_SERVICE_NAME"] = "test-only"
    os.environ["OTEL_EXPORTER_OTLP_ENDPOINT"] = ""
    os.environ["ORIGINAL_CSV_RETENTION_DAYS"] = csv_thresh
    os.environ["ORIGINAL_PARQUET_RETENTION_DAYS"] = original_pq_thresh
    os.environ["PSEUDONYMISED_RETENTION_DAYS"] = pseudo_thresh
    os.environ["HL7_BZ2_ARCHIVE_RETENTION_DAYS"] = hl7_thresh
    export_dir = tmp_path_factory.mktemp("export")
    saved_hl7_dir = tmp_path_factory.mktemp("saved")

    def get_base_path(code):
        # these return values don't exist until the test has started
        if code == "exp":
            return export_dir
        elif code == "saved":
            return saved_hl7_dir
        else:
            raise AssertionError()

    for test_file in maybe_stale_files:
        base_dir = get_base_path(test_file.base)
        test_file_path = base_dir / test_file.path
        test_file_path.parent.mkdir(parents=True, exist_ok=True)
        test_file_path.write_text("whatever")
        os.utime(str(test_file_path), (test_file.mtime, test_file.mtime))

    monkeypatch.setattr(janitor, "WAVEFORM_EXPORT_DIR", export_dir)
    monkeypatch.setattr(janitor, "SAVED_MESSAGES_DIR", saved_hl7_dir)

    # run the janitor
    args = Mock()
    args.dry_run = dry_run
    janitor.main(args)

    # assert files got removed or not
    for test_file in maybe_stale_files:
        base_dir = get_base_path(test_file.base)
        test_file_full = base_dir / test_file.path
        file_actually_exists = test_file_full.exists()
        if dry_run:
            # dry run, so all files should still exist
            assert file_actually_exists
        else:
            if file_actually_exists:
                assert test_file.id in expected_files
            else:
                assert test_file.id not in expected_files
