import re


FORBIDDEN_KEYWORDS = (
    "drop",
    "delete",
    "update",
    "insert",
    "alter",
    "truncate",
    "create",
)


class SQLValidationError(Exception):
    pass


class ValidationAgent:
    """
    Deterministic agent that validates SQL safety.
    """

    def __init__(self, default_limit: int = 1000):
        self.default_limit = default_limit

    def run(self, sql: str) -> str:
        sql_lower = sql.lower()

        for keyword in FORBIDDEN_KEYWORDS:
            if re.search(rf"\b{keyword}\b", sql_lower):
                raise SQLValidationError(f"Forbidden SQL keyword detected: {keyword}")

        if "limit" not in sql_lower:
            sql = f"{sql.rstrip(';')} LIMIT {self.default_limit};"

        return sql
