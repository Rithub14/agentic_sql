import json
import os
import re
from typing import Any, Dict, List, Optional

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI

from agentic_sql.logger import get_logger

logger = get_logger(__name__)

SYSTEM_PROMPT = """You are a data analyst helping users explore a new database.
Given the database schema, suggest exactly 5 interesting analytical questions a user could ask.
Return ONLY a JSON array of 5 question strings — no other text, no numbering, no markdown.
Example format: ["Question 1?", "Question 2?", "Question 3?", "Question 4?", "Question 5?"]
Make questions specific to the actual tables and columns in the schema."""

USER_PROMPT = """Database schema:
{schema}

Return a JSON array of 5 interesting questions:"""


class SuggestionAgent:
    """
    LLM-powered agent that suggests analytical questions based on the database schema.
    """

    def __init__(
        self,
        model: str = "gpt-4o-mini",
        temperature: float = 0.7,
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

    def run(self, schema: Dict[str, Any]) -> List[str]:
        logger.info("generating query suggestions")
        try:
            raw = self.chain.invoke({"schema": schema})
        except Exception:
            logger.exception("LLM call failed during suggestion generation")
            return []

        # Parse JSON array from response
        try:
            match = re.search(r'\[.*?\]', raw, re.DOTALL)
            if match:
                suggestions = json.loads(match.group())
                return [s for s in suggestions if isinstance(s, str)][:5]
        except (json.JSONDecodeError, AttributeError):
            pass

        # Fallback: extract lines that look like questions
        lines = [ln.strip().lstrip("0123456789.-) ").strip() for ln in raw.split("\n") if ln.strip()]
        return [ln for ln in lines if "?" in ln][:5]
