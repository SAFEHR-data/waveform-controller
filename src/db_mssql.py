from datetime import datetime
from typing import Any

import mssql_python
import pandas as pd

import settings as settings  # type:ignore
from db_utils import (
    get_sql_query_text,
    utc_to_naive_local,
    naive_local_to_utc,
    validate_args_must_be_utc,
)


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


def tz_adjust(value: Any) -> Any:
    """Only relevant to data returned from MS SQL Server, convert naive local times to
    UTC."""
    if isinstance(value, datetime):
        return naive_local_to_utc(value)
    else:
        # non-datetimes are returned unchanged
        return value


class caboodleDB:
    """For querying the caboodle database to extract electronic healthcare records per
    patient.

    Caboodle stores its timestamps as timezone-naive SQL types
    (`datetime` in SQL Server) that are in the local time of the hospital.

    Note: hospital time is not necessarily system time!

    The behaviour of the DB driver is also relevant here:
    https://learn.microsoft.com/en-us/sql/connect/python/mssql-python/datetime-handling?view=sql-server-ver17

    The waveform pipeline uses UTC wherever possible, so appropriate conversions to local time and back
    again are the responsibility of these methods.
    """

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
        self, utc_start_datetime: datetime, utc_end_datetime: datetime, csn: str
    ) -> pd.DataFrame:
        """Retrieve airflow data from database."""
        validate_args_must_be_utc(utc_start_datetime, utc_end_datetime)

        local_start_datetime = utc_to_naive_local(utc_start_datetime)
        local_end_datetime = utc_to_naive_local(utc_end_datetime)

        airway_query = get_sql_query_text("private/airway.sql")
        parameters = {
            "start_datetime": local_start_datetime,
            "end_datetime": local_end_datetime,
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

        rows, columns = self._get_rows(airway_query, parameters)
        rows_adjusted = [tuple(tz_adjust(v) for v in r) for r in rows]
        return pd.DataFrame(rows_adjusted, columns=columns)

    def _get_rows(self, sql_query: str, parameters: dict) -> tuple[list, list[str]]:
        try:
            with self.db_connection.cursor() as curs:
                curs.execute(sql_query, parameters)
                rows = curs.fetchall()
                col_names = [col[0] for col in curs.description]
        except mssql_python.OperationalError as e:
            raise ConnectionError(f"Database error: {e}") from e

        return rows, col_names
