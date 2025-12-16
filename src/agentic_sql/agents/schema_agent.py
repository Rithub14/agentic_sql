from sqlalchemy.engine import Engine

from agentic_sql.db.schema import inspect_schema


class SchemaAgent:
    """
    Deterministic agent that returns database schema in an LLM-friendly format.
    """

    def __init__(self, engine: Engine):
        self.engine = engine

    def run(self) -> dict:
        """
        Returns:
            {
              "tables": {
                "table_name": {
                  "column_name": "TYPE",
                  ...
                },
                ...
              }
            }
        """
        raw_schema = inspect_schema(self.engine)

        return {
            "tables": raw_schema
        }
