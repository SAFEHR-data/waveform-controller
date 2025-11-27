import psycopg2
from psycopg2 import sql
import json
from datetime import datetime, timedelta

import waveform_controller.settings as settings


class starDB:
    sql_query: str = ""
    connection_string: str = "dbname={} user={} password={} host={} port={}".format(
        settings.UDS_DBNAME,
        settings.UDS_USERNAME,
        settings.UDS_PASSWORD,
        settings.UDS_HOST,
        settings.UDS_PORT,
    )

    def init_query(self):
        with open(
            "waveform_controller/sql/mrn_based_on_bed_and_datetime.sql", "r"
        ) as file:
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
        with psycopg2.connect(self.connection_string) as db_connection:
            with db_connection.cursor() as curs:
                curs.execute(self.sql_query, parameters)
                single_row = curs.fetchone()

        return single_row

    def waveform_callback(self, ch, method, properties, body):
        data = json.loads(body)
        location_string = data.get("mappedLocationString", "unknown")
        observation_time = data.get("observationTime", "NaT")
        observation_time = datetime.fromtimestamp(observation_time)
        # I found in testing that to find the first patient I had to go back 7 months. I'm not sure this
        # is expected, but I suppose an ICU patient could occupy a bed for a long time. Let's use
        # 52 weeks for now.
        start_time = observation_time - timedelta(weeks=52)
        obs_time_str = observation_time.strftime("%Y-%m-%d:%H:%M:%S")
        start_time_str = start_time.strftime("%Y-%m-%d:%H:%M:%S")
        matched_mrn = self.get_row(location_string, start_time_str, obs_time_str)
        # print(f"Received a waveform message {data.get('observationTime', 'NAT')}")
        print(
            f"Received a waveform message from {location_string} at {obs_time_str} with matching mrn = {matched_mrn}"
        )
