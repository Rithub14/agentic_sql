import time
from typing import TypedDict, Dict, Any, Optional

from langgraph.graph import StateGraph, END

from agentic_sql.agents.schema_agent import SchemaAgent
from agentic_sql.agents.sql_agent import SQLAgent
from agentic_sql.agents.validation_agent import ValidationAgent, SQLValidationError
from agentic_sql.execution.sql_executor import SQLExecutor
from agentic_sql.agents.visualization_agent import VisualizationAgent
from agentic_sql.db.engine import get_engine
from agentic_sql.logger import get_logger

logger = get_logger(__name__)


class AgentState(TypedDict):
    question: str
    schema: Dict[str, Any]
    sql: str
    validated_sql: str
    results: list[Dict[str, Any]]
    visualization: Dict[str, Any]
    user_requested_chart: Optional[str]


class CoordinatorAgent:
    """
    LangGraph-based coordinator that orchestrates the full NL→SQL pipeline.
    A NEW instance is created per request so each request gets its own DB connection.
    """

    def __init__(
        self,
        database_url: Optional[str] = None,
        sql_agent: Optional[SQLAgent] = None,
        engine=None,
    ):
        engine = engine or get_engine(database_url)

        self.schema_agent = SchemaAgent(engine)
        self.sql_agent = sql_agent or SQLAgent()
        self.validation_agent = ValidationAgent()
        self.executor = SQLExecutor(engine)
        self.visualization_agent = VisualizationAgent()

        self.graph = self._build_graph()

    # ------------------------------------------------------------------
    # Graph nodes — each logs its own duration for observability
    # ------------------------------------------------------------------

    def _get_schema(self, state: AgentState) -> AgentState:
        t0 = time.perf_counter()
        state["schema"] = self.schema_agent.run()
        logger.info("schema_agent completed", extra={"duration_ms": round((time.perf_counter() - t0) * 1000)})
        return state

    def _generate_sql(self, state: AgentState) -> AgentState:
        t0 = time.perf_counter()
        state["sql"] = self.sql_agent.run(
            question=state["question"],
            schema=state["schema"],
        )
        logger.info(
            "sql_agent completed",
            extra={"duration_ms": round((time.perf_counter() - t0) * 1000), "sql_preview": state["sql"][:120]},
        )
        return state

    def _validate_sql(self, state: AgentState) -> AgentState:
        t0 = time.perf_counter()
        state["validated_sql"] = self.validation_agent.run(state["sql"])
        logger.info("validation_agent completed", extra={"duration_ms": round((time.perf_counter() - t0) * 1000)})
        return state

    def _execute_sql(self, state: AgentState) -> AgentState:
        t0 = time.perf_counter()
        state["results"] = self.executor.run(state["validated_sql"])
        logger.info(
            "sql_executor completed",
            extra={"duration_ms": round((time.perf_counter() - t0) * 1000), "row_count": len(state["results"])},
        )
        return state

    def _visualize(self, state: AgentState) -> AgentState:
        t0 = time.perf_counter()
        state["visualization"] = self.visualization_agent.run(
            results=state["results"],
            user_requested_chart=state.get("user_requested_chart"),
        )
        logger.info("visualization_agent completed", extra={"duration_ms": round((time.perf_counter() - t0) * 1000)})
        return state

    def _build_graph(self) -> StateGraph:
        graph = StateGraph(AgentState)

        graph.add_node("schema", self._get_schema)
        graph.add_node("sql", self._generate_sql)
        graph.add_node("validate", self._validate_sql)
        graph.add_node("execute", self._execute_sql)
        graph.add_node("visualize", self._visualize)

        graph.set_entry_point("schema")
        graph.add_edge("schema", "sql")
        graph.add_edge("sql", "validate")
        graph.add_edge("validate", "execute")
        graph.add_edge("execute", "visualize")
        graph.add_edge("visualize", END)

        return graph.compile()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(
        self,
        question: str,
        user_requested_chart: Optional[str] = None,
    ) -> Dict[str, Any]:
        pipeline_start = time.perf_counter()
        logger.info("pipeline started", extra={"question_preview": question[:120]})

        initial_state: AgentState = {
            "question": question,
            "schema": {},
            "sql": "",
            "validated_sql": "",
            "results": [],
            "visualization": {},
            "user_requested_chart": user_requested_chart,
        }

        try:
            final_state = self.graph.invoke(initial_state)
        except SQLValidationError:
            # Re-raise so callers can return a 422 instead of 500
            raise
        except Exception:
            logger.exception("pipeline failed")
            raise

        total_ms = round((time.perf_counter() - pipeline_start) * 1000)
        logger.info("pipeline completed", extra={"total_ms": total_ms, "row_count": len(final_state["results"])})

        return {
            "sql": final_state["validated_sql"],
            "results": final_state["results"],
            "visualization": final_state["visualization"],
        }
