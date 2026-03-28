from sqlalchemy import inspect
from sqlalchemy.engine import Engine

from agentic_sql.logger import get_logger

logger = get_logger(__name__)


def inspect_schema(engine: Engine) -> dict:
    """
    Return a dict keyed by table name.  Each value is a dict of column_name → type_string.

    The type string is enriched with PK and FK annotations so the LLM can generate
    accurate JOINs without additional prompting:
        "id":      "INTEGER PK"
        "user_id": "INTEGER FK->users.id"
    """
    inspector = inspect(engine)
    table_names = inspector.get_table_names()

    if not table_names:
        logger.warning("Schema inspection returned no tables")

    schema: dict[str, dict[str, str]] = {}

    for table_name in table_names:
        # --- primary keys ---
        try:
            pk_cols = set(inspector.get_pk_constraint(table_name).get("constrained_columns", []))
        except Exception:
            pk_cols = set()

        # --- foreign keys: constrained_col → "referred_table.referred_col" ---
        fk_map: dict[str, str] = {}
        try:
            for fk in inspector.get_foreign_keys(table_name):
                for src_col, ref_col in zip(
                    fk.get("constrained_columns", []),
                    fk.get("referred_columns", []),
                ):
                    fk_map[src_col] = f"{fk['referred_table']}.{ref_col}"
        except Exception:
            pass

        # --- columns ---
        try:
            columns = inspector.get_columns(table_name)
        except Exception as exc:
            logger.warning("Could not inspect columns", extra={"table": table_name, "error": str(exc)})
            continue

        col_schema: dict[str, str] = {}
        for col in columns:
            col_name = col["name"]
            type_str = str(col["type"])
            if col_name in pk_cols:
                type_str += " PK"
            if col_name in fk_map:
                type_str += f" FK->{fk_map[col_name]}"
            col_schema[col_name] = type_str

        schema[table_name] = col_schema

    return schema
