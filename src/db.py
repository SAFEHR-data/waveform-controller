import psycopg2
from psycopg2 import sql, pool
import json
from datetime import datetime, timedelta
import functools
import logging

import settings as settings  # type:ignore
import csv_writer as writer  # type:ignore

logging.basicConfig(format="%(levelname)s:%(asctime)s: %(message)s")
logger = logging.getLogger(__name__)


def ack_message(ch, delivery_tag):
    """Note that `ch` must be the same pika channel instance via which the
    message being ACKed was retrieved (AMQP protocol constraint)."""
    if ch.is_open:
        ch.basic_ack(delivery_tag)
    else:
        logger.warning("Attempting to acknowledge a message on a closed channel.")


def nack_message(ch, delivery_tag):
    if ch.is_open:
        ch.basic_nack(delivery_tag)
    else:
        logger.warning("Attempting to not acknowledge a message on a closed channel.")


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

    def create_connection_pool(self):
        self.connection_pool = pool.ThreadedConnectionPool(2, 5, self.connection_string)

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
            db_connection = self.connection_pool.getconn()
            with db_connection.cursor() as curs:
                logger.error("I get data")
                curs.execute(self.sql_query, parameters)
                logger.error("I got data")
                single_row = curs.fetchone()
            self.connection_pool.putconn(db_connection)
        except psycopg2.errors.UndefinedTable:
            return ("null", "null", "null")
            logger.error("Failed to find required tables in database.")
            self.connection_pool.putconn(db_connection)
            raise ConnectionError("There is no table in your data base")

        return single_row
