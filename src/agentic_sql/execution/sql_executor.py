from typing import List, Dict, Any

from sqlalchemy import text
from sqlalchemy.engine import Engine


class SQLExecutor:
    """
    Executes validated SQL and returns results as list of dicts.
    """

    def __init__(self, engine: Engine):
        self.engine = engine

    def run(self, sql: str) -> List[Dict[str, Any]]:
        with self.engine.connect() as conn:
            result = conn.execute(text(sql))
            columns = result.keys()
            rows = result.fetchall()

        return [dict(zip(columns, row)) for row in rows]
