from datetime import timedelta

import pytest
import locations

import src.pipeline.utils as utils


def mock_do_hash(csn: str):
    return "no-hash"


def test_determine_eventual_outputs(monkeypatch):
    tmp_path = "../"
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
