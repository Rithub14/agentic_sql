import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

load_dotenv()


def get_engine(database_url: str | None = None, echo: bool = False) -> Engine:
    """
    Create a SQLAlchemy engine for the given database URL.
    Falls back to DATABASE_URL env var if not provided.

    PostgreSQL/MySQL: uses a connection pool with pre-ping so stale connections
    are detected before use.  SQLite: disables the pool (StaticPool isn't needed
    here; check_same_thread=False allows use from multiple threads as FastAPI
    can do).
    """
    url = database_url or os.getenv("DATABASE_URL")
    if not url:
        raise ValueError("DATABASE_URL is not set. Provide database_url or set the env var.")

    if url.startswith("sqlite"):
        return create_engine(
            url,
            echo=echo,
            connect_args={"check_same_thread": False},
        )

    return create_engine(
        url,
        echo=echo,
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True,   # Verify connection health before handing it out
        pool_recycle=3600,    # Recycle connections after 1 hour to avoid stale TCP issues
    )
