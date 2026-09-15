from datetime import datetime

import mssql_python
import pandas as pd

import settings as settings  # type:ignore
from db_utils import get_sql_query_text


def _odbc_escape(value: object) -> str:
    """Quote a value for use in an ODBC connection string."""
    return "{" + str(value).replace("}", "}}") + "}"


def _get_connection_string() -> str:
    return "Server={server};Database={database};UID={username};PWD={password};".format(
        server=_odbc_escape(
            f"{settings.CABOODLE_HOST},{settings.CABOODLE_PORT}"  # type:ignore
        ),
        database=_odbc_escape(settings.CABOODLE_DBNAME),  # type:ignore
        username=_odbc_escape(settings.CABOODLE_USERNAME),  # type:ignore
        password=_odbc_escape(settings.CABOODLE_PASSWORD),  # type:ignore
    )


class caboodleDB:
    """For querying the caboodle database to extract electronic healthcare records per
    patient."""

    connection_string: str
    db_connection: mssql_python.Connection
    fake_caboodle: bool = False

    def connect(self) -> None:
        """Set up connection to the database."""
        self.fake_caboodle = settings.CABOODLE_TESTING == "TRUE"
        if not self.fake_caboodle:
            self.connection_string = _get_connection_string()
            self.db_connection = mssql_python.connect(
                self.connection_string,
                timeout=int(settings.CABOODLE_QUERY_TIMEOUT),
                attrs_before={
                    mssql_python.SQL_ATTR_LOGIN_TIMEOUT: int(
                        settings.CABOODLE_CONNECT_TIMEOUT  # type:ignore
                    )
                },
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

    def _get_rows(self, sql_query: str, parameters: dict) -> pd.DataFrame:
        try:
            with self.db_connection.cursor() as curs:
                curs.execute(sql_query, parameters)
                rows = curs.fetchall()
                col_names = [col[0] for col in curs.description]
        except mssql_python.OperationalError as e:
            raise ConnectionError(f"Database error: {e}") from e

        return pd.DataFrame(rows, columns=col_names)
