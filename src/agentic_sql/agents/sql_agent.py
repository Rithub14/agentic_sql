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

    def run(self, question: str, schema: dict) -> str:
        sql = self.chain.invoke(
            {
                "question": question,
                "schema": schema,
            }
        )
        return sql.strip()
