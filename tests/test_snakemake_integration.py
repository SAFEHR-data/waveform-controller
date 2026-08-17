import json
import os
import re
import shutil
from decimal import Decimal

import pyarrow as pa
import pyarrow.parquet as pq
import subprocess
import time
from pathlib import Path

import pytest
from tests.helpers import TestFileDescription


def _run_compose(
    compose_file: Path, args: list[str], cwd: Path
) -> subprocess.CompletedProcess:
    # set project name so as not to interfere with images/containers the user might already have
    cmd = ["docker", "compose", "-p", "pytest", "-f", str(compose_file), *args]
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

REPO_ROOT = Path(__file__).resolve().parents[1]
COMPOSE_FILE = REPO_ROOT / "docker-compose.yml"


@pytest.fixture(scope="session", autouse=True)
def build_required_images():
    for image in ["waveform-exporter", "waveform-hasher"]:
        print(f"BUILDING {image}:")
        build_args = ["build", image]
        # Exporter needs the coverage optional extra so in-container measurement works.
        if image == "waveform-exporter":
            build_args = ["build", "--build-arg", "INSTALL_COVERAGE=1", image]
        result = _run_compose(COMPOSE_FILE, build_args, cwd=REPO_ROOT)
        print(
            f"{image} build output:\nstdout:\n{result.stdout}\n"
            f"stderr:\n{result.stderr}END {image} build output [rc={result.returncode}]"
        )
        result.check_returncode()


def _make_test_input_csv(tmp_path, t: TestFileDescription) -> list[list[Decimal]]:
    original_csv_dir = tmp_path / "original-csv"
    csv_path = original_csv_dir / t.get_orig_csv()
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    secs_per_row = 1
    vals_per_row = t.sampling_rate * secs_per_row
    test_data = t.generate_data(vals_per_row)
    with open(csv_path, "w") as f:
        f.write(",".join(EXPECTED_COLUMN_NAMES) + "\n")
        start_time = t.start_timestamp
        row_time = start_time
        for td in test_data:
            row_values_str = ", ".join(str(v) for v in td)
            f.write(
                f'{t.csn},{t.mrn},{t.variable_id},{t.channel_id},{t.units},{t.sampling_rate},{row_time},{t.location},"[{row_values_str}]"\n'
            )
            row_time += secs_per_row
    # The test input CSV file needs to be old enough so that snakemake doesn't skip it
    old_time = time.time() - (10 * 60)
    os.utime(csv_path, (old_time, old_time))
    return test_data


@pytest.fixture(scope="function")
def background_hasher():
    # run hasher in background
    _run_compose(
        COMPOSE_FILE,
        [
            "up",
            "-d",
            # Assume Azure envs will come from config file
            "waveform-hasher",
        ],
        cwd=REPO_ROOT,
    ).check_returncode()
    yield
    # print hasher logs whether failed or not
    result = _run_compose(
        COMPOSE_FILE,
        [
            "logs",
            "--no-color",
            "waveform-hasher",
        ],
        cwd=REPO_ROOT,
    )
    print(f"waveform-hasher logs:\n{result.stdout}\n{result.stderr}")
    _run_compose(
        COMPOSE_FILE,
        [
            "down",
            "waveform-hasher",
        ],
        cwd=REPO_ROOT,
    ).check_returncode()


def test_snakemake_pipeline(tmp_path: Path, background_hasher):
    # ARRANGE

    # all fields that need to be de-IDed should contain the string "SECRET" so we can search for it later
    file1 = TestFileDescription(
        "2025-01-01",
        1735740780.0,
        "SECRET_CSN_1234",
        "SECRET_MRN_12345",
        "SECRET_LOCATION_123",
        "11",
        "3",
        100,
        "uV",
        5,
    )
    # same day, same CSN, earlier time
    file2 = TestFileDescription(
        "2025-01-01",
        1735740765.0,
        "SECRET_CSN_1234",
        "SECRET_MRN_12345",
        "SECRET_LOCATION_123",
        "27",
        "noCh",
        50,
        "uV",
        2,
    )
    # same day, different CSN
    file3 = TestFileDescription(
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
    # new day, first CSN again
    file4 = TestFileDescription(
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
    test_data_files = []
    for f in [file1, file2, file3, file4]:
        test_data_values = _make_test_input_csv(tmp_path, f)
        test_data_files.append((f, test_data_values))

    expected_hash_summaries = {
        "2025-01-01": [
            {
                "csn": file1.csn,
                "hashed_csn": file1.get_hashed_csn(),
                "min_timestamp": file2.start_timestamp,
                "max_timestamp": (
                    file1.start_timestamp + file1.num_rows - 1
                ),  # one sec per row
            },
            {
                "csn": file3.csn,
                "hashed_csn": file3.get_hashed_csn(),
                "min_timestamp": file3.start_timestamp,
                "max_timestamp": (
                    file3.start_timestamp + file3.num_rows - 1
                ),  # one sec per row
            },
        ],
        "2025-01-02": [
            {
                "csn": file4.csn,
                "hashed_csn": file4.get_hashed_csn(),
                "min_timestamp": file4.start_timestamp,
                "max_timestamp": (
                    file4.start_timestamp + file4.num_rows - 1
                ),  # one sec per row
            }
        ],
    }

    # ACT
    _run_snakemake(tmp_path)

    # ASSERT (data files)
    for filename, expected_data in test_data_files:
        original_parquet_path = (
            tmp_path / "original-parquet" / filename.get_orig_parquet()
        )
        pseudon_path = tmp_path / "pseudonymised" / filename.get_pseudon_parquet()

        assert original_parquet_path.exists()
        assert pseudon_path.exists()

        _compare_original_parquet_to_expected(original_parquet_path, expected_data)
        _compare_parquets(original_parquet_path, pseudon_path)
        # check metadata showing the instance name is in both parquet files
        expected_metadata = {"instance_name": "pytest"}
        _assert_parquet_footer_waveform_metadata(pseudon_path, expected_metadata)
        _assert_parquet_footer_waveform_metadata(
            original_parquet_path, expected_metadata
        )

    # ASSERT (hash summaries)
    # Hash summaries are one per day, not per input file
    for datestr, expected_summary in expected_hash_summaries.items():
        expected_path = tmp_path / "hash-lookups" / datestr / f"{datestr}.hashes.json"
        actual_hash_lookup_data = json.loads(expected_path.read_text())
        assert isinstance(actual_hash_lookup_data, list)
        # sort order to match expected
        actual_hash_lookup_data.sort(key=lambda x: x["csn"])
        assert expected_summary == actual_hash_lookup_data

    # check no extraneous files
    expected_file_counts = {"2025-01-01": 3, "2025-01-02": 1}
    _assert_date_partitioned_files(tmp_path / "original-csv", expected_file_counts)
    _assert_date_partitioned_files(tmp_path / "original-parquet", expected_file_counts)
    _assert_date_partitioned_files(tmp_path / "pseudonymised", expected_file_counts)
    _assert_date_partitioned_files(
        tmp_path / "hash-lookups", {"2025-01-01": 1, "2025-01-02": 1}
    )


def _assert_date_partitioned_files(
    base_dir: Path, expected_file_counts: dict[str, int]
):
    base_dir_items = list(base_dir.iterdir())
    # no files directly in the base dir, all are subdirs
    assert not any(i.is_file() for i in base_dir_items)
    assert len(base_dir_items) == len(expected_file_counts)
    for date_str, expected_count in expected_file_counts.items():
        date_dir_items = list((base_dir / date_str).iterdir())
        # no subdirs, only files
        assert not any(i.is_dir() for i in date_dir_items)
        assert expected_count == len(date_dir_items)


def _collect_docker_coverage(coverage_dir: Path) -> None:
    """Copy in-container coverage data next to pytest-cov's files for session combine."""
    # Replace any previous docker shards so a later `coverage combine` cannot
    # mix stale runs.
    for stale in REPO_ROOT.glob(".coverage.docker.*"):
        stale.unlink(missing_ok=True)

    files = [
        f
        for f in coverage_dir.iterdir()
        if f.is_file() and f.name.startswith(".coverage")
    ]
    if not files:
        print(
            "WARNING: no coverage data from Docker. Rebuild waveform-exporter "
            "with INSTALL_COVERAGE=1 (tests do this via build_required_images)."
        )
        return
    for i, src in enumerate(files):
        dest = REPO_ROOT / f".coverage.docker.{os.getpid()}.{i}"
        shutil.copy(src, dest)
        print(f"Collected Docker coverage data: {src.name} -> {dest.name}")


def _run_snakemake(tmp_path):
    # Config is a right pain. The exporter has a blank environment because it's launched by cron, so
    # nothing passed in as an env var will be seen.
    # It works around this in normal use by reading env vars only from the bind-mounted exporter.env file.
    # So to use a different config during test, we must override that file with a special version
    # that we create here.
    # Note that since we bypass cron here, any config on your dev machine will be picked up and then
    # overwritten by what is below. Therefore, you should explicitly set values below even if you only
    # want the default value to be used.
    tmp_exporter_env_path = tmp_path / "config/exporter.env"
    tmp_exporter_env_path.parent.mkdir(exist_ok=True)
    tmp_exporter_env_path.write_text(
        "SNAKEMAKE_RULE_UNTIL=all_daily_hash_lookups\n"
        "SNAKEMAKE_CORES=1\n"
        "INSTANCE_NAME=pytest\n"
        "CSV_AGE_THRESHOLD_MINUTES=5\n"
        "ONLY_USE_CSV_FROM_YESTERDAY=False\n"
        "PROCESS_CSV_FROM_DATE=\n"
    )

    # Collect coverage from Python processes inside the exporter container
    # (snakemake + rule bodies). Config is the same pyproject.toml as the host;
    # COVERAGE_FILE redirects the data onto the pytest bind mount.
    # https://coverage.readthedocs.io/en/latest/subprocess.html
    coverage_dir = tmp_path / "coverage-data"
    coverage_dir.mkdir(exist_ok=True)

    # run system under test (exporter container) in foreground
    compose_args = [
        "run",
        "--rm",
        # we override the volume defined in the compose file to be the pytest tmp path
        "-v",
        f"{tmp_path}:/waveform-export",
        # feed in our special config file
        "-v",
        f"{tmp_exporter_env_path}:/config/exporter.env:ro",
        # Auto-start coverage in every Python process in the container
        "-e",
        "COVERAGE_PROCESS_START=/app/pyproject.toml",
        "-e",
        "COVERAGE_FILE=/waveform-export/coverage-data/.coverage",
        "--entrypoint",
        "/app/exporter-scripts/scheduled-script.sh",
        "waveform-exporter",
    ]
    result = _run_compose(
        COMPOSE_FILE,
        compose_args,
        cwd=REPO_ROOT,
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
    _collect_docker_coverage(coverage_dir)


def _compare_original_parquet_to_expected(original_parquet: Path, expected_test_values):
    # CSV should always match original parquet
    orig_parquet_file = pq.ParquetFile(original_parquet)
    orig_reader = orig_parquet_file.read()
    orig_all_values = orig_reader["values"].combine_chunks()
    expected_pa = pa.array(expected_test_values, type=orig_all_values.type)
    assert orig_all_values == expected_pa


def _compare_parquets(original_parquet_path: Path, pseudon_parquet_path: Path):
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
                re.match(r"[a-f0-9]{64}$", str(v)) for v in pseudon_all_values
            ), f"{pseudon_all_values} in column {column_name} does not appear to be a hash"
            # orig, all sensitive values contain SECRET
            assert all(
                "SECRET" in str(v) for v in orig_all_values
            ), f"{orig_all_values} in column {column_name} contains SECRET string"


def _assert_parquet_footer_waveform_metadata(
    parquet_path: Path, expected_values: dict[str, str]
):
    parquet_file = pq.ParquetFile(parquet_path)
    footer_metadata: dict[bytes, bytes] = parquet_file.metadata.metadata
    # top-level key that separates our metadata from pre-existing metadata from eg pandas
    expected_metadata_key = b"waveform_exporter"
    actual_metadata_dict = json.loads(
        footer_metadata[expected_metadata_key].decode("utf-8")
    )
    for expected_key, expected_val in expected_values.items():
        assert (
            expected_val == actual_metadata_dict[expected_key]
        ), f"{parquet_path} value mismatch"
    # no metadata items contain identifiers
    for actual_key, actual_val in actual_metadata_dict.items():
        assert "SECRET" not in actual_key
        assert "SECRET" not in actual_val
