from datetime import datetime
import pandas as pd
import psycopg2
from psycopg2 import sql, pool
import logging

import settings as settings  # type:ignore

logging.basicConfig(format="%(levelname)s:%(asctime)s: %(message)s")
logger = logging.getLogger(__name__)


class starDB:
    mrn_lookup_query: str = ""
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
    fake_star: bool = False

    def connect(self) -> None:
        self.fake_star = True if settings.STARDB_TESTING == "TRUE" else False
        if not self.fake_star:
            self.connection_pool = pool.SimpleConnectionPool(
                1, 1, self.connection_string
            )

    def _init_mrn_lookup_query(self) -> None:
        with open(settings.SQL_PATH + "mrn_based_on_bed_and_datetime.sql", "r") as file:
            self.mrn_lookup_query = sql.SQL(file.read())  # type:ignore

        self.mrn_lookup_query = self.mrn_lookup_query.format(
            schema_name=sql.Identifier(settings.SCHEMA_NAME)
        )

    def get_matched_mrn(
        self, location_string: str, observation_datetime: datetime
    ) -> pd.DataFrame:
        parameters = {
            "location_string": location_string,
            "observation_datetime": observation_datetime,
        }
        if self.mrn_lookup_query == "":
            self._init_mrn_lookup_query()

        rows = self._get_rows(self.mrn_lookup_query, parameters)  # type: ignore

        if len(rows) != 1:
            raise ValueError(
                f"Wrong number of rows returned from database. {len(rows)} != 1, for {location_string}:{observation_datetime}"
            )

        return rows[0]

    def get_hospital_visit_from_csn(self, csn: str) -> int:
        with open(settings.SQL_PATH + "get_hospital_visit_id.sql", "r") as file:
            hv_query = sql.SQL(file.read())

        hv_query = hv_query.format(schema_name=sql.Identifier(settings.SCHEMA_NAME))  # type: ignore

        parameters = {
            "csn": csn,
        }
        if self.fake_star:
            return 12345678

        hospital_visit_id = self._get_rows(hv_query, parameters)

        # fetchall returns a list of tuples. We want the first element of the first tuple
        if not isinstance(hospital_visit_id[0][0], int):
            logger.warning(
                f"hospital_visit_id[0][0] is not integer {hospital_visit_id}"
            )

        return hospital_visit_id[0][0]

    def _get_rows(self, sql_query: sql.SQL, parameters: dict):
        try:
            with self.connection_pool.getconn() as db_connection:
                with db_connection.cursor() as curs:
                    curs.execute(sql_query, parameters)
                    rows = curs.fetchall()
                self.connection_pool.putconn(db_connection)
        except psycopg2.errors.OperationalError as e:
            self.connection_pool.putconn(db_connection)
            raise ConnectionError(f"Data base error: {e}")
        return rows


class caboodleDB:
    """For querying the caboodle database to extract electronic healthcare records per
    patient."""

    connection_string: str = "dbname={} user={} password={} host={} port={} connect_timeout={} options='-c statement_timeout={}'".format(
        settings.CABOODLE_DBNAME,  # type:ignore
        settings.CABOODLE_USERNAME,  # type:ignore
        settings.CABOODLE_PASSWORD,  # type:ignore
        settings.CABOODLE_HOST,  # type:ignore
        settings.CABOODLE_PORT,  # type:ignore
        settings.CABOODLE_CONNECT_TIMEOUT,  # type:ignore
        settings.CABOODLE_QUERY_TIMEOUT,  # type:ignore
    )
    connection_pool: pool.SimpleConnectionPool
    fake_caboodle: bool = False

    def connect(self) -> None:
        """Set up connection to the database."""
        self.fake_caboodle = True if settings.CABOODLE_TESTING == "TRUE" else False
        if not self.fake_caboodle:
            self.connection_pool = pool.SimpleConnectionPool(
                1, 1, self.connection_string
            )

    def get_airflow(
        self, start_datetime: datetime, end_datetime: datetime, csn: str
    ) -> pd.DataFrame:
        """Retrieve airflow data from database."""

        with open(settings.SQL_PATH + "airway.sql", "r") as file:
            airway_query = sql.SQL(file.read())
        parameters = {
            "start_datetime": start_datetime,
            "end_datetime": end_datetime,
            "csn": csn,
        }

        if self.fake_caboodle:
            fake_airway = {
                "DateTimeRecorded": [0],
                "PlacementInstant": [0],
                "RemovalInstant": [0],
                "TubeSize": [0],
            }
            return pd.DataFrame(data=fake_airway)

        return self._get_rows(airway_query, parameters)

    def get_flowsheets(
        self, start_datetime: datetime, end_datetime: datetime, hospital_visit_id: int
    ) -> pd.DataFrame:
        """Retrieve airflow data from database."""

        with open(settings.SQL_PATH + "flow_sheet_values.sql", "r") as file:
            flowsheet_query = sql.SQL(file.read())
        parameters = {
            "start_datetime": start_datetime,
            "end_datetime": end_datetime,
            "hospital_visit_id": hospital_visit_id,
        }

        if self.fake_caboodle:
            fake_flowsheet = {
                "DateTimeRecorded": [0],
                "Temperature": [0],
                "Noradrenaline": [0],
                "Metaraminol": [0],
            }
            return pd.DataFrame(data=fake_flowsheet)

        return self._get_rows(flowsheet_query, parameters)

    def _get_rows(self, sql_query: sql.SQL, parameters: dict):
        try:
            with self.connection_pool.getconn() as db_connection:
                with db_connection.cursor() as curs:
                    curs.execute(sql_query, parameters)
                    rows = curs.fetchall()
                self.connection_pool.putconn(db_connection)
        except psycopg2.errors.OperationalError as e:
            self.connection_pool.putconn(db_connection)
            raise ConnectionError(f"Data base error: {e}")

        return rows
