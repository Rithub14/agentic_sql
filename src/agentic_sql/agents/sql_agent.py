import re

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI


SYSTEM_PROMPT = """
You are a senior data engineer.

Your task:
- Convert a natural language question into a SINGLE valid SQL query.
- Use ONLY the provided database schema.
- Do NOT hallucinate tables or columns.
- Do NOT use DELETE, UPDATE, DROP, INSERT, ALTER.
- Return ONLY SQL. No explanations.
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

    def __init__(self, model: str = "gpt-4o-mini", temperature: float = 0.0):
        self.llm = ChatOpenAI(model=model, temperature=temperature)

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
