from contextlib import contextmanager
from typing import Iterator
from sqlalchemy.engine import Connection

from agentic_sql.db.engine import get_engine


@contextmanager
def get_connection() -> Iterator[Connection]:
    engine = get_engine()
    with engine.connect() as connection:
        yield connection
