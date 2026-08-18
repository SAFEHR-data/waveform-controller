import math
from dataclasses import dataclass
from decimal import Decimal
import random
from stablehash import stablehash


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
        return f"{self.date}/{self.date}.{self.csn}.{self.variable_id}.{self.channel_id}.{self.units}.csv"

    def get_orig_parquet(self):
        return f"{self.date}/{self.date}.{self.csn}.{self.variable_id}.{self.channel_id}.{self.units}.parquet"

    def get_pseudon_parquet(self):
        return f"{self.date}/{self.date}.{self.get_hashed_csn()}.{self.variable_id}.{self.channel_id}.{self.units}.parquet"

    def get_pseudon_ehr(self):
        return f"{self.date}/{self.date}.{self.get_hashed_csn()}_ehr.csv"

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
