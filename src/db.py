import psycopg2
from psycopg2 import sql, pool
import logging

import settings as settings  # type:ignore

logging.basicConfig(format="%(levelname)s:%(asctime)s: %(message)s")
logger = logging.getLogger(__name__)


class starDB:
    sql_query: str = ""
    connection_string: str = "dbname={} user={} password={} host={} port={}".format(
        settings.UDS_DBNAME,  # type:ignore
        settings.UDS_USERNAME,  # type:ignore
        settings.UDS_PASSWORD,  # type:ignore
        settings.UDS_HOST,  # type:ignore
        settings.UDS_PORT,  # type:ignore
    )
    connection_pool: pool.ThreadedConnectionPool

    def connect(self):
        self.connection_pool = pool.ThreadedConnectionPool(1, 1, self.connection_string)

    def init_query(self):
        with open("src/sql/mrn_based_on_bed_and_datetime.sql", "r") as file:
            self.sql_query = sql.SQL(file.read())
        self.sql_query = self.sql_query.format(
            schema_name=sql.Identifier(settings.SCHEMA_NAME)
        )

    def get_row(self, location_string: str, start_datetime: str, end_datetime: str):
        parameters = {
            "location_string": location_string,
            "start_datetime": start_datetime,
            "end_datetime": end_datetime,
        }
        try:
            with self.connection_pool.getconn() as db_connection:
                with db_connection.cursor() as curs:
                    curs.execute(self.sql_query, parameters)
                    single_row = curs.fetchone()
        except psycopg2.errors.UndefinedTable as e:
            self.connection_pool.putconn(db_connection)
            logger.error(f"Failed to find required tables in database: {e}")
            raise ConnectionError("Missing tables in database.")

        return single_row
