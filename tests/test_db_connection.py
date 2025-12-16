from sqlalchemy import text

from agentic_sql.db.connection import get_connection


def test_db_connection():
    with get_connection() as conn:
        result = conn.execute(text("SELECT 1"))
        row = result.fetchone()

    assert row is not None
    assert row[0] == 1
