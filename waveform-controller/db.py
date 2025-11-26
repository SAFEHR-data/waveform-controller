import psycopg2
from psycopg2 import sql
import settings

class starDB:

    db_connection: psycopg2.connect = None
    sql_query : psycopg2.sql.SQL = None

    def connect (self):
        connection_string = "dbname={} user={} password={} host={} port={}".format(
            settings.UDS_DBNAME,
            settings.UDS_USERNAME,
            settings.UDS_PASSWORD,
            settings.UDS_HOST,
            settings.UDS_PORT
            )
        self.db_connection = psycopg2.connect(connection_string)

    def init_query (self):
        with open("../sql/mrn_based_on_bed_and_datetime.sql", "r" ) as file:
            self.sql_query = sql.SQL(file.read())
        self.sql_query = self.sql_query.format(schema_name = sql.Identifier(settings.SCHEMA_NAME))

    def get_row(location_string : str, start_datetime : str, end_datetime : str):
        parameters = { "location_string" : location_string, 
                      "start_datetime" : start_datetime, 
                      "end_datetime" : end_datetime } 
        
        with conn.cursor() as curs:
            curs.execute(self.sql_query, parameters)
            single_row = curs.fetchone()
        
        return single_row



# the username and password come from docker compose for the fake uds. 
# I'm not sure why the port is 5433 not 5432



