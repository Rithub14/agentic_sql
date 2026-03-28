import os
from typing import Any, Optional

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI

from agentic_sql.logger import get_logger

logger = get_logger(__name__)

SYSTEM_PROMPT = """You are a data analyst explaining SQL queries to non-technical stakeholders.
Explain what the SQL query does in 2-3 clear, plain-English sentences.
Focus on: what data is retrieved, any filters applied, how data is grouped or aggregated.
Do not use SQL keywords or technical jargon. Be concise and direct."""

USER_PROMPT = """SQL Query:
{sql}

Explain what this query does in plain English:"""


class ExplanationAgent:
    """
    LLM-powered agent that explains a SQL query in plain English.
    Called after execution so it knows the query ran successfully.
    """

    def __init__(
        self,
        model: str = "gpt-4o-mini",
        temperature: float = 0.3,
        llm: Optional[Any] = None,
    ):
        api_key_present = bool(os.getenv("OPENAI_API_KEY"))
        if llm is None and not api_key_present:
            raise ValueError("OPENAI_API_KEY environment variable is required.")

        self.llm = llm or ChatOpenAI(model=model, temperature=temperature)
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", SYSTEM_PROMPT),
            ("user", USER_PROMPT),
        ])
        self.chain = self.prompt | self.llm | StrOutputParser()

    def run(self, sql: str) -> str:
        logger.info("generating SQL explanation")
        try:
            explanation = self.chain.invoke({"sql": sql})
        except Exception:
            logger.exception("LLM call failed during explanation")
            return ""
        return explanation.strip()
