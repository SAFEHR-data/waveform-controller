from functools import lru_cache


@lru_cache
def do_hash(type_prefix, value: str):
    """Stub implementation of deidentification function for testing purposes.

    Not that I think this will happen in practice, but we'd want the CSN
    "1234" to hash to a different value than the MRN "1234", so prefix
    each value with its type.
    """
    SALT = "waveform-exporter"
    full_value_to_hash = f"{SALT}:{type_prefix}:{value}"
    hash_str = f"{hash(full_value_to_hash) & 0xFFFFFFFF:08x}"
    return hash_str
