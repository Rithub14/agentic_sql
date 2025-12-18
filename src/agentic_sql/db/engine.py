import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine


load_dotenv()


def get_engine(database_url: str | None = None, echo: bool = False) -> Engine:
    """
    Create a SQLAlchemy engine for the given database URL.
    Falls back to DATABASE_URL env var if not provided.
    """
    url = database_url or os.getenv("DATABASE_URL")
    if not url:
        raise ValueError("DATABASE_URL is not set. Provide database_url or set env var.")

    return create_engine(url, echo=echo, future=True)
