import logging

from datetime import datetime, timedelta, timezone
import pandas as pd

from db_mssql import caboodleDB
from db_pg import starDB
from locations import (
    make_file_name,
    EHR_STEM_PATTERN_HASHED,
    WAVEFORM_PSEUDONYMISED_PARQUET,
)
from pseudon.pseudon import pseudonymise_relevant_columns, write_ehr_parquet


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

    # When waveform data is grouped into days, it's always in UTC, so calculate the day
    # boundaries as UTC.
    utc_start_datetime = datetime.strptime(date_str, "%Y-%m-%d").replace(
        tzinfo=timezone.utc
    )
    utc_end_datetime = utc_start_datetime + timedelta(days=1)

    # we need hospital visit id for flowsheet and lab_result queries
    hospital_visit_id = star_connection.get_hospital_visit_from_csn(original_csn)

    # fetch data from caboodle
    airways = caboodle_connection.get_airway(
        utc_start_datetime, utc_end_datetime, original_csn
    )

    secretions = caboodle_connection.get_sputum_secretions(
        utc_start_datetime, utc_end_datetime, original_csn
    )

    # delete csn once we no longer need it
    del original_csn

    # fetch data from Emap
    flowsheet_values = star_connection.get_flowsheets(
        utc_start_datetime, utc_end_datetime, hospital_visit_id
    )

    lab_results = star_connection.get_lab_results(
        utc_start_datetime, utc_end_datetime, hospital_visit_id
    )

    ehr_data = pd.concat([airways, secretions, flowsheet_values, lab_results])

    # we can pseudonymise to safe, although at the moment all columns
    # are considered safe
    safe_columns = [
        "TubeEventId",
        "TubeDateTimeRecorded",
        "TubePlacementInstant",
        "TubeRemovalInstant",
        "TubeSize",
        "SecrDateTimeRecorded",
        "SecrSecretions",
        "SecrSputum",
        # Free text comments could in principle contain sensitive information but
        # we have assessed this particular column to be low risk
        "SecrComments",
        "Repositioned",
        "Position frequency",
        "FlowsheetDateTimeRecorded",
        "FlowsheetTemperature",
        "FlowsheetNoradrenaline",
        "FlowsheetMetaraminol",
        "FlowsheetPaO2",
        "FlowsheetPaCO2",
        "FlowsheetUnits",
        "LabDateTimeRecorded",
        "LabUnits",
        "LabCRP",
        "LabWCC",
    ]

    ehr_data = pseudonymise_relevant_columns(ehr_data, safe_columns)
    print(ehr_data.columns)
    print(ehr_data)
    t = ehr_data["FlowsheetTemperature"].iloc[0]
    print(f"({type(t)}) {t}")

    subs_dict = dict(date=date_str, hashed_csn=hashed_csn)
    stem = make_file_name(EHR_STEM_PATTERN_HASHED, subs_dict)
    filename = WAVEFORM_PSEUDONYMISED_PARQUET / f"{stem}.ehr.csv"
    filename.parent.mkdir(exist_ok=True, parents=True)

    write_ehr_parquet(ehr_data, filename)
