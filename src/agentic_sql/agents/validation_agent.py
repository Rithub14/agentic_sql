import re

from agentic_sql.logger import get_logger

logger = get_logger(__name__)

# Expanded set — includes database-specific destructive/escape commands
FORBIDDEN_KEYWORDS = frozenset({
    "drop",
    "delete",
    "update",
    "insert",
    "alter",
    "truncate",
    "create",
    "exec",
    "execute",
    "pragma",
    "attach",
    "detach",
    "load_extension",
})


class SQLValidationError(Exception):
    pass


def _strip_comments(sql: str) -> str:
    """Remove /* block */ and -- line comments so they can't hide forbidden keywords."""
    sql = re.sub(r"/\*.*?\*/", " ", sql, flags=re.DOTALL)
    sql = re.sub(r"--[^\n]*", " ", sql)
    return sql


def _strip_string_literals(sql: str) -> str:
    """Replace quoted string contents with empty strings to prevent keyword-in-string bypass."""
    sql = re.sub(r"'[^']*'", "''", sql)
    sql = re.sub(r'"[^"]*"', '""', sql)
    return sql


class ValidationAgent:
    """
    Deterministic agent that validates SQL safety.

    Strips comments and string literals before keyword scanning so constructs
    like  SELECT 1 /* DROP TABLE users */  or  SELECT 'delete' FROM t  are
    safely rejected / passed through correctly.
    """

    def __init__(self, default_limit: int = 1000):
        self.default_limit = default_limit

    def run(self, sql: str) -> str:
        # Validate against a sanitised copy so the original formatting is preserved
        clean = _strip_string_literals(_strip_comments(sql))
        clean_lower = clean.lower()

        for keyword in FORBIDDEN_KEYWORDS:
            if re.search(rf"\b{keyword}\b", clean_lower):
                logger.warning("Forbidden SQL keyword blocked", extra={"keyword": keyword})
                raise SQLValidationError(f"Forbidden SQL keyword detected: '{keyword}'")

        # Use word-boundary check so columns named e.g. "limit_date" are not confused with LIMIT
        if not re.search(r"\blimit\b", clean_lower):
            sql = f"{sql.rstrip(';').rstrip()} LIMIT {self.default_limit};"

        return sql
