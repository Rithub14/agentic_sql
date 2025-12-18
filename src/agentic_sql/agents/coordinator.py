from typing import TypedDict, Dict, Any, Optional

from langgraph.graph import StateGraph, END

from agentic_sql.agents.schema_agent import SchemaAgent
from agentic_sql.agents.sql_agent import SQLAgent
from agentic_sql.agents.validation_agent import ValidationAgent
from agentic_sql.execution.sql_executor import SQLExecutor
from agentic_sql.agents.visualization_agent import VisualizationAgent
from agentic_sql.db.engine import get_engine


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
    LangGraph-based coordinator.
    A NEW instance is created per request with a user-selected database.
    """

    def __init__(self, database_url: Optional[str] = None):
        engine = get_engine(database_url)

        self.schema_agent = SchemaAgent(engine)
        self.sql_agent = SQLAgent()
        self.validation_agent = ValidationAgent()
        self.executor = SQLExecutor(engine)
        self.visualization_agent = VisualizationAgent()

        self.graph = self._build_graph()

    # -------------------------
    # Graph nodes
    # -------------------------

    def _get_schema(self, state: AgentState) -> AgentState:
        state["schema"] = self.schema_agent.run()
        return state

    def _generate_sql(self, state: AgentState) -> AgentState:
        state["sql"] = self.sql_agent.run(
            question=state["question"],
            schema=state["schema"],
        )
        return state

    def _validate_sql(self, state: AgentState) -> AgentState:
        state["validated_sql"] = self.validation_agent.run(state["sql"])
        return state

    def _execute_sql(self, state: AgentState) -> AgentState:
        state["results"] = self.executor.run(state["validated_sql"])
        return state

    def _visualize(self, state: AgentState) -> AgentState:
        state["visualization"] = self.visualization_agent.run(
            results=state["results"],
            user_requested_chart=state.get("user_requested_chart"),
        )
        return state

    # -------------------------
    # Graph construction
    # -------------------------

    def _build_graph(self):
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

    # -------------------------
    # Public API
    # -------------------------

    def run(
        self,
        question: str,
        user_requested_chart: Optional[str] = None,
    ) -> Dict[str, Any]:

        initial_state: AgentState = {
            "question": question,
            "schema": {},
            "sql": "",
            "validated_sql": "",
            "results": [],
            "visualization": {},
            "user_requested_chart": user_requested_chart,
        }

        final_state = self.graph.invoke(initial_state)

        return {
            "sql": final_state["validated_sql"],
            "results": final_state["results"],
            "visualization": final_state["visualization"],
        }
