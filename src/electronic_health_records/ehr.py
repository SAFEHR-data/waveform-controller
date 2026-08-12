import functools
import logging

import pandas as pd
from datetime import datetime

from .hashing import do_hash
from db import caboodleDB


def ehr_for_csv(
    datetime: datetime,
    original_csn: str,
    hashed_csn: str,
    db_connection: caboodleDB,
) -> None:
    """Extracts electronic healthcare records for a given csn and writes the results to
    a pseudonymised csv file for a single day.

    This is a privacy-sensitive area of code. Unhashed CSNs must not appear in uploaded
    files.
    :param date_str: the date to look up data for
    :param original_csn: the csn to base look up on.
    :param hashed_csn: the pseudonymised hash to use for file output.
    :param db_connection: connection to the caboodle database.
    """
    # will pick up the logger config defined in the snakemake job (ie. log to file)
    logger = logging.getLogger(__name__)

    caboodle = caboodleDB()
    caboodle.connect()

    logger.info("Looking for airway data for %s.", hashed_csn)

    start_datetime = datetime
    end_datetime = datetime
    airflow = caboodle.get_airflow(start_datetime, end_datetime, original_csn)
    airflow = pseudonymise_relevant_columns(airflow)
    logger.info(airflow)

    # delete csn once we no longer need it
    del original_csn


SAFE_COLUMNS = [
    "sampling_rate",
    "source_variable_id",
    "source_channel_id",
    "timestamp",
    "units",
    "values",
]


def pseudonymise_relevant_columns(df: pd.DataFrame):
    """ "csn", "mrn", "location" are examples of columns that must be pseudonymised.

    However, it's safer to list which columns *don't* need to be pseudonymised. Eg. you
    add a column but forget to consider whether it's sensitive, OR you rename one of the
    known sensitive columns and forget that this will cause privacy to break. This means
    that when you add a new column, you have to add it here if you don't want it to be
    hashed.
    """
    for col in df.columns:
        if col not in SAFE_COLUMNS:
            df[col] = df[col].apply(functools.partial(do_hash, col))
    return df
