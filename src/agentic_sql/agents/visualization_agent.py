import re
from typing import List, Dict, Any, Optional

from agentic_sql.logger import get_logger

logger = get_logger(__name__)

_TYPE_SAMPLE_SIZE = 20

# Column name fragments that indicate a date/time axis
_DATE_KEYWORDS = frozenset({
    "date", "time", "year", "month", "day",
    "season", "period", "week", "quarter", "created", "updated",
})

# Simple ISO-date pattern: 2023-01-15 or 2023-01-15T00:00:00
_DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}")

# Horizontal bar is better when there are many categories
_H_BAR_THRESHOLD = 10

# Pie chart only looks good with few slices
_PIE_MAX_CATEGORIES = 7


def _fmt(col: str) -> str:
    """Turn snake_case into Title Case for chart titles/labels."""
    return col.replace("_", " ").title()


class VisualizationAgent:
    """
    Analyses query results and returns a rich visualization spec.

    Chart selection logic (in priority order):
      1. date/time column present          → line chart
      2. two numeric columns               → scatter plot
      3. one numeric, no categories        → histogram
      4. categories + numeric(s):
           ≤ PIE_MAX_CATEGORIES & 1 num    → pie
           > H_BAR_THRESHOLD categories    → horizontal bar
           otherwise                       → vertical bar (grouped if multi-y)

    The spec ``y`` field is always a list so the frontend can render
    multi-series charts without special-casing.
    """

    def run(
        self,
        results: List[Dict[str, Any]],
        user_requested_chart: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not results:
            return {"render": False, "suggest": False, "chart": None, "spec": None,
                    "message": "No data returned from query."}

        columns = list(results[0].keys())
        numeric_cols, categorical_cols = self._classify_columns(results, columns)
        date_cols = self._detect_date_columns(results, categorical_cols)
        # Treat date cols as neither numeric nor plain categorical
        non_date_cats = [c for c in categorical_cols if c not in date_cols]

        if user_requested_chart:
            spec = self._build_spec_for(
                user_requested_chart, date_cols, non_date_cats, numeric_cols
            )
            can_render = spec is not None
            return {
                "render": can_render,
                "suggest": False,
                "chart": user_requested_chart,
                "spec": spec,
                "message": None if can_render else "Not enough columns to render this chart type.",
            }

        chart, spec = self._auto_select(date_cols, non_date_cats, numeric_cols, results)
        if chart is None:
            return {"render": False, "suggest": False, "chart": None, "spec": None, "message": None}

        message = self._suggestion_message(chart)
        return {
            "render": False,
            "suggest": True,
            "chart": chart,
            "spec": spec,
            "message": message,
        }

    # ------------------------------------------------------------------
    # Chart selection
    # ------------------------------------------------------------------

    def _auto_select(
        self,
        date_cols: List[str],
        cat_cols: List[str],
        num_cols: List[str],
        results: List[Dict[str, Any]],
    ):
        # 1. Time series
        if date_cols and num_cols:
            x = date_cols[0]
            y = num_cols[:3]
            return "line", self._make_spec("line", x, y, title=f"{_fmt(y[0])} over {_fmt(x)}")

        # 2. Two numeric → scatter
        if len(num_cols) >= 2 and not cat_cols:
            x, y = num_cols[0], num_cols[1]
            color = cat_cols[0] if cat_cols else None
            return "scatter", self._make_spec(
                "scatter", x, [y], color=color,
                title=f"{_fmt(y)} vs {_fmt(x)}"
            )

        if len(num_cols) >= 2 and cat_cols:
            x, y = num_cols[0], num_cols[1]
            return "scatter", self._make_spec(
                "scatter", x, [y], color=cat_cols[0],
                title=f"{_fmt(y)} vs {_fmt(x)}"
            )

        # 3. Single numeric, no categories → histogram
        if len(num_cols) == 1 and not cat_cols:
            return "histogram", self._make_spec(
                "histogram", num_cols[0], [],
                title=f"Distribution of {_fmt(num_cols[0])}"
            )

        # 4. Categories + numerics
        if cat_cols and num_cols:
            n_unique = len({str(r.get(cat_cols[0])) for r in results})
            y_cols = num_cols[:3]

            if n_unique <= _PIE_MAX_CATEGORIES and len(num_cols) == 1:
                return "pie", self._make_spec(
                    "pie", cat_cols[0], num_cols[:1],
                    title=f"{_fmt(num_cols[0])} by {_fmt(cat_cols[0])}"
                )

            if n_unique > _H_BAR_THRESHOLD:
                return "bar_h", self._make_spec(
                    "bar_h", cat_cols[0], y_cols,
                    title=f"{_fmt(y_cols[0])} by {_fmt(cat_cols[0])}"
                )

            barmode = "group" if len(y_cols) > 1 else None
            return "bar", self._make_spec(
                "bar", cat_cols[0], y_cols,
                barmode=barmode,
                title=f"{_fmt(y_cols[0])} by {_fmt(cat_cols[0])}"
            )

        return None, None

    def _build_spec_for(
        self,
        chart: str,
        date_cols: List[str],
        cat_cols: List[str],
        num_cols: List[str],
    ) -> Optional[Dict[str, Any]]:
        """Build the best spec for a user-requested chart type."""
        if chart == "bar":
            if cat_cols and num_cols:
                return self._make_spec("bar", cat_cols[0], num_cols[:3],
                                       barmode="group" if len(num_cols) > 1 else None,
                                       title=f"{_fmt(num_cols[0])} by {_fmt(cat_cols[0])}")
        elif chart == "bar_h":
            if cat_cols and num_cols:
                return self._make_spec("bar_h", cat_cols[0], num_cols[:1],
                                       title=f"{_fmt(num_cols[0])} by {_fmt(cat_cols[0])}")
        elif chart == "line":
            x = date_cols[0] if date_cols else (cat_cols[0] if cat_cols else None)
            if x and num_cols:
                return self._make_spec("line", x, num_cols[:3],
                                       title=f"{_fmt(num_cols[0])} over {_fmt(x)}")
        elif chart == "scatter":
            if len(num_cols) >= 2:
                return self._make_spec("scatter", num_cols[0], [num_cols[1]],
                                       color=cat_cols[0] if cat_cols else None,
                                       title=f"{_fmt(num_cols[1])} vs {_fmt(num_cols[0])}")
        elif chart == "histogram":
            if num_cols:
                return self._make_spec("histogram", num_cols[0], [],
                                       title=f"Distribution of {_fmt(num_cols[0])}")
        elif chart == "pie":
            if cat_cols and num_cols:
                return self._make_spec("pie", cat_cols[0], num_cols[:1],
                                       title=f"{_fmt(num_cols[0])} by {_fmt(cat_cols[0])}")
        return None

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _make_spec(
        self,
        chart: str,
        x: Optional[str],
        y: List[str],
        color: Optional[str] = None,
        title: str = "",
        barmode: Optional[str] = None,
    ) -> Dict[str, Any]:
        return {
            "chart": chart,
            "x": x,
            "y": y,           # always a list
            "color": color,
            "title": title,
            "barmode": barmode,
        }

    def _suggestion_message(self, chart: str) -> str:
        labels = {
            "bar":       "A bar chart would help compare values across categories.",
            "bar_h":     "A horizontal bar chart works well with many categories.",
            "line":      "A line chart would show how values change over time.",
            "scatter":   "A scatter plot would reveal the relationship between these two measures.",
            "histogram": "A histogram would show the distribution of values.",
            "pie":       "A pie chart would show the proportion of each category.",
        }
        base = labels.get(chart, "A chart would help visualize this data.")
        return f"{base} Would you like to generate it?"

    def _classify_columns(
        self, results: List[Dict[str, Any]], columns: List[str]
    ) -> tuple[List[str], List[str]]:
        sample = results[: min(len(results), _TYPE_SAMPLE_SIZE)]
        numeric_votes: Dict[str, int] = {c: 0 for c in columns}
        total_votes: Dict[str, int] = {c: 0 for c in columns}

        for row in sample:
            for col in columns:
                val = row.get(col)
                if val is None:
                    continue
                total_votes[col] += 1
                if isinstance(val, (int, float)) and not isinstance(val, bool):
                    numeric_votes[col] += 1

        numeric_cols = [
            c for c in columns
            if total_votes[c] > 0 and numeric_votes[c] / total_votes[c] > 0.5
        ]
        categorical_cols = [c for c in columns if c not in numeric_cols]
        return numeric_cols, categorical_cols

    def _detect_date_columns(
        self, results: List[Dict[str, Any]], categorical_cols: List[str]
    ) -> List[str]:
        """
        A column is considered a date/time axis if its name contains a date keyword
        OR its values match an ISO-date pattern.
        """
        date_cols = []
        sample_row = results[0] if results else {}

        for col in categorical_cols:
            name_match = any(kw in col.lower() for kw in _DATE_KEYWORDS)
            val = str(sample_row.get(col, ""))
            value_match = bool(_DATE_PATTERN.match(val))
            if name_match or value_match:
                date_cols.append(col)

        return date_cols
