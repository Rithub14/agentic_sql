from langchain_core.runnables import RunnableLambda

from agentic_sql.agents.coordinator import CoordinatorAgent
from agentic_sql.agents.sql_agent import SQLAgent


class TestCoordinatorAgent:
    def _make_coordinator(self, engine_with_sales, stub_sql: str) -> CoordinatorAgent:
        sql_stub = SQLAgent(
            llm=RunnableLambda(lambda _: stub_sql)
        )
        # Pass the engine directly so the coordinator reuses the same
        # in-memory SQLite connection (new engine = new empty DB)
        return CoordinatorAgent(
            engine=engine_with_sales,
            sql_agent=sql_stub,
        )

    def test_end_to_end_returns_expected_keys(self, engine_with_sales):
        coordinator = self._make_coordinator(
            engine_with_sales,
            "SELECT country, SUM(amount) AS total_sales FROM sales GROUP BY country",
        )
        output = coordinator.run(question="Show total sales per country")

        assert "results" in output
        assert "sql" in output
        assert "visualization" in output

    def test_results_are_non_empty(self, engine_with_sales):
        coordinator = self._make_coordinator(
            engine_with_sales,
            "SELECT country, SUM(amount) AS total_sales FROM sales GROUP BY country",
        )
        output = coordinator.run(question="Show total sales per country")
        assert len(output["results"]) > 0

    def test_visualization_suggests_chart(self, engine_with_sales):
        coordinator = self._make_coordinator(
            engine_with_sales,
            "SELECT country, SUM(amount) AS total_sales FROM sales GROUP BY country",
        )
        output = coordinator.run(question="Show total sales per country")
        viz = output["visualization"]
        assert viz["suggest"] is True
        # 3 unique countries → pie (≤7 categories); more categories would give bar
        assert viz["chart"] in ("pie", "bar", "bar_h")

    def test_user_requested_chart_is_rendered(self, engine_with_sales):
        coordinator = self._make_coordinator(
            engine_with_sales,
            "SELECT country, SUM(amount) AS total_sales FROM sales GROUP BY country",
        )
        output = coordinator.run(question="Bar chart of sales", user_requested_chart="bar")
        assert output["visualization"]["render"] is True
