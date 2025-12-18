import os
import re
from typing import Dict, Any, Optional

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
        llm: Optional[Any] = None,
    ):
        api_key_present = bool(os.getenv("OPENAI_API_KEY"))
        if llm is None and not api_key_present:
            raise ValueError("OPENAI_API_KEY is required for SQL generation.")

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
        """
        Remove Markdown code fences so downstream validators/executors
        receive plain SQL.
        """
        match = re.search(r"```(?:sql)?\s*(.*?)\s*```", text, re.DOTALL | re.IGNORECASE)
        if match:
            return match.group(1)
        return text

    def run(self, question: str, schema: dict) -> str:
        raw_sql = self.chain.invoke(
            {
                "question": question,
                "schema": schema,
            }
        )
        sql = self._strip_code_fences(raw_sql)
        return sql.strip()
