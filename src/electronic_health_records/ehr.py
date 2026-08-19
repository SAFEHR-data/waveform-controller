import logging

from datetime import datetime, timedelta

from db import caboodleDB, starDB
from csv_writer import write_ehr
from pseudon.pseudon import pseudonymise_relevant_columns


def ehr_for_csv(date_str: str, original_csn: str, hashed_csn: str) -> None:
    """Extracts electronic healthcare records for a given csn and writes the results to
    a pseudonymised csv file for a single day.

    This is a privacy-sensitive area of code. Unhashed CSNs must not appear in uploaded
    files.
    :param date_str: the date to look up data for
    :param original_csn: the csn to base look up on.
    :param hashed_csn: the pseudonymised hash to use for file output.
    """

    caboodle_connection = caboodleDB()
    caboodle_connection.connect()

    star_connection = starDB()
    star_connection.connect()

    _ehr_for_csv(
        date_str, original_csn, hashed_csn, caboodle_connection, star_connection
    )


def _ehr_for_csv(
    date_str: str,
    original_csn: str,
    hashed_csn: str,
    caboodle_connection: caboodleDB,
    star_connection: starDB,
) -> None:
    # will pick up the logger config defined in the snakemake job (ie. log to file)
    logger = logging.getLogger(__name__)

    logger.info("Looking for airway data for %s.", hashed_csn)

    start_datetime = datetime.strptime(date_str, "%Y-%m-%d")
    end_datetime = start_datetime + timedelta(days=1)
    airflow = caboodle_connection.get_airflow(
        start_datetime, end_datetime, original_csn
    )

    hospital_visit = star_connection.get_hospital_visit_from_csn(original_csn)

    logger.info(hospital_visit)

    safe_columns = [
        "DateTimeRecorded",
        "PlacementInstant",
        "RemovalInstant",
        "TubeSize",
    ]

    airflow = pseudonymise_relevant_columns(airflow, safe_columns)

    write_ehr(airflow, date_str, hashed_csn)

    logger.info(airflow)

    # delete csn once we no longer need it
    del original_csn
