import pytest

from agentic_sql.agents.validation_agent import ValidationAgent, SQLValidationError
from agentic_sql.execution.sql_executor import SQLExecutor


# ---------------------------------------------------------------------------
# ValidationAgent
# ---------------------------------------------------------------------------

class TestValidationAgent:
    def setup_method(self):
        self.agent = ValidationAgent(default_limit=10)

    def test_blocks_drop_table(self):
        with pytest.raises(SQLValidationError, match="drop"):
            self.agent.run("DROP TABLE users;")

    def test_blocks_delete(self):
        with pytest.raises(SQLValidationError, match="delete"):
            self.agent.run("DELETE FROM users WHERE id = 1;")

    def test_blocks_insert(self):
        with pytest.raises(SQLValidationError, match="insert"):
            self.agent.run("INSERT INTO users VALUES (1, 'x');")

    def test_does_not_false_positive_on_keyword_in_block_comment(self):
        """DROP inside a /* comment */ is harmless — must NOT be blocked."""
        sql = self.agent.run("SELECT 1 /* DROP TABLE users */")
        assert "SELECT 1" in sql

    def test_does_not_false_positive_on_keyword_in_line_comment(self):
        """DROP after -- is harmless — must NOT be blocked."""
        sql = self.agent.run("SELECT 1 -- DROP TABLE users\nFROM t")
        assert "SELECT" in sql

    def test_blocks_drop_hidden_with_inline_comment(self):
        """DROP /* comment */ TABLE is still actual DROP — must be blocked."""
        with pytest.raises(SQLValidationError):
            self.agent.run("DROP /* safe */ TABLE users;")

    def test_allows_keyword_in_string_literal(self):
        """A string value containing 'drop' should NOT be blocked."""
        sql = self.agent.run("SELECT 'drop me' AS label FROM t")
        assert "drop me" in sql

    def test_adds_limit_when_missing(self):
        sql = self.agent.run("SELECT * FROM users")
        assert "limit 10" in sql.lower()

    def test_does_not_double_add_limit(self):
        sql = self.agent.run("SELECT * FROM users LIMIT 5")
        assert sql.lower().count("limit") == 1

    def test_limit_column_name_not_confused(self):
        """A column named limit_date should not trigger LIMIT injection bypass."""
        sql = self.agent.run("SELECT limit_date FROM events")
        # 'limit_date' is not the LIMIT clause — LIMIT should still be added
        assert "limit 10" in sql.lower()


# ---------------------------------------------------------------------------
# SQLExecutor
# ---------------------------------------------------------------------------

class TestSQLExecutor:
    def test_returns_list_of_dicts(self, engine_with_users):
        executor = SQLExecutor(engine_with_users)
        results = executor.run("SELECT * FROM users LIMIT 5")
        assert isinstance(results, list)
        assert len(results) == 3
        assert "name" in results[0]
        assert "age" in results[0]

    def test_empty_result_set(self, engine_with_users):
        executor = SQLExecutor(engine_with_users)
        results = executor.run("SELECT * FROM users WHERE id = 9999 LIMIT 1")
        assert results == []

    def test_column_mapping_correct(self, engine_with_users):
        executor = SQLExecutor(engine_with_users)
        results = executor.run("SELECT name, age FROM users WHERE name = 'Alice' LIMIT 1")
        assert results[0] == {"name": "Alice", "age": 35}
