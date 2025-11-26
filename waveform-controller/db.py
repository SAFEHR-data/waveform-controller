import psycopg2
import settings

class starDB:

    db_connection: psycopg2.connection = None

    def connect (self):
        connection_string = "dbname={} user={} password={} host={} port={}".format(
            settings.UDS_DBNAME,
            settings.UDS_USERNAME,
            settings.UDS_PASSWORD,
            settings.UDS_HOST,
            settings.UDS_PORT
            )
        self.db_connection = psycopg2.connect(connection_string)



# the username and password come from docker compose for the fake uds. 
# I'm not sure why the port is 5433 not 5432
connstring = "dbname={} user={} password={} host={} port={}".format(
'fakeuds', 'xxxxxxxxx', 'xxxxxxxx', 'xxxxxx', '5433')

dbconn = psycopg2.connect(connstring)

with conn.cursor() as curs:
    curs.execute("SELECT version()")
    single_row = curs.fetchone()
    print(f"{single_row}")

