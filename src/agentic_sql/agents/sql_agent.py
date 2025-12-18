import os
import re
from typing import Dict, Any

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI


SYSTEM_PROMPT = """
You are a senior data engineer.

Convert the user’s natural language question into a single valid SQL statement
that will run on the given database.

Use the exact table and column names from the schema. 
For PostgreSQL in particular, quote identifiers exactly as they appear:
e.g., "TableName"."ColumnName".

Do NOT:
- Use DELETE, UPDATE, DROP, ALTER, INSERT
- Use unrecognized tables/columns
- Return anything other than the SQL query itself
No explanations, no markdown.
"""

USER_PROMPT = """
Database schema:
{schema}

Question:
{question}
"""


class SQLAgent:
    """
    LLM-powered agent that converts natural language into safe SQL.
    """

    def __init__(
        self,
        model: str = "gpt-4o-mini",
        temperature: float = 0.0,
        use_mock_if_no_api_key: bool = True,
    ):
        self.use_mock = use_mock_if_no_api_key and not os.getenv("OPENAI_API_KEY")

        if not self.use_mock:
            self.llm = ChatOpenAI(model=model, temperature=temperature)

            self.prompt = ChatPromptTemplate.from_messages(
                [
                    ("system", SYSTEM_PROMPT),
                    ("user", USER_PROMPT),
                ]
            )

            self.chain = self.prompt | self.llm | StrOutputParser()
        else:
            self.llm = None
            self.chain = None

    @staticmethod
    def _strip_code_fences(text: str) -> str:
        """
        Remove Markdown code fences so downstream validators/executors
        receive plain SQL.
        """
        match = re.search(r"```(?:sql)?\s*(.*?)\s*```", text, re.DOTALL | re.IGNORECASE)
        if match:
            return match.group(1)
        return text

    def _mock_sql(self, question: str, schema: Dict[str, Any]) -> str:
        """Fallback deterministic SQL generator for offline/testing."""
        tables = schema.get("tables") or {}
        table_name = next(iter(tables), "results")
        columns = tables.get(table_name, {})

        question_lower = question.lower()
        where_clause = ""

        # Simple heuristic for "older/greater than N"
        match = re.search(r"(?:older|greater) than (\d+)", question_lower)
        if match and "age" in {c.lower() for c in columns}:
            where_clause = f"WHERE age > {match.group(1)}"

        sql = f"SELECT * FROM {table_name}"
        if where_clause:
            sql += f" {where_clause}"
        return f"{sql};"

    def run(self, question: str, schema: dict) -> str:
        if self.use_mock:
            return self._mock_sql(question, schema)

        raw_sql = self.chain.invoke(
            {
                "question": question,
                "schema": schema,
            }
        )
        sql = self._strip_code_fences(raw_sql)
        return sql.strip()
