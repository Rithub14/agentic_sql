from sqlalchemy import text

from agentic_sql.db.connection import get_connection


class TestDBConnection:
    def test_select_one(self, engine):
        with get_connection(str(engine.url)) as conn:
            result = conn.execute(text("SELECT 1"))
            row = result.fetchone()

        assert row is not None
        assert row[0] == 1
