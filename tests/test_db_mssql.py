from unittest.mock import MagicMock

import pytest

import db_mssql


def test_connect_uses_mssql_connection_string_and_timeouts(monkeypatch):
    monkeypatch.setattr(db_mssql.settings, "CABOODLE_TESTING", "FALSE")
    monkeypatch.setattr(db_mssql.settings, "CABOODLE_HOST", "sql.example.com")
    monkeypatch.setattr(db_mssql.settings, "CABOODLE_PORT", "1433")
    monkeypatch.setattr(db_mssql.settings, "CABOODLE_DBNAME", "Caboodle")
    monkeypatch.setattr(db_mssql.settings, "CABOODLE_USERNAME", "reader")
    monkeypatch.setattr(db_mssql.settings, "CABOODLE_PASSWORD", "p;ass}")
    monkeypatch.setattr(db_mssql.settings, "CABOODLE_CONNECT_TIMEOUT", "10")
    monkeypatch.setattr(db_mssql.settings, "CABOODLE_QUERY_TIMEOUT", "3001")
    connection = MagicMock()
    connect = MagicMock(return_value=connection)
    monkeypatch.setattr(db_mssql.mssql_python, "connect", connect)

    database = db_mssql.caboodleDB()
    database.connect()

    connect.assert_called_once_with(
        (
            "Server={sql.example.com,1433};Database={Caboodle};"
            "UID={reader};PWD={p;ass}}};"
        ),
        timeout=4,
        attrs_before={db_mssql.mssql_python.SQL_ATTR_LOGIN_TIMEOUT: 10},
    )
    assert database.db_connection is connection


def test_get_rows_executes_named_parameters():
    cursor = MagicMock()
    cursor.fetchall.return_value = [("row",)]
    connection = MagicMock()
    connection.cursor.return_value.__enter__.return_value = cursor
    database = db_mssql.caboodleDB()
    database.db_connection = connection
    parameters = {"csn": "123"}

    rows = database._get_rows("SELECT * FROM Encounter WHERE CSN = %(csn)s", parameters)

    cursor.execute.assert_called_once_with(
        "SELECT * FROM Encounter WHERE CSN = %(csn)s", parameters
    )
    assert rows == [("row",)]


def test_get_rows_translates_operational_errors():
    cursor = MagicMock()
    cursor.execute.side_effect = db_mssql.mssql_python.OperationalError(
        "timed out", "timed out"
    )
    connection = MagicMock()
    connection.cursor.return_value.__enter__.return_value = cursor
    database = db_mssql.caboodleDB()
    database.db_connection = connection

    with pytest.raises(ConnectionError, match="Database error"):
        database._get_rows("SELECT 1", {})
