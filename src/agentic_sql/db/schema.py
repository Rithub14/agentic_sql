from sqlalchemy import inspect
from sqlalchemy.engine import Engine


def inspect_schema(engine: Engine) -> dict:
    inspector = inspect(engine)

    schema: dict[str, dict[str, str]] = {}

    for table_name in inspector.get_table_names():
        columns = inspector.get_columns(table_name)
        schema[table_name] = {
            column["name"]: str(column["type"])
            for column in columns
        }

    return schema
