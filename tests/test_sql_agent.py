from langchain_core.runnables import RunnableLambda

from agentic_sql.agents.sql_agent import SQLAgent


SCHEMA = {
    "tables": {
        "users": {
            "id": "INTEGER PK",
            "name": "TEXT",
            "age": "INTEGER",
        }
    }
}


class TestSQLAgent:
    def _make_agent(self, stub_output: str) -> SQLAgent:
        return SQLAgent(llm=RunnableLambda(lambda _: stub_output))

    def test_returns_plain_sql(self):
        agent = self._make_agent("SELECT * FROM users WHERE age > 30;")
        sql = agent.run(question="Users older than 30", schema=SCHEMA)
        assert "SELECT" in sql.upper()
        assert "users" in sql.lower()

    def test_strips_markdown_code_fences(self):
        agent = self._make_agent("```sql\nSELECT * FROM users;\n```")
        sql = agent.run(question="All users", schema=SCHEMA)
        assert "```" not in sql
        assert "SELECT" in sql.upper()

    def test_strips_plain_code_fences(self):
        agent = self._make_agent("```\nSELECT id FROM users;\n```")
        sql = agent.run(question="User IDs", schema=SCHEMA)
        assert "```" not in sql
        assert "SELECT" in sql.upper()

    def test_output_is_stripped(self):
        agent = self._make_agent("  SELECT * FROM users;  ")
        sql = agent.run(question="All users", schema=SCHEMA)
        assert sql == sql.strip()
