import logging

from datetime import datetime, timedelta, timezone
import pandas as pd
from zoneinfo import ZoneInfo

from db_mssql import caboodleDB
from db_pg import starDB
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


HOSPITAL_TZ = ZoneInfo("Europe/London")


def utc_to_naive_local(utc_dt: datetime) -> datetime:
    return utc_dt.astimezone(HOSPITAL_TZ).replace(tzinfo=None)


def naive_local_to_utc(naive_dt: datetime) -> datetime:
    return naive_dt.replace(tzinfo=HOSPITAL_TZ).astimezone(timezone.utc)


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

    # When waveform data is grouped into days, it's always in UTC, so calculate the day
    # boundaries as UTC.
    # However, Caboodle stores its timestamps as timezone-naive SQL types
    # (`datetime` in SQL Server) that represent the local time of the hospital.
    # This is not necessarily the same as our system timezone, and should
    # be configured independently!
    # The behaviour of your DB driver is relevant here:
    # https://learn.microsoft.com/en-us/sql/connect/python/mssql-python/datetime-handling?view=sql-server-ver17
    utc_start_datetime = datetime.strptime(date_str, "%Y-%m-%d").replace(
        tzinfo=timezone.utc
    )
    utc_end_datetime = utc_start_datetime + timedelta(days=1)
    local_start_datetime = utc_to_naive_local(utc_start_datetime)
    local_end_datetime = utc_to_naive_local(utc_end_datetime)

    # we need hospital visit id for flowsheet and lab_result queries
    hospital_visit_id = star_connection.get_hospital_visit_from_csn(original_csn)

    # fetch data from caboodle, which uses local naive timestamps
    airflow = caboodle_connection.get_airflow(
        local_start_datetime, local_end_datetime, original_csn
    )

    # Emap uses explicit UTC for its timestamps
    flowsheet_values = star_connection.get_flowsheets(
        utc_start_datetime, utc_end_datetime, hospital_visit_id
    )

    lab_results = star_connection.get_lab_results(
        utc_start_datetime, utc_end_datetime, hospital_visit_id
    )

    ehr_data = pd.concat([airflow, flowsheet_values, lab_results])

    # we can pseudonymise to safe, although at the moment all columns
    # are considered safe
    safe_columns = [
        "DateTimeRecorded",
        "PlacementInstant",
        "RemovalInstant",
        "TubeSize",
        "Repositioned",
        "Position frequency",
        "Temperature",
        "Noradrenaline",
        "Metaraminol",
        "PaO2",
        "PaCO2",
        "Secretions",
        "Sputum",
        "Units",
        "CRP",
        "WCC",
        "Comments",  # Free text comments could contain sensitive information. Should we hash it?
    ]

    ehr_data = pseudonymise_relevant_columns(ehr_data, safe_columns)

    write_ehr(ehr_data, date_str, hashed_csn)

    # delete csn once we no longer need it
    del original_csn
