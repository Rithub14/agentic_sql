from agentic_sql.agents.sql_agent import SQLAgent


def test_sql_agent_simple_query():
    schema = {
        "tables": {
            "users": {
                "id": "INTEGER",
                "name": "TEXT",
                "age": "INTEGER",
            }
        }
    }

    agent = SQLAgent()
    sql = agent.run(
        question="Get all users older than 30",
        schema=schema,
    )

    assert "SELECT" in sql.upper()
    assert "from users" in sql.lower()
    assert "age" in sql.lower()
