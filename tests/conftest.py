"""
Shared pytest fixtures.

All tests use in-memory SQLite so there are no relative-path issues and
each fixture is fully isolated — no state leaks between test runs.
"""
import pytest
from sqlalchemy import text
from sqlalchemy.engine import Engine

from agentic_sql.db.engine import get_engine

# In-memory SQLite: isolated, fast, no cleanup required
_IN_MEMORY_URL = "sqlite:///:memory:"


@pytest.fixture
def engine() -> Engine:
    """Bare in-memory engine — no tables created."""
    eng = get_engine(_IN_MEMORY_URL)
    yield eng
    eng.dispose()


@pytest.fixture
def engine_with_users(engine: Engine) -> Engine:
    """Engine pre-seeded with a `users` table."""
    with engine.begin() as conn:
        conn.execute(text(
            "CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT, age INTEGER)"
        ))
        conn.execute(text(
            "INSERT INTO users VALUES (1, 'Alice', 35), (2, 'Bob', 28), (3, 'Carol', 42)"
        ))
    return engine


@pytest.fixture
def engine_with_sales(engine: Engine) -> Engine:
    """Engine pre-seeded with a `sales` table."""
    with engine.begin() as conn:
        conn.execute(text(
            "CREATE TABLE sales (country TEXT, amount INTEGER)"
        ))
        conn.execute(text(
            "INSERT INTO sales VALUES ('DE', 100), ('FR', 80), ('US', 200)"
        ))
    return engine


@pytest.fixture
def engine_with_products(engine: Engine) -> Engine:
    """Engine pre-seeded with a `products` table."""
    with engine.begin() as conn:
        conn.execute(text(
            "CREATE TABLE products (id INTEGER PRIMARY KEY, name TEXT, price INTEGER)"
        ))
        conn.execute(text(
            "INSERT INTO products VALUES (1, 'Widget', 10), (2, 'Gadget', 25)"
        ))
    return engine
