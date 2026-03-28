import os
import re
from typing import Dict, Any, Optional

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI

from agentic_sql.logger import get_logger

logger = get_logger(__name__)


SYSTEM_PROMPT = """
You are a senior data engineer.

Convert the user's natural language question into a single valid SQL SELECT statement
that will run on the given database.

Rules:
- Use the exact table and column names from the schema.
- For PostgreSQL, quote identifiers exactly as they appear: e.g., "TableName"."ColumnName".
- Return ONLY the SQL query — no explanation, no markdown, no code fences.
- Never use DELETE, UPDATE, DROP, ALTER, INSERT, TRUNCATE, or CREATE.
- Never reference tables or columns that are not in the schema.
- If a JOIN is needed, infer it from foreign key annotations in the schema (FK->table.column).
"""

USER_PROMPT = """
Database schema:
{schema}

Question:
{question}
"""


class SQLAgent:
    """
    LLM-powered agent that converts natural language into a safe SQL SELECT statement.
    """

    def __init__(
        self,
        model: str = "gpt-4o-mini",
        temperature: float = 0.0,
        llm: Optional[Any] = None,
    ):
        api_key_present = bool(os.getenv("OPENAI_API_KEY"))
        if llm is None and not api_key_present:
            raise ValueError("OPENAI_API_KEY environment variable is required for SQL generation.")

        self.llm = llm or ChatOpenAI(model=model, temperature=temperature)

        self.prompt = ChatPromptTemplate.from_messages(
            [
                ("system", SYSTEM_PROMPT),
                ("user", USER_PROMPT),
            ]
        )

        self.chain = self.prompt | self.llm | StrOutputParser()

    @staticmethod
    def _strip_code_fences(text: str) -> str:
        """Remove Markdown code fences so downstream validators receive plain SQL."""
        match = re.search(r"```(?:sql)?\s*(.*?)\s*```", text, re.DOTALL | re.IGNORECASE)
        if match:
            return match.group(1)
        return text

    def run(self, question: str, schema: Dict[str, Any]) -> str:
        logger.info("generating SQL", extra={"question_preview": question[:120]})

        try:
            raw_sql = self.chain.invoke({"question": question, "schema": schema})
        except Exception:
            logger.exception("LLM call failed during SQL generation")
            raise

        sql = self._strip_code_fences(raw_sql).strip()
        logger.info("SQL generated", extra={"sql_preview": sql[:120]})
        return sql
