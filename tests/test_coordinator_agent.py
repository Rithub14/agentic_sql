from sqlalchemy import text

from agentic_sql.agents.coordinator import CoordinatorAgent
from agentic_sql.db.engine import get_engine


def test_coordinator_end_to_end():
    engine = get_engine()

    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS sales (
                    country TEXT,
                    amount INTEGER
                )
                """
            )
        )
        conn.execute(
            text(
                """
                INSERT INTO sales (country, amount)
                VALUES ('DE', 100), ('FR', 80)
                """
            )
        )

    coordinator = CoordinatorAgent()

    output = coordinator.run(
        question="Show total sales per country",
    )

    assert "results" in output
    assert isinstance(output["results"], list)
    assert "sql" in output
