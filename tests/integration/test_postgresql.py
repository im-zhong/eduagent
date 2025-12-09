from __future__ import annotations

from uuid import uuid4

import psycopg
import pytest
from psycopg import sql

from eduagent.settings import settings

pytestmark = pytest.mark.integration


def test_postgresql_roundtrip() -> None:
    config = settings.database
    table_name = f"test_table_{uuid4().hex}"
    value = f"value-{uuid4().hex}"
    with psycopg.connect(
        host=config.host,
        port=config.port,
        user=config.user,
        password=config.password,
        dbname=config.name,
    ) as conn:
        conn.autocommit = True
        with conn.cursor() as cur:
            table_identifier = sql.Identifier(table_name)
            cur.execute(
                sql.SQL(
                    "CREATE TABLE IF NOT EXISTS {} (id SERIAL PRIMARY KEY, value TEXT NOT NULL)"
                ).format(table_identifier)
            )
            cur.execute(
                sql.SQL("INSERT INTO {} (value) VALUES (%s)").format(table_identifier),
                (value,),
            )
            cur.execute(
                sql.SQL("SELECT value FROM {} ORDER BY id DESC LIMIT 1").format(
                    table_identifier
                )
            )
            row = cur.fetchone()
            assert row is not None
            assert row[0] == value
            cur.execute(sql.SQL("DROP TABLE {}").format(table_identifier))
