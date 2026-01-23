from functools import lru_cache
from stablehash import stablehash


@lru_cache
def do_hash(type_prefix: str, value: str):
    """Stub implementation of deidentification function for testing purposes.

    Not that I think this will happen in practice, but we'd want the CSN "1234" to hash
    to a different value than the MRN "1234", so prefix each value with its type.
    """
    # Full implementation of issue #6 must remove this code and call the real hasher!!
    SALT = "waveform-exporter"
    full_value_to_hash = f"{SALT}:{type_prefix}:{value}"
    full_hash = stablehash(full_value_to_hash).hexdigest()
    tiny_hash = full_hash[:8]
    return tiny_hash
