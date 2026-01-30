import json
import os
import re

import pyarrow.parquet as pq
import subprocess
import time
from pathlib import Path

import pytest

from src.pseudon.hashing import do_hash


def _run_compose(
    compose_file: Path, args: list[str], cwd: Path
) -> subprocess.CompletedProcess:
    cmd = ["docker", "compose", "-f", str(compose_file), *args]
    return subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True)


EXPECTED_COLUMN_NAMES = [
    "csn",
    "mrn",
    "source_variable_id",
    "source_channel_id",
    "units",
    "sampling_rate",
    "timestamp",
    "location",
    "values",
]


@pytest.fixture(scope="session", autouse=True)
def build_exporter_image():
    repo_root = Path(__file__).resolve().parents[1]
    compose_file = repo_root / "docker-compose.yml"
    result = _run_compose(compose_file, ["build", "waveform-exporter"], cwd=repo_root)
    print(f"stdout:\n{result.stdout}\n" f"stderr:\n{result.stderr}")
    result.check_returncode()


def test_snakemake_pipeline_runs_via_exporter_wrapper(tmp_path: Path):
    repo_root = Path(__file__).resolve().parents[1]
    compose_file = repo_root / "docker-compose.yml"

    date = "2025-01-01"
    # all fields that need to be de-IDed should contain the string "SECRET" so we can search for it later!
    csn = "SECRET_CSN_1234"
    mrn = "SECRET_MRN_12345"
    loc = "SECRET_LOCATION_123"
    variable_id = "11"
    channel_id = "3"
    units = "uV"

    original_csv_dir = tmp_path / "original-csv"
    original_csv_dir.mkdir(parents=True, exist_ok=True)
    csv_path = original_csv_dir / f"{date}.{csn}.{variable_id}.{channel_id}.{units}.csv"
    csv_path.write_text(
        ",".join(EXPECTED_COLUMN_NAMES) + "\n"
        f'{csn},{mrn},{variable_id},{channel_id},{units},100,1769795156.0,{loc},"[1.0,2.0]"\n'
        f'{csn},{mrn},{variable_id},{channel_id},{units},100,1769795157.0,{loc},"[3.0, 4.0]"\n'
    )
    # The test input CSV file needs to be old enough so that snakemake doesn't skip it
    old_time = time.time() - (10 * 60)
    os.utime(csv_path, (old_time, old_time))

    compose_args = [
        "run",
        "--rm",
        # we override the volume defined in the compose file to be the pytest tmp path
        "-v",
        f"{tmp_path}:/waveform-export",
        "--entrypoint",
        "/app/exporter-scripts/scheduled-script.sh",
        "-e",
        "SNAKEMAKE_RULE_UNTIL=all_daily_hash_lookups",
        "-e",
        "SNAKEMAKE_CORES=1",
        "waveform-exporter",
    ]
    result = _run_compose(
        compose_file,
        compose_args,
        cwd=repo_root,
    )
    # for convenience print the snakemake log files if they exist (on success or error)
    outer_logs_dir = tmp_path / "snakemake-logs"
    outer_logs = sorted(outer_logs_dir.glob("snakemake-outer-log*.log"))
    if not outer_logs:
        print("No outer logs found")
    for ol in outer_logs:
        print(f"Log file {ol}:")
        print(ol.read_text())
    # print all output then raise if there was an error
    print(f"stdout:\n{result.stdout}\n" f"stderr:\n{result.stderr}")
    result.check_returncode()

    expected_hashed_csn = do_hash("csn", csn)
    original_parquet_path = (
        tmp_path
        / "original-parquet"
        / f"{date}.{csn}.{variable_id}.{channel_id}.{units}.parquet"
    )
    pseudon_path = (
        tmp_path
        / "pseudonymised"
        / f"{date}.{expected_hashed_csn}.{variable_id}.{channel_id}.{units}.parquet"
    )
    hash_lookup_path = tmp_path / "hash-lookups" / f"{date}.hashes.json"

    assert original_parquet_path.exists()
    assert pseudon_path.exists()
    assert hash_lookup_path.exists()

    # does our CSN -> hashed_csn
    hash_lookup = json.loads(hash_lookup_path.read_text())
    assert isinstance(hash_lookup, list)
    assert any(
        entry.get("csn") == csn and entry.get("hashed_csn") == expected_hashed_csn
        for entry in hash_lookup
    )
    _check_parquets(original_parquet_path, pseudon_path)


def _check_parquets(original_parquet_path: Path, pseudon_parquet_path: Path):
    # columns where we expect the values to differ due to pseudonymisation
    COLUMN_EXPECT_DIFFERENT = ["csn", "mrn", "location"]
    orig_parquet_file = pq.ParquetFile(original_parquet_path)
    pseudon_parquet_file = pq.ParquetFile(pseudon_parquet_path)
    column_names = orig_parquet_file.schema_arrow.names
    assert column_names == EXPECTED_COLUMN_NAMES
    assert column_names == pseudon_parquet_file.schema_arrow.names
    orig_reader = orig_parquet_file.read()
    pseudon_reader = pseudon_parquet_file.read()
    for column_name in column_names:
        orig_all_values = orig_reader[column_name].combine_chunks()
        pseudon_all_values = pseudon_reader[column_name].combine_chunks()
        # pseudonymised contains no secrets
        assert not any(
            ("SECRET" in str(v) for v in pseudon_all_values)
        ), f"{pseudon_all_values} in column {column_name} contains SECRET string"
        if column_name not in COLUMN_EXPECT_DIFFERENT:
            # no pseudon expected, should be identical
            assert orig_all_values == pseudon_all_values
        else:
            # pseudon expected, check that it looks like a hash
            assert all(
                # will need lengthening when we use real hashes!
                re.match(r"[a-f0-9]{8}$", str(v))
                for v in pseudon_all_values
            ), f"{pseudon_all_values} in column {column_name} does not appear to be a hash"
            # orig, all sensitive values contain SECRET
            assert all(
                "SECRET" in str(v) for v in orig_all_values
            ), f"{orig_all_values} in column {column_name} contains SECRET string"
