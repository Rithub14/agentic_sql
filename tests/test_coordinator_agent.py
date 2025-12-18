from sqlalchemy import text

from langchain_core.runnables import RunnableLambda

from agentic_sql.agents.coordinator import CoordinatorAgent
from agentic_sql.agents.sql_agent import SQLAgent


TEST_DB_URL = "sqlite:///./test.db"


def test_coordinator_end_to_end():
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

    sql_agent_stub = SQLAgent(llm=RunnableLambda(lambda _: 'SELECT country, SUM(amount) AS total_sales FROM sales GROUP BY country;'))
    coordinator = CoordinatorAgent(database_url=TEST_DB_URL, sql_agent=sql_agent_stub)

    output = coordinator.run(
        question="Show total sales per country"
    )

    assert "results" in output
    assert isinstance(output["results"], list)
    assert len(output["results"]) > 0
    assert "sql" in output
