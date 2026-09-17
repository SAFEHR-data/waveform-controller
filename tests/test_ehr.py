from unittest.mock import Mock

import pandas as pd
import pytest

from db_mssql import caboodleDB
from db_pg import starDB, get_sql_query_with_schema
from datetime import datetime, timedelta, timezone
import pyarrow.parquet as pq
from db_utils import get_sql_query_text
from electronic_health_records.ehr import ehr_for_csv

import settings


@pytest.fixture(scope="function", autouse=True)
def patch_mock_get_rows(monkeypatch):
    """Replace the DB fetchers with simplified versions that just look at the query (but
    not the params) and returns some data with the right types/shape (as it comes from
    cursor.fetchall(), so it's already converted to Python types).

    This allows testing of some of the TZ conversion and EHR output writing files but
    doesn't test the DB behaviour (esp re TZ)

    These must be manually kept in step with the columns returned by the queries
    """

    def mock_get_rows_mssql(self, query, params):
        if query == get_sql_query_text("private/airway.sql"):
            col_names = [
                "TubeEventId",
                "TubeDateTimeRecorded",
                "TubePlacementInstant",
                "TubeRemovalInstant",
                "TubeSize",
            ]
            # this is based on the assumed data, not a real query
            # Assumptions:
            # * all return timezone-naive Python datetimes because that's what it is in the DB
            rows = [
                (
                    10,
                    datetime(2026, 9, 14, 3, 30),
                    datetime(2026, 9, 14, 3, 20),
                    # use a mix of summer and winter dates
                    datetime(2026, 11, 14, 5, 10),
                    "7 mm",
                ),
                (
                    20,
                    datetime(2026, 9, 14, 2, 31),
                    datetime(2026, 9, 14, 3, 21),
                    None,
                    "7.5 mm",
                ),
            ]
            return rows, col_names
        elif query == get_sql_query_text("private/sputum_secretions.sql"):
            col_names = [
                "SecrDateTimeRecorded",
                "SecrSecretions",
                "SecrSputum",
                "SecrComments",
            ]
            rows = [
                (
                    datetime(2026, 9, 14, 3, 30),
                    "Small",
                    None,
                    "",
                ),
                (
                    datetime(2026, 9, 14, 6, 30),
                    None,
                    "None",  # "None" as in no Sputum!
                    "",
                ),
            ]
            return rows, col_names
        else:
            raise ValueError(f"Caboodle query not recognised: {query}")

    def mock_get_rows_pg(self, query, params):
        if query == get_sql_query_with_schema("lab_results.sql", settings.SCHEMA_NAME):
            # this is based on real queries
            rows = [
                (
                    datetime(
                        2026, 9, 14, 6, 30, tzinfo=timezone(timedelta(seconds=3600))
                    ),
                    30.1,
                    None,
                    "mg/L",
                ),
                (
                    datetime(
                        2026, 9, 14, 6, 39, tzinfo=timezone(timedelta(seconds=3600))
                    ),
                    None,
                    30.21,
                    "x10^9/L",
                ),
            ]
            col_names = ["LabDateTimeRecorded", "LabCRP", "LabWCC", "LabUnits"]
            return rows, col_names
        elif query == get_sql_query_with_schema(
            "flow_sheet_values.sql", settings.SCHEMA_NAME
        ):
            col_names = [
                "FlowsheetDateTimeRecorded",
                "FlowsheetTemperature",
                "FlowsheetNoradrenaline",
                "FlowsheetMetaraminol",
                "FlowsheetPaO2",
                "FlowsheetPaCO2",
                "FlowsheetUnits",
            ]
            # example flowsheets, based on real queries
            rows = [
                # Noradrenaline (shouldn't there be a concentration or a time component to the unit?)
                (
                    datetime(
                        2026, 9, 14, 1, 2, tzinfo=timezone(timedelta(seconds=3600))
                    ),
                    None,
                    1.0,
                    None,
                    None,
                    None,
                    "mL",
                ),
                # Temperature (why no units?)
                (
                    datetime(
                        2026, 9, 14, 2, 5, tzinfo=timezone(timedelta(seconds=3600))
                    ),
                    97.5,
                    None,
                    None,
                    None,
                    None,
                    None,
                ),
            ]
            return rows, col_names
        elif query == get_sql_query_with_schema(
            "get_hospital_visit_id.sql", settings.SCHEMA_NAME
        ):
            rows = [
                (123456,),
            ]
            col_names = ["hospital_visit_id"]
            return rows, col_names
        else:
            raise ValueError(f"Star query not recognised: {query}")

    monkeypatch.setattr(caboodleDB, "connect", Mock())
    monkeypatch.setattr(caboodleDB, "_get_rows", mock_get_rows_mssql)
    monkeypatch.setattr(starDB, "connect", Mock())
    monkeypatch.setattr(starDB, "_get_rows", mock_get_rows_pg)


def test_ehr(monkeypatch, tmp_path):
    fake_abs_root = tmp_path.absolute()
    fake_waveform_pseudonymised_ehr = fake_abs_root / "pseudonymised"
    monkeypatch.setattr(
        "electronic_health_records.ehr.WAVEFORM_PSEUDONYMISED_PARQUET",
        fake_waveform_pseudonymised_ehr,
    )

    ehr_for_csv(date_str="2026-09-14", original_csn="SECRET1234", hashed_csn="fakehash")

    # just check the file contains something for now (it will be changing to parquet)
    expected_file = (
        fake_waveform_pseudonymised_ehr / "2026-09-14" / "2026-09-14.fakehash.ehr.csv"
    )
    assert expected_file.exists()

    ehr_data = pq.read_table(expected_file)
    assert ehr_data.num_rows == 8
    df = ehr_data.to_pandas(
        # in particular, stop ints from being loaded as floats if there are null values in the column
        types_mapper=pd.ArrowDtype
    )

    def non_null_vals(df, flowsheet_col) -> pd.DataFrame:
        return df[df[flowsheet_col].notna()][
            ["FlowsheetDateTimeRecorded", flowsheet_col, "FlowsheetUnits"]
        ]

    # always check against UTC
    actual_temps = non_null_vals(df, "FlowsheetTemperature")
    assert actual_temps.shape[0] == 1
    row0 = actual_temps.iloc[0]
    assert row0[0] == datetime(2026, 9, 14, 1, 5, tzinfo=timezone.utc)
    assert row0[1] == 97.5
    assert pd.isna(row0[2])

    actual_norad = non_null_vals(df, "FlowsheetNoradrenaline")
    assert actual_norad.shape[0] == 1
    assert tuple(actual_norad.iloc[0]) == (
        datetime(2026, 9, 14, 0, 2, tzinfo=timezone.utc),
        1.0,
        "mL",
    )

    actual_pa02 = non_null_vals(df, "FlowsheetPaO2")
    assert actual_pa02.shape[0] == 0

    actual_tube_events = df[df["TubeEventId"].notna()][
        [
            "TubeEventId",
            "TubeDateTimeRecorded",
            "TubePlacementInstant",
            "TubeRemovalInstant",
            "TubeSize",
        ]
    ]
    assert actual_tube_events.shape[0] == 2
    assert tuple(actual_tube_events.iloc[0]) == (
        10,
        datetime(2026, 9, 14, 2, 30, tzinfo=timezone.utc),
        datetime(2026, 9, 14, 2, 20, tzinfo=timezone.utc),
        datetime(2026, 11, 14, 5, 10, tzinfo=timezone.utc),
        "7 mm",
    )
    assert tuple(actual_tube_events.iloc[1].iloc[[0, 1, 2, 4]]) == (
        20,
        datetime(2026, 9, 14, 1, 31, tzinfo=timezone.utc),
        datetime(2026, 9, 14, 2, 21, tzinfo=timezone.utc),
        "7.5 mm",
    )
    assert pd.isna(actual_tube_events.iloc[1].iloc[3])

    # pd.testing.assert_frame_equal handles None/nan nicely, so use it
    # when values might be missing
    actual_secrs = df[df["SecrDateTimeRecorded"].notna()][
        ["SecrDateTimeRecorded", "SecrSecretions", "SecrSputum", "SecrComments"]
    ].reset_index(drop=True)
    pd.testing.assert_frame_equal(
        actual_secrs,
        pd.DataFrame(
            [
                (
                    datetime(2026, 9, 14, 2, 30, tzinfo=timezone.utc),
                    "Small",
                    None,
                    "",
                ),
                (
                    datetime(2026, 9, 14, 5, 30, tzinfo=timezone.utc),
                    None,
                    "None",
                    "",
                ),
            ],
            columns=actual_secrs.columns,
        ),
        check_dtype=False,
    )

    actual_labs = df[df["LabDateTimeRecorded"].notna()][
        ["LabDateTimeRecorded", "LabCRP", "LabWCC", "LabUnits"]
    ].reset_index(drop=True)

    pd.testing.assert_frame_equal(
        actual_labs,
        pd.DataFrame(
            [
                (
                    datetime(2026, 9, 14, 5, 30, tzinfo=timezone.utc),
                    30.1,
                    None,
                    "mg/L",
                ),
                (
                    datetime(2026, 9, 14, 5, 39, tzinfo=timezone.utc),
                    None,
                    30.21,
                    "x10^9/L",
                ),
            ],
            columns=actual_labs.columns,
        ),
        check_dtype=False,
    )
