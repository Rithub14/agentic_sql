from sqlalchemy import text

from agentic_sql.db.engine import get_engine
from agentic_sql.agents.schema_agent import SchemaAgent


def test_schema_agent():
    engine = get_engine()

    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS products (
                    id INTEGER PRIMARY KEY,
                    name TEXT,
                    price INTEGER
                )
                """
            )
        )

    agent = SchemaAgent(engine)
    schema = agent.run()

    assert "tables" in schema
    assert "products" in schema["tables"]
    assert "id" in schema["tables"]["products"]
    assert "name" in schema["tables"]["products"]
    assert "price" in schema["tables"]["products"]
