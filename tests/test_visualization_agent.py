from agentic_sql.agents.visualization_agent import VisualizationAgent


def test_visualization_suggestion():
    results = [
        {"country": "DE", "total_sales": 100},
        {"country": "FR", "total_sales": 80},
    ]

    agent = VisualizationAgent()
    output = agent.run(results)

    assert output["suggest"] is True
    assert output["chart"] == "bar"
    assert output["spec"]["x"] == "country"
    assert output["spec"]["y"] == "total_sales"


def test_visualization_render_when_requested():
    results = [
        {"month": "Jan", "revenue": 200},
        {"month": "Feb", "revenue": 250},
    ]

    agent = VisualizationAgent()
    output = agent.run(results, user_requested_chart="line")

    assert output["render"] is True
    assert output["chart"] == "line"
