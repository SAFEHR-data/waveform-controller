import json
import math
import os
import re
from dataclasses import dataclass
from decimal import Decimal
import random

import pyarrow as pa
import pyarrow.parquet as pq
import subprocess
import time
from pathlib import Path

import pytest
from stablehash import stablehash


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
        result = _run_compose(COMPOSE_FILE, ["build", image], cwd=REPO_ROOT)
        print(
            f"{image} build output:\nstdout:\n{result.stdout}\n"
            f"stderr:\n{result.stderr}END {image} build output [rc={result.returncode}]"
        )
        result.check_returncode()


@dataclass
class TestFileDescription:
    __test__ = False
    date: str
    start_timestamp: float
    csn: str
    mrn: str
    location: str
    variable_id: str
    channel_id: str
    sampling_rate: int
    units: str
    num_rows: int
    _test_values: list = None

    def get_hashed_csn(self):
        """This test runs outside of a docker container and the hasher doesn't expose a
        fixed port, so is somewhat hard to find.

        Easier to just hard code the CSNs since we have a limited set of input CSNs. We
        are defining expected values here; the test exporter will still use the test
        hasher to generate the actual values.
        """
        static_lookup = {
            # These hashes are not secrets, they're keyed hashes of the input values
            "SECRET_CSN_1234": "253d32c67e0d5aa4cdc7e9fc8442710dee8338c92abc3b905ab4b2f03194fc7e",  # pragma: allowlist secret
            "SECRET_CSN_1235": "ea2fda353f54926ae9d43fbc0ff4253912c250a137e9bd38bed860abacfe03ef",  # pragma: allowlist secret
        }
        try:
            return static_lookup[self.csn]
        except KeyError as e:
            # See develop.md "Manual hash lookup" if you need to add value
            raise KeyError(
                f"Unknown CSN '{self.csn}' passed to static get_hashed_csn(). "
                f"You may need to manually add the known hash for your CSN. See docs for details."
            ) from e

    def get_orig_csv(self):
        return f"{self.date}.{self.csn}.{self.variable_id}.{self.channel_id}.{self.units}.csv"

    def get_orig_parquet(self):
        return f"{self.date}.{self.csn}.{self.variable_id}.{self.channel_id}.{self.units}.parquet"

    def get_pseudon_parquet(self):
        return f"{self.date}.{self.get_hashed_csn()}.{self.variable_id}.{self.channel_id}.{self.units}.parquet"

    def get_hashes(self):
        return f"{self.date}.hashes.json"

    def get_stable_hash(self):
        """To aid in generating different but repeatable test data for each file."""
        return stablehash(
            (
                self.date,
                self.csn,
                self.mrn,
                self.location,
                self.variable_id,
                self.channel_id,
            )
        )

    def get_stable_seed(self):
        byte_hash = self.get_stable_hash().digest()[:4]
        return int.from_bytes(byte_hash)

    def generate_data(self, vals_per_row: int) -> list[list[Decimal]]:
        if self._test_values is None:
            seed = self.get_stable_seed()
            rng = random.Random(seed)
            base_ampl = rng.normalvariate(1, 0.2)
            base_offset = rng.normalvariate(0, 0.2)
            self._test_values = []
            for row_num in range(self.num_rows):
                values_row = [
                    Decimal.from_float(
                        base_ampl * math.sin(base_offset + row_num * vals_per_row + i)
                    ).quantize(Decimal("1.0000"))
                    for i in range(vals_per_row)
                ]
                self._test_values.append(values_row)
        # return as string but keep the numerical representation for comparison to parquet later
        return self._test_values


def _make_test_input_csv(tmp_path, t: TestFileDescription) -> list[list[Decimal]]:
    original_csv_dir = tmp_path / "original-csv"
    original_csv_dir.mkdir(parents=True, exist_ok=True)
    csv_path = original_csv_dir / t.get_orig_csv()
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
        _compare_parquets(expected_data, original_parquet_path, pseudon_path)
        # check metadata showing the instance name is in both parquet files
        expected_data = {"instance_name": "pytest"}
        _assert_parquet_footer_metadata(pseudon_path, expected_data)
        _assert_parquet_footer_metadata(original_parquet_path, expected_data)

    # ASSERT (hash summaries)
    # Hash summaries are one per day, not per input file
    for datestr, expected_summary in expected_hash_summaries.items():
        expected_path = tmp_path / "hash-lookups" / f"{datestr}.hashes.json"
        actual_hash_lookup_data = json.loads(expected_path.read_text())
        assert isinstance(actual_hash_lookup_data, list)
        # sort order to match expected
        actual_hash_lookup_data.sort(key=lambda x: x["csn"])
        assert expected_summary == actual_hash_lookup_data

    # check no extraneous files
    assert 4 == len(list((tmp_path / "original-csv").iterdir()))
    assert 4 == len(list((tmp_path / "original-parquet").iterdir()))
    assert 4 == len(list((tmp_path / "pseudonymised").iterdir()))
    assert 2 == len(list((tmp_path / "hash-lookups").iterdir()))


def _run_snakemake(tmp_path):
    # Config is a right pain. The exporter has a blank environment because it's launched by cron, so
    # nothing passed in as an env var will be seen.
    # It works around this in normal use by reading env vars only from the bind-mounted exporter.env file.
    # So to use a different config during test, we must override that file with a special version
    # that we create here.
    tmp_exporter_env_path = tmp_path / "config/exporter.env"
    tmp_exporter_env_path.parent.mkdir(exist_ok=True)
    tmp_exporter_env_path.write_text(
        "SNAKEMAKE_RULE_UNTIL=all_daily_hash_lookups\n"
        "SNAKEMAKE_CORES=1\n"
        "INSTANCE_NAME=pytest\n"
    )
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


def _compare_original_parquet_to_expected(original_parquet: Path, expected_test_values):
    # CSV should always match original parquet
    orig_parquet_file = pq.ParquetFile(original_parquet)
    orig_reader = orig_parquet_file.read()
    orig_all_values = orig_reader["values"].combine_chunks()
    expected_pa = pa.array(expected_test_values, type=orig_all_values.type)
    assert orig_all_values == expected_pa


def _compare_parquets(
    expected_test_values, original_parquet_path: Path, pseudon_parquet_path: Path
):
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


def _assert_parquet_footer_metadata(
    parquet_path: Path, expected_values: dict[str, str]
):
    parquet_file = pq.ParquetFile(parquet_path)
    footer_metadata: dict[bytes, bytes] = parquet_file.metadata.metadata
    # top-level key that separates our metadata from pre-existing metadata from eg pandas
    expected_metadata_key = b"waveform_metadata"
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
