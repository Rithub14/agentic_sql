from sqlalchemy import text

from agentic_sql.agents.coordinator import CoordinatorAgent


TEST_DB_URL = "sqlite:///./test.db"


def test_coordinator_end_to_end():
    # Prepare test DB
    from agentic_sql.db.engine import get_engine

    engine = get_engine(TEST_DB_URL)

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

    coordinator = CoordinatorAgent(database_url=TEST_DB_URL)

    output = coordinator.run(
        question="Show total sales per country"
    )

    assert "results" in output
    assert isinstance(output["results"], list)
    assert len(output["results"]) > 0
    assert "sql" in output
