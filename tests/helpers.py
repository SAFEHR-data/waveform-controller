import math
from dataclasses import dataclass
from decimal import Decimal
import random
from typing import Literal, Optional

from stablehash import stablehash

ValueKind = Literal["numeric", "string"]


@dataclass
class TestFileDescription:
    __test__ = False
    date: str
    start_timestamp: float
    csn: str
    mrn: str
    location: str
    variable_id: str
    channel_id: Optional[str]
    # None => low-frequency (no sampling rate in CSV)
    sampling_rate: Optional[int]
    units: str
    num_rows: int
    # Which values column is populated. String values are LF-only in these fixtures.
    value_kind: ValueKind = "numeric"
    _test_numeric_values: Optional[list] = None
    _test_string_values: Optional[list] = None

    def __post_init__(self):
        if self.value_kind == "string" and self.sampling_rate is not None:
            raise ValueError(
                "string value_kind is only supported for low-frequency data"
            )

    @property
    def is_low_freq(self) -> bool:
        return self.sampling_rate is None

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
        return f"{self.date}/{self.date}.{self.csn}.{self.variable_id}.{self.channel_id}.{self.units}.csv"

    def get_orig_parquet(self):
        return f"{self.date}/{self.date}.{self.csn}.{self.variable_id}.{self.channel_id}.{self.units}.parquet"

    def get_pseudon_parquet(self):
        return f"{self.date}/{self.date}.{self.get_hashed_csn()}.{self.variable_id}.{self.channel_id}.{self.units}.parquet"

    def get_hashes(self):
        return f"{self.date}/{self.date}.hashes.json"

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
                self.value_kind,
            )
        )

    def get_stable_seed(self):
        byte_hash = self.get_stable_hash().digest()[:4]
        return int.from_bytes(byte_hash)

    def generate_data(self) -> tuple[list, list]:
        """Return (numeric_rows, string_rows), each of length num_rows.

        Exactly one of the two lists has non-None row entries (lists of values); the
        other is all None. CSV serialization of None is handled by write_frame.
        """
        if self.value_kind == "string":
            string_rows = self._generate_lf_string_rows()
            return [None] * self.num_rows, string_rows
        if self.is_low_freq:
            numeric_rows = self._generate_lf_numeric_rows()
            return numeric_rows, [None] * self.num_rows
        vals_per_row = self.sampling_rate  # one second of samples per row
        numeric_rows = self._generate_hf_numeric_rows(vals_per_row)
        return numeric_rows, [None] * self.num_rows

    def _generate_hf_numeric_rows(self, vals_per_row: int) -> list[list[Decimal]]:
        if self._test_numeric_values is None:
            seed = self.get_stable_seed()
            rng = random.Random(seed)
            base_ampl = rng.normalvariate(1, 0.2)
            base_offset = rng.normalvariate(0, 0.2)
            self._test_numeric_values = []
            for row_num in range(self.num_rows):
                values_row = [
                    Decimal.from_float(
                        base_ampl * math.sin(base_offset + row_num * vals_per_row + i)
                    ).quantize(Decimal("1.0000"))
                    for i in range(vals_per_row)
                ]
                self._test_numeric_values.append(values_row)
        return self._test_numeric_values

    def _generate_lf_numeric_rows(self) -> list[list[Decimal]]:
        if self._test_numeric_values is None:
            seed = self.get_stable_seed()
            rng = random.Random(seed)
            self._test_numeric_values = [
                [Decimal.from_float(rng.uniform(0, 100)).quantize(Decimal("1.0000"))]
                for _ in range(self.num_rows)
            ]
        return self._test_numeric_values

    def _generate_lf_string_rows(self) -> list[list[str]]:
        if self._test_string_values is None:
            # Realistic categorical / free-text LF examples (incl. commas / colons)
            catalogue = [
                "Pressure Support / CPAP (PS)",
                "1:2",
                "Assist Control, Volume",
                "SIMV",
            ]
            seed = self.get_stable_seed()
            rng = random.Random(seed)
            self._test_string_values = [
                [rng.choice(catalogue)] for _ in range(self.num_rows)
            ]
        return self._test_string_values
