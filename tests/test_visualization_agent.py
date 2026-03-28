from agentic_sql.agents.visualization_agent import VisualizationAgent


class TestVisualizationAgent:
    def setup_method(self):
        self.agent = VisualizationAgent()

    def test_suggests_bar_chart_for_categorical_and_numeric(self):
        results = [
            {"country": "DE", "total_sales": 100},
            {"country": "FR", "total_sales": 80},
        ]
        out = self.agent.run(results)
        assert out["suggest"] is True
        assert out["chart"] == "pie"  # 2 categories → pie
        assert out["spec"]["x"] == "country"
        assert "total_sales" in out["spec"]["y"]

    def test_many_categories_suggests_bar(self):
        results = [{"country": c, "sales": i * 10} for i, c in enumerate(
            ["DE", "FR", "US", "UK", "JP", "CN", "IN", "BR", "AU", "CA", "MX"]
        )]
        out = self.agent.run(results)
        assert out["suggest"] is True
        assert out["chart"] in ("bar", "bar_h")

    def test_renders_when_user_requests_line_chart(self):
        results = [
            {"month": "Jan", "revenue": 200},
            {"month": "Feb", "revenue": 250},
        ]
        out = self.agent.run(results, user_requested_chart="line")
        assert out["render"] is True
        assert out["chart"] == "line"
        assert out["spec"]["x"] == "month"
        assert "revenue" in out["spec"]["y"]

    def test_y_is_always_a_list(self):
        results = [{"country": "DE", "sales": 100}, {"country": "FR", "sales": 80}]
        out = self.agent.run(results, user_requested_chart="bar")
        assert isinstance(out["spec"]["y"], list)

    def test_two_numeric_columns_suggests_scatter(self):
        results = [{"height": 200, "weight": 100}, {"height": 195, "weight": 95}]
        out = self.agent.run(results)
        assert out["suggest"] is True
        assert out["chart"] == "scatter"

    def test_single_numeric_no_category_suggests_histogram(self):
        results = [{"score": i} for i in range(20)]
        out = self.agent.run(results)
        assert out["suggest"] is True
        assert out["chart"] == "histogram"

    def test_no_results_returns_no_render(self):
        out = self.agent.run([])
        assert out["render"] is False
        assert out["suggest"] is False
        assert out["spec"] is None

    def test_type_inference_uses_majority_not_first_row(self):
        results = [
            {"label": "A", "amount": None},
            {"label": "B", "amount": 50},
            {"label": "C", "amount": 75},
            {"label": "D", "amount": 90},
        ]
        out = self.agent.run(results)
        assert out["suggest"] is True
        assert "amount" in out["spec"]["y"]

    def test_user_requested_chart_with_missing_columns_does_not_render(self):
        results = [{"name": "Alice"}, {"name": "Bob"}]
        out = self.agent.run(results, user_requested_chart="bar")
        assert out["render"] is False
        assert out["spec"] is None

    def test_date_column_suggests_line(self):
        results = [
            {"game_date": "2023-01-01", "pts": 110},
            {"game_date": "2023-01-02", "pts": 105},
        ]
        out = self.agent.run(results)
        assert out["suggest"] is True
        assert out["chart"] == "line"
        assert out["spec"]["x"] == "game_date"
