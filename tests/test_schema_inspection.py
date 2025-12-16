from sqlalchemy import text

from agentic_sql.db.engine import get_engine
from agentic_sql.db.schema import inspect_schema


def test_schema_inspection():
    engine = get_engine()

    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY,
                    name TEXT
                )
                """
            )
        )

    schema = inspect_schema(engine)

    assert "users" in schema
    assert "id" in schema["users"]
    assert "name" in schema["users"]
