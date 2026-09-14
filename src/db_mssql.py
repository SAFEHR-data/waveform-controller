from datetime import datetime
from typing import Optional

import pandas as pd
import psycopg2
from psycopg2 import sql, pool
import logging
from importlib import resources


import settings as settings  # type:ignore
from db_utils import get_sql_query_text

logging.basicConfig(format="%(levelname)s:%(asctime)s: %(message)s")
logger = logging.getLogger(__name__)


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

        airway_query = get_sql_query_text("private/airway.sql")
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

    def _get_rows(self, sql_query: sql.Composable, parameters: dict):
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
