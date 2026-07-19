"""
dbcompat.py — tiny storage backend shim so the app can run on either SQLite
(local/dev/tests) or MySQL (AWS RDS) with no changes to call sites.

The rest of the codebase opens a connection via a factory (api.db / geocoding._db /
payments via the passed factory) and uses it exactly like a sqlite3 Connection:

    with db() as c:
        row = c.execute("SELECT ... WHERE id=?", (rid,)).fetchone()

This module preserves that interface for MySQL too:
  * connect() returns a sqlite3.Connection when running on SQLite (unchanged
    behaviour — tests and local dev are byte-for-byte identical), OR a thin
    MySQLConn wrapper that mimics sqlite3.Connection's context-manager + .execute.
  * On MySQL, SQL is translated on the fly: ? -> %s, INSERT OR REPLACE -> REPLACE,
    INSERT OR IGNORE -> INSERT IGNORE, json_extract(...) -> JSON_UNQUOTE(JSON_EXTRACT(...)),
    and SQLite DDL types (TEXT/INTEGER/REAL) -> MySQL types in CREATE TABLE.

Backend selection: MySQL is used when DB_HOST is set (as it is on Elastic
Beanstalk). Otherwise SQLite via DB_PATH. Force with DB_BACKEND=sqlite|mysql.
"""
import os
import re
import sqlite3


def _backend() -> str:
    forced = os.getenv("DB_BACKEND", "").strip().lower()
    if forced in ("sqlite", "mysql"):
        return forced
    return "mysql" if os.getenv("DB_HOST") else "sqlite"


def using_mysql() -> bool:
    return _backend() == "mysql"


# --------------------------------------------------------------------------- #
# SQL translation (SQLite dialect -> MySQL). Only applied on the MySQL backend.
# --------------------------------------------------------------------------- #
_JSON_EXTRACT_RE = re.compile(r"json_extract\s*\(([^)]*)\)", re.IGNORECASE)


def _translate_ddl_types(sql: str) -> str:
    # Order matters: handle "TEXT PRIMARY KEY" before the generic TEXT rule.
    sql = re.sub(r"\bTEXT\s+PRIMARY\s+KEY\b", "VARCHAR(255) PRIMARY KEY", sql, flags=re.IGNORECASE)
    sql = re.sub(r"\bTEXT\b", "LONGTEXT", sql, flags=re.IGNORECASE)
    sql = re.sub(r"\bINTEGER\b", "BIGINT", sql, flags=re.IGNORECASE)
    sql = re.sub(r"\bREAL\b", "DOUBLE", sql, flags=re.IGNORECASE)
    return sql


def translate(sql: str) -> str:
    s = sql
    # SQLite upsert / ignore -> MySQL equivalents.
    s = re.sub(r"INSERT\s+OR\s+REPLACE\s+INTO", "REPLACE INTO", s, flags=re.IGNORECASE)
    s = re.sub(r"INSERT\s+OR\s+IGNORE\s+INTO", "INSERT IGNORE INTO", s, flags=re.IGNORECASE)
    # json_extract(x,'$.p') -> JSON_UNQUOTE(JSON_EXTRACT(x,'$.p')) (scalar text).
    s = _JSON_EXTRACT_RE.sub(r"JSON_UNQUOTE(JSON_EXTRACT(\1))", s)
    # DDL type mapping only inside CREATE TABLE statements.
    if re.match(r"\s*CREATE\s+TABLE", s, flags=re.IGNORECASE):
        s = _translate_ddl_types(s)
    # Positional placeholders. No literal '?' or '%' appears in these queries,
    # so a direct swap is safe; PyMySQL uses %s.
    s = s.replace("?", "%s")
    return s


# --------------------------------------------------------------------------- #
# MySQL connection wrapper that quacks like sqlite3.Connection.
# --------------------------------------------------------------------------- #
class MySQLConn:
    def __init__(self, conn):
        self._conn = conn

    def execute(self, sql, params=()):
        cur = self._conn.cursor()  # PyMySQL default cursor is buffered
        q = translate(sql)
        if params:
            cur.execute(q, params)
        else:
            cur.execute(q)
        return cur  # exposes fetchone()/fetchall()

    def cursor(self):
        return self._conn.cursor()

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()

    def close(self):
        self._conn.close()

    # Mirror sqlite3.Connection's context-manager semantics: commit on success,
    # rollback on exception. We also close (MySQL connections are not GC-cheap).
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        try:
            if exc_type is None:
                self._conn.commit()
            else:
                self._conn.rollback()
        finally:
            self._conn.close()
        return False


def _mysql_connect() -> MySQLConn:
    import pymysql
    conn = pymysql.connect(
        host=os.environ["DB_HOST"],
        port=int(os.getenv("DB_PORT", "3306")),
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
        database=os.environ["DB_NAME"],
        charset="utf8mb4",
        autocommit=False,
        connect_timeout=10,
    )
    return MySQLConn(conn)


def _sqlite_connect():
    base = os.path.dirname(os.path.abspath(__file__))
    db_path = os.getenv("DB_PATH", os.path.join(base, "data", "reports.db"))
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    return sqlite3.connect(db_path)


def connect():
    """Open a fresh connection for the active backend."""
    return _mysql_connect() if using_mysql() else _sqlite_connect()
