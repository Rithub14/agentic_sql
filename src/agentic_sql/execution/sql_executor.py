from typing import List, Dict, Any

from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError

from agentic_sql.logger import get_logger

logger = get_logger(__name__)


class SQLExecutor:
    """
    Executes validated SQL and returns results as a list of dicts.
    Errors from the database are logged and re-raised so the coordinator
    can surface them correctly to the API layer.
    """

    def __init__(self, engine: Engine):
        self.engine = engine

    def run(self, sql: str) -> List[Dict[str, Any]]:
        logger.info("executing SQL", extra={"sql_preview": sql[:120]})
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text(sql))
                columns = list(result.keys())
                rows = result.fetchall()
        except SQLAlchemyError as exc:
            logger.error("SQL execution failed", extra={"error": str(exc), "sql_preview": sql[:120]})
            raise

        records = [dict(zip(columns, row)) for row in rows]
        logger.info("SQL executed successfully", extra={"row_count": len(records)})
        return records
