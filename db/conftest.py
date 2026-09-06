"""
Shared pytest fixtures for the db/ tests.

The `conn` fixture builds a throwaway MySQL schema, loads db/schema_v2.sql into it,
hands the test a (non-autocommit) connection pointed at it, then drops it. Every
db/ test that takes a `conn` argument gets this automatically.

RUN (from repo root, with pymysql + pytest installed):
    DB_PASSWORD='<your local mysql password>' python3 -m pytest db/ -v
"""
import os
import re
import sys
from pathlib import Path

import pymysql
import pytest

sys.path.insert(0, str(Path(__file__).parent))
import db_v2  # noqa: E402

TEST_DB = os.getenv("DBV2_TEST_NAME", "axtroshastra_v2_test")
SCHEMA_FILE = Path(__file__).with_name("schema_v2.sql")


def _server_conn(database=None, autocommit=True):
    return pymysql.connect(
        host=os.getenv("DB_HOST", "127.0.0.1"),
        port=int(os.getenv("DB_PORT", "3306")),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", ""),
        database=database, charset="utf8mb4", autocommit=autocommit,
    )


def _statements(ddl: str):
    # Strip `-- ...` comments FIRST — some contain ';' (e.g. "we identify them;
    # holds first-touch attribution"), which would otherwise split a comment
    # mid-sentence and feed the tail to MySQL as bogus SQL. The DDL has no `--`
    # inside string literals and no stored procedures, so this is safe.
    no_comments = re.sub(r"--[^\n]*", "", ddl)
    for chunk in no_comments.split(";"):
        if chunk.strip():
            yield chunk


@pytest.fixture()
def conn():
    admin = _server_conn()
    with admin.cursor() as c:
        c.execute(f"DROP DATABASE IF EXISTS {TEST_DB}")
        c.execute(f"CREATE DATABASE {TEST_DB} CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci")
    admin.close()

    loader = _server_conn(database=TEST_DB)
    with loader.cursor() as c:
        for stmt in _statements(SCHEMA_FILE.read_text()):
            c.execute(stmt)
    loader.close()

    c = db_v2.get_conn(db_name=TEST_DB)
    yield c
    try:
        c.close()
    finally:
        admin = _server_conn()
        with admin.cursor() as cur:
            cur.execute(f"DROP DATABASE IF EXISTS {TEST_DB}")
        admin.close()
