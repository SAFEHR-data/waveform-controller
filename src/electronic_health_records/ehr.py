import logging

from datetime import datetime, timedelta
import pandas as pd

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

    # we need hospital visit id for flowsheet and lab_result queries
    hospital_visit_id = star_connection.get_hospital_visit_from_csn(original_csn)

    # fetch data from caboodle
    airflow = caboodle_connection.get_airflow(
        start_datetime, end_datetime, original_csn
    )

    flowsheet_values = star_connection.get_flowsheets(
        start_datetime, end_datetime, hospital_visit_id
    )

    lab_results = star_connection.get_lab_results(
        start_datetime, end_datetime, hospital_visit_id
    )

    ehr_data = pd.concat([airflow, flowsheet_values, lab_results])

    # we can pseudonymise to safe, although at the moment all columns
    # are considered safe
    safe_columns = [
        "DateTimeRecorded",
        "PlacementInstant",
        "RemovalInstant",
        "TubeSize",
        "Temperature",
        "Noradrenaline",
        "Metaraminol",
        "Units",
        "Abnormal_result",
        "C-reactive protein 1",
        "CSF WCC TUBE 1",
        "CSF WCC TUBE 2",
        "CSF WCC TUBE 3",
        "C-reactive protein 2",
        "Comments",  # Free text comments could contain sensitive information. Should we hash it?
    ]

    ehr_data = pseudonymise_relevant_columns(ehr_data, safe_columns)

    write_ehr(ehr_data, date_str, hashed_csn)

    # delete csn once we no longer need it
    del original_csn
