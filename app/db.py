import psycopg
from psycopg.rows import dict_row

from app.config import get_settings


def connect() -> psycopg.Connection:
    """Open a connection to the project's Postgres.

    autocommit=True: every statement saves immediately. That matters for the cost log,
    because a row written before a crash must not be lost.
    dict_row: rows come back as dicts, so you write row["status"], not row[3].
    """
    return psycopg.connect(get_settings().database_url, autocommit=True, row_factory=dict_row)
