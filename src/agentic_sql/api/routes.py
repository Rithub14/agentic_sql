from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import Optional, Any, Dict, List

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from agentic_sql.agents import CoordinatorAgent
from agentic_sql.agents.schema_agent import SchemaAgent
from agentic_sql.agents.suggestion_agent import SuggestionAgent
from agentic_sql.agents.validation_agent import SQLValidationError
from agentic_sql.db.engine import get_engine
from agentic_sql.db.erd import schema_to_mermaid
from agentic_sql.limiter import limiter
from agentic_sql.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class ConversationTurn(BaseModel):
    question: str
    sql: str


class QueryRequest(BaseModel):
    question: str
    chart: Optional[str] = None
    database_url: str
    conversation_history: List[ConversationTurn] = []


class QueryResponse(BaseModel):
    sql: Optional[str]
    results: List[Dict[str, Any]]
    visualization: Dict[str, Any]
    explanation: Optional[str] = None
    request_id: Optional[str] = None


class TestConnectionRequest(BaseModel):
    database_url: str


class TestConnectionResponse(BaseModel):
    ok: bool
    message: Optional[str] = None


class SchemaRequest(BaseModel):
    database_url: str


class SchemaResponse(BaseModel):
    tables: Dict[str, Any]
    mermaid: str


class SuggestionsRequest(BaseModel):
    database_url: str


class SuggestionsResponse(BaseModel):
    suggestions: List[str]


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/query", response_model=QueryResponse, tags=["query"])
@limiter.limit("10/minute")
def run_query(request: Request, payload: QueryRequest):
    """
    Execute a natural-language query against the target database.

    Rate-limited to 10 requests per minute per IP.
    Returns HTTP 422 for invalid/unsafe SQL, 500 for unexpected errors.
    Supports conversation_history for multi-turn follow-up queries.
    """
    request_id: str = getattr(request.state, "request_id", "unknown")
    logger.info(
        "query request received",
        extra={"request_id": request_id, "question_preview": payload.question[:120]},
    )

    history = [t.model_dump() for t in payload.conversation_history]

    try:
        coordinator = CoordinatorAgent(database_url=payload.database_url)
        output = coordinator.run(
            question=payload.question,
            user_requested_chart=payload.chart,
            conversation_history=history,
        )
        output["request_id"] = request_id
        return output

    except SQLValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    except Exception:
        logger.exception("query pipeline failed", extra={"request_id": request_id})
        raise HTTPException(
            status_code=500,
            detail=f"Query execution failed. Reference ID: {request_id}",
        )


@router.post("/schema", response_model=SchemaResponse, tags=["schema"])
@limiter.limit("20/minute")
def get_schema(request: Request, payload: SchemaRequest):
    """
    Inspect the database schema and return table/column info plus a Mermaid ERD string.
    """
    try:
        engine = get_engine(payload.database_url)
        schema_agent = SchemaAgent(engine)
        schema = schema_agent.run()
        mermaid = schema_to_mermaid(schema)
        return SchemaResponse(tables=schema.get("tables", {}), mermaid=mermaid)
    except (SQLAlchemyError, Exception) as exc:
        logger.exception("schema inspection failed")
        raise HTTPException(status_code=500, detail=f"Schema inspection failed: {exc}")


@router.post("/suggestions", response_model=SuggestionsResponse, tags=["schema"])
@limiter.limit("10/minute")
def get_suggestions(request: Request, payload: SuggestionsRequest):
    """
    Return up to 5 LLM-generated analytical questions based on the database schema.
    """
    try:
        engine = get_engine(payload.database_url)
        schema_agent = SchemaAgent(engine)
        schema = schema_agent.run()
        suggestion_agent = SuggestionAgent()
        suggestions = suggestion_agent.run(schema)
        return SuggestionsResponse(suggestions=suggestions)
    except (SQLAlchemyError, Exception) as exc:
        logger.exception("suggestion generation failed")
        raise HTTPException(status_code=500, detail=f"Suggestion generation failed: {exc}")


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
