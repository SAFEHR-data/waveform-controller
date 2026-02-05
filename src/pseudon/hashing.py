import logging
from functools import lru_cache

import requests

import settings

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1000)
def do_hash(type_prefix: str, value: str):
    """Pass data to the hasher API for de-identification purposes.

    Not that I think this will happen in practice, but we'd want the CSN "1234" to hash
    to a different value than the MRN "1234", so prefix each value with its type.
    """

    project_slug = "waveform-exporter"
    full_value_to_hash = f"{type_prefix}:{value}"

    hasher_hostname = settings.HASHER_API_HOSTNAME
    hasher_port = settings.HASHER_API_PORT
    hasher_req_url = f"http://{hasher_hostname}:{hasher_port}/hash"
    request_params: dict[str, str | int] = {
        "project_slug": project_slug,
        "message": full_value_to_hash,
    }
    # do we need to specify a particular hash length?
    # request_params["length"] = hash_len

    response = requests.get(hasher_req_url, params=request_params)
    logger.debug("RESPONSE = {}", response.text)
    response.raise_for_status()
    real_hash = response.text
    return real_hash
