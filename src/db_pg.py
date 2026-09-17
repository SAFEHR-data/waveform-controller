from datetime import datetime
from typing import Optional

import pandas as pd
import psycopg2
from psycopg2 import sql, pool
import logging

import settings as settings  # type:ignore
from db_utils import get_sql_query_text, validate_args_must_be_utc

logging.basicConfig(format="%(levelname)s:%(asctime)s: %(message)s")
logger = logging.getLogger(__name__)


def get_sql_query_with_schema(
    query_rel_path: str, schema_name: Optional[str] = None
) -> sql.Composable:
    query_text_tmpl = sql.SQL(get_sql_query_text(query_rel_path))
    if schema_name is None:
        return query_text_tmpl
    else:
        return query_text_tmpl.format(schema_name=sql.Identifier(schema_name))


class starDB:
    connection_string: str = "dbname={} user={} password={} host={} port={} connect_timeout={} options='-c statement_timeout={}'".format(
        settings.UDS_DBNAME,  # type:ignore
        settings.UDS_USERNAME,  # type:ignore
        settings.UDS_PASSWORD,  # type:ignore
        settings.UDS_HOST,  # type:ignore
        settings.UDS_PORT,  # type:ignore
        settings.UDS_CONNECT_TIMEOUT,  # type:ignore
        settings.UDS_QUERY_TIMEOUT,  # type:ignore
    )
    connection_pool: pool.SimpleConnectionPool

    def connect(self) -> None:
        self.connection_pool = pool.SimpleConnectionPool(1, 1, self.connection_string)

    def get_matched_mrn(
        self, location_string: str, observation_datetime: datetime
    ) -> tuple:
        validate_args_must_be_utc(observation_datetime)

        parameters = {
            "location_string": location_string,
            "observation_datetime": observation_datetime,
        }
        mrn_lookup_query = get_sql_query_with_schema(
            "mrn_based_on_bed_and_datetime.sql", settings.SCHEMA_NAME
        )

        rows, col_names = self._get_rows(mrn_lookup_query, parameters)

        num_rows = len(rows)
        if num_rows != 1:
            raise ValueError(
                f"Wrong number of rows returned from database. {num_rows} != 1, for {location_string}:{observation_datetime}"
            )

        return rows[0]

    def get_hospital_visit_from_csn(self, csn: str) -> int:
        hv_query = get_sql_query_with_schema(
            "get_hospital_visit_id.sql", settings.SCHEMA_NAME
        )

        parameters = {
            "csn": csn,
        }

        hospital_visit_rows, col_names = self._get_rows(hv_query, parameters)
        return int(hospital_visit_rows[0][0])

    def get_flowsheets(
        self,
        utc_start_datetime: datetime,
        utc_end_datetime: datetime,
        hospital_visit_id: int,
    ) -> pd.DataFrame:
        """Retrieve airflow data from database."""
        validate_args_must_be_utc(utc_start_datetime, utc_end_datetime)

        flowsheet_query = get_sql_query_with_schema(
            "flow_sheet_values.sql", settings.SCHEMA_NAME
        )

        parameters = {
            "start_datetime": utc_start_datetime,
            "end_datetime": utc_end_datetime,
            "hospital_visit_id": hospital_visit_id,
        }

        rows, col_names = self._get_rows(flowsheet_query, parameters)
        return pd.DataFrame(rows, columns=col_names)

    def get_lab_results(
        self,
        utc_start_datetime: datetime,
        utc_end_datetime: datetime,
        hospital_visit_id: int,
    ) -> pd.DataFrame:
        """Retrieve lab result data from caboodle."""
        validate_args_must_be_utc(utc_start_datetime, utc_end_datetime)

        lab_result_query = get_sql_query_with_schema(
            "lab_results.sql", settings.SCHEMA_NAME
        )
        parameters = {
            "start_datetime": utc_start_datetime,
            "end_datetime": utc_end_datetime,
            "hospital_visit_id": hospital_visit_id,
        }

        rows, col_names = self._get_rows(lab_result_query, parameters)
        return pd.DataFrame(rows, columns=col_names)

    def _get_rows(
        self, sql_query: sql.Composable, parameters: dict
    ) -> tuple[list, list[str]]:
        try:
            with self.connection_pool.getconn() as db_connection:
                with db_connection.cursor() as curs:
                    curs.execute(sql_query, parameters)
                    rows = curs.fetchall()
                    col_names = [col.name for col in curs.description]
                self.connection_pool.putconn(db_connection)
        except psycopg2.errors.OperationalError as e:
            self.connection_pool.putconn(db_connection)
            raise ConnectionError(f"Data base error: {e}")
        return rows, col_names
