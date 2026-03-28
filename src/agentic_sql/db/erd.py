import re
from typing import Any, Dict

_FK_PATTERN = re.compile(r"FK->(\w+)\.\w+")


def _mermaid_type(type_str: str) -> str:
    """
    Extract a Mermaid-compatible base type from a SQLAlchemy type string
    that may contain PK/FK annotations.

    Examples:
        "INTEGER PK"              → "INTEGER"
        "INTEGER FK->users.id"    → "INTEGER"
        "VARCHAR(255)"            → "VARCHAR"
        "TIMESTAMP WITHOUT TIME"  → "TIMESTAMP"
    """
    # Strip PK and FK annotations
    clean = re.sub(r"\s*(PK|FK->\S+)", "", type_str).strip()
    # Take only the first alphanumeric token (no parentheses or spaces)
    base = re.split(r"[\s(]", clean)[0]
    return base or "TEXT"


def schema_to_mermaid(schema: Dict[str, Any]) -> str:
    """
    Convert an inspect_schema() result dict to a Mermaid erDiagram string.

    Input format:
        {
            "tables": {
                "users": {"id": "INTEGER PK", "name": "VARCHAR"},
                "orders": {"id": "INTEGER PK", "user_id": "INTEGER FK->users.id"}
            }
        }

    Output:
        erDiagram
            users {
                INTEGER id PK
                VARCHAR name
            }
            orders {
                INTEGER id PK
                INTEGER user_id FK
            }
            orders }o--|| users : ""
    """
    tables = schema.get("tables", {})
    if not tables:
        return "erDiagram\n    %% No tables found"

    lines = ["erDiagram"]
    relationships: set[str] = set()

    for table_name, columns in tables.items():
        lines.append(f"    {table_name} {{")
        for col_name, col_type in columns.items():
            mtype = _mermaid_type(col_type)

            if "PK" in col_type:
                annotation = " PK"
            elif "FK->" in col_type:
                annotation = " FK"
            else:
                annotation = ""

            lines.append(f"        {mtype} {col_name}{annotation}")

            fk_match = _FK_PATTERN.search(col_type)
            if fk_match:
                ref_table = fk_match.group(1)
                relationships.add(f'    {table_name} }}o--|| {ref_table} : ""')

        lines.append("    }")

    lines.extend(sorted(relationships))
    return "\n".join(lines)
