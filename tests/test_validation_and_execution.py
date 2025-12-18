from sqlalchemy import text

from agentic_sql.db.engine import get_engine
from agentic_sql.agents.validation_agent import ValidationAgent, SQLValidationError
from agentic_sql.execution.sql_executor import SQLExecutor


TEST_DB_URL = "sqlite:///./test.db"


def test_validation_blocks_destructive_sql():
    agent = ValidationAgent()

    try:
        agent.run("DROP TABLE users;")
        assert False, "Expected SQLValidationError"
    except SQLValidationError:
        assert True


def test_validation_adds_limit():
    agent = ValidationAgent(default_limit=10)
    sql = agent.run("SELECT * FROM users")
    assert "limit 10" in sql.lower()


def test_sql_execution():
    engine = get_engine(TEST_DB_URL)

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
        conn.execute(
            text(
                "INSERT INTO users (name) VALUES ('Alice'), ('Bob')"
            )
        )

    validator = ValidationAgent(default_limit=5)
    executor = SQLExecutor(engine)

    sql = validator.run("SELECT * FROM users")
    result = executor.run(sql)

    assert isinstance(result, list)
    assert len(result) >= 2
    assert "name" in result[0]
