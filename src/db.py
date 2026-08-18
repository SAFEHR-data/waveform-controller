from datetime import datetime
import pandas as pd
import psycopg2
from psycopg2 import sql, pool
import logging

import settings as settings  # type:ignore

logging.basicConfig(format="%(levelname)s:%(asctime)s: %(message)s")
logger = logging.getLogger(__name__)


class starDB:
    sql_query: str = ""
    connection_string: str = "dbname={} user={} password={} host={} port={} connect_timeout={} options='-c statement_timeout={}'".format(
        settings.UDS_DBNAME,  # type:ignore
        settings.UDS_USERNAME,  # type:ignore
        settings.UDS_PASSWORD,  # type:ignore
        settings.UDS_HOST,  # type:ignore
        settings.UDS_PORT,  # type:ignore
        settings.UDS_CONNECT_TIMEOUT,  # type:ignore
        settings.UDS_QUERY_TIMEOUT,  # type:ignore
    )
    connection_pool: pool.ThreadedConnectionPool

    def connect(self):
        self.connection_pool = pool.SimpleConnectionPool(1, 1, self.connection_string)

    def init_query(self):
        with open("src/sql/mrn_based_on_bed_and_datetime.sql", "r") as file:
            self.sql_query = sql.SQL(file.read())
        self.sql_query = self.sql_query.format(
            schema_name=sql.Identifier(settings.SCHEMA_NAME)
        )

    def get_row(self, location_string: str, observation_datetime: datetime):
        parameters = {
            "location_string": location_string,
            "observation_datetime": observation_datetime,
        }
        try:
            with self.connection_pool.getconn() as db_connection:
                with db_connection.cursor() as curs:
                    curs.execute(self.sql_query, parameters)
                    rows = curs.fetchall()
                self.connection_pool.putconn(db_connection)
        except psycopg2.errors.OperationalError as e:
            self.connection_pool.putconn(db_connection)
            raise ConnectionError(f"Data base error: {e}")

        if len(rows) != 1:
            raise ValueError(
                f"Wrong number of rows returned from database. {len(rows)} != 1, for {location_string}:{observation_datetime}"
            )

        return rows[0]


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
    connection_pool: pool.ThreadedConnectionPool
    fake_caboodle: bool

    def connect(self):
        """Set up connection to the database."""
        self.fake_caboodle = True if settings.CABOODLE_TESTING == "TRUE" else False
        if not self.fake_caboodle:
            self.connection_pool = pool.SimpleConnectionPool(
                1, 1, self.connection_string
            )

    def get_airflow(self, start_datetime: datetime, end_datetime: datetime, csn: str):
        """Retrieve airflow data from database."""
        if self.fake_caboodle:
            fake_airway = {
                "DateTimeRecorded": [0],
                "PlacementInstant": [0],
                "RemovalInstant": [0],
                "TubeSize": [0],
            }
            return pd.DataFrame(data=fake_airway)
        with open("src/sql/airway.sql", "r") as file:
            airway_query = sql.SQL(file.read())
        parameters = {
            "start_datetime": start_datetime,
            "end_datetime": end_datetime,
            "csn": csn,
        }
        return self._get_rows(airway_query, parameters)

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
