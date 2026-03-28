from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import Optional, Any, Dict

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from agentic_sql.agents import CoordinatorAgent
from agentic_sql.agents.validation_agent import SQLValidationError
from agentic_sql.db.engine import get_engine
from agentic_sql.limiter import limiter
from agentic_sql.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class QueryRequest(BaseModel):
    question: str
    chart: Optional[str] = None
    database_url: str


class QueryResponse(BaseModel):
    sql: Optional[str]
    results: list[Dict[str, Any]]
    visualization: Dict[str, Any]
    request_id: Optional[str] = None


class TestConnectionRequest(BaseModel):
    database_url: str


class TestConnectionResponse(BaseModel):
    ok: bool
    message: Optional[str] = None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/query", response_model=QueryResponse, tags=["query"])
@limiter.limit("10/minute")
def run_query(request: Request, payload: QueryRequest):
    """
    Execute a natural-language query against the target database.

    Rate-limited to 10 requests per minute per IP.
    Returns HTTP 422 for invalid/unsafe SQL, 500 for unexpected errors
    (with a request_id for log correlation).
    """
    request_id: str = getattr(request.state, "request_id", "unknown")
    logger.info(
        "query request received",
        extra={"request_id": request_id, "question_preview": payload.question[:120]},
    )

    try:
        coordinator = CoordinatorAgent(database_url=payload.database_url)
        output = coordinator.run(
            question=payload.question,
            user_requested_chart=payload.chart,
        )
        output["request_id"] = request_id
        return output

    except SQLValidationError as exc:
        # Unsafe SQL is a client error — tell them what was wrong
        raise HTTPException(status_code=422, detail=str(exc))

    except Exception:
        logger.exception("query pipeline failed", extra={"request_id": request_id})
        raise HTTPException(
            status_code=500,
            detail=f"Query execution failed. Reference ID: {request_id}",
        )


@router.post("/test-connection", response_model=TestConnectionResponse, tags=["ops"])
def test_connection(payload: TestConnectionRequest):
    """Validate that the supplied database URL is reachable."""
    try:
        engine = get_engine(payload.database_url)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return TestConnectionResponse(ok=True)
    except (SQLAlchemyError, Exception) as exc:
        return TestConnectionResponse(ok=False, message=str(exc))
