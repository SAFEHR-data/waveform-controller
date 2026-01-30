import json
import os
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
    if result.returncode != 0:
        pytest.fail(
            "docker compose build waveform-exporter failed\n"
            f"stdout:\n{result.stdout}\n"
            f"stderr:\n{result.stderr}"
        )


def test_snakemake_pipeline_runs_via_exporter_wrapper(tmp_path: Path):
    repo_root = Path(__file__).resolve().parents[1]
    compose_file = repo_root / "docker-compose.yml"

    exporter_config_file = repo_root.parent / "config" / "exporter.env"
    # This is mainly needed for Github actions because the docker-compose file requires the
    # config file to exist, but be gentle because this might also be your development area!
    # Empty is fine, actual config is passed through on the command line later.
    exporter_config_file.parent.mkdir(exist_ok=True)
    exporter_config_file.touch()

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
    if result.returncode != 0:
        pytest.fail(
            "docker compose run waveform-exporter failed\n"
            f"stdout:\n{result.stdout}\n"
            f"stderr:\n{result.stderr}"
        )

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
    _check_parquet(pseudon_path, allow_no_secrets=True)
    _check_parquet(original_parquet_path, allow_no_secrets=False)


def _check_parquet(parquet_path: Path, allow_no_secrets=True):
    parquet_file = pq.ParquetFile(parquet_path)
    column_names = parquet_file.schema_arrow.names
    assert column_names == EXPECTED_COLUMN_NAMES
    reader = parquet_file.read()
    for column_name in column_names:
        all_values = reader[column_name].combine_chunks()
        if allow_no_secrets:
            assert not any(
                ("SECRET" in str(v) for v in all_values)
            ), f"{all_values} in column {column_name} contains SECRET string"
