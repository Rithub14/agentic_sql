from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Any, Dict

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from agentic_sql.agents import CoordinatorAgent
from agentic_sql.db.engine import get_engine

router = APIRouter()


class QueryRequest(BaseModel):
    question: str
    chart: Optional[str] = None
    database_url: str


class QueryResponse(BaseModel):
    sql: Optional[str]
    results: list[Dict[str, Any]]
    visualization: Dict[str, Any]


class TestConnectionRequest(BaseModel):
    database_url: str


class TestConnectionResponse(BaseModel):
    ok: bool
    message: Optional[str] = None


@router.post("/query", response_model=QueryResponse)
def run_query(payload: QueryRequest):
    try:
        coordinator = CoordinatorAgent(
            database_url=payload.database_url
        )

        output = coordinator.run(
            question=payload.question,
            user_requested_chart=payload.chart,
        )

        return output

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/test-connection", response_model=TestConnectionResponse)
def test_connection(payload: TestConnectionRequest):
    try:
        engine = get_engine(payload.database_url)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return TestConnectionResponse(ok=True)
    except SQLAlchemyError as e:
        return TestConnectionResponse(ok=False, message=str(e))
    except Exception as e:
        return TestConnectionResponse(ok=False, message=str(e))
