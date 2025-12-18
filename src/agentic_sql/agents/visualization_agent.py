from typing import List, Dict, Any, Optional


class VisualizationAgent:
    """
    Determines whether a visualization should be rendered or suggested,
    and returns a visualization specification.
    """

    def run(
        self,
        results: List[Dict[str, Any]],
        user_requested_chart: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not results:
            return {
                "render": False,
                "suggest": False,
                "chart": None,
                "spec": None,
                "message": "No data returned from query.",
            }

        columns = results[0].keys()
        numeric_cols = [
            col for col in columns
            if isinstance(results[0][col], (int, float))
        ]
        categorical_cols = [
            col for col in columns
            if col not in numeric_cols
        ]

        if user_requested_chart:
            return {
                "render": True,
                "suggest": False,
                "chart": user_requested_chart,
                "spec": self._build_spec(
                    user_requested_chart, categorical_cols, numeric_cols
                ),
                "message": None,
            }

        if categorical_cols and numeric_cols:
            suggested_chart = "bar"

            return {
                "render": False,
                "suggest": True,
                "chart": suggested_chart,
                "spec": self._build_spec(
                    suggested_chart, categorical_cols, numeric_cols
                ),
                "message": (
                    "This result compares numeric values across categories. "
                    "A bar chart would help visualize this better. "
                    "Would you like to generate it?"
                ),
            }

        return {
            "render": False,
            "suggest": False,
            "chart": None,
            "spec": None,
            "message": None,
        }

    def _build_spec(
        self,
        chart: str,
        categorical_cols: List[str],
        numeric_cols: List[str],
    ) -> Dict[str, Any]:
        return {
            "chart": chart,
            "x": categorical_cols[0] if categorical_cols else None,
            "y": numeric_cols[0] if numeric_cols else None,
        }
