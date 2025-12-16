from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

from agentic_sql.db.config import get_database_url


def get_engine(echo: bool = False) -> Engine:
    database_url = get_database_url()
    engine = create_engine(database_url, echo=echo, future=True)
    return engine
