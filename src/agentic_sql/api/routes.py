from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional, Any, Dict

from agentic_sql.agents import CoordinatorAgent

router = APIRouter()
coordinator = CoordinatorAgent()


class QueryRequest(BaseModel):
    question: str
    chart: Optional[str] = None


class QueryResponse(BaseModel):
    sql: str
    results: list[Dict[str, Any]]
    visualization: Dict[str, Any]


@router.post("/query", response_model=QueryResponse)
def run_query(payload: QueryRequest):
    output = coordinator.run(
        question=payload.question,
        user_requested_chart=payload.chart,
    )

    return {
        "sql": output["sql"],
        "results": output["results"],
        "visualization": output["visualization"],
    }
