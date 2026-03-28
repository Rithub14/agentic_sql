# Agentic SQL Explorer

Ask questions about your database in plain English and get SQL, results, and charts back — no SQL knowledge needed.

**Live demo:** https://agentic-sql-frontend.onrender.com (NBA dataset pre-loaded)

---

## What it does

Type a question like *"Which teams had the best winning percentage last season?"* and the app:

1. Inspects your database schema
2. Generates a SQL query via GPT-4o-mini
3. Validates it (blocks any destructive statements)
4. Executes it and returns results
5. Suggests or renders the best chart for the data
6. Explains what the query does in plain English

Supports follow-up questions with conversation context — ask *"now filter that by the Western Conference"* and it remembers the previous query.

---

## Stack

- **FastAPI** — backend API
- **LangGraph** — multi-agent pipeline orchestration
- **OpenAI GPT-4o-mini** — SQL generation and explanation
- **SQLAlchemy** — database connectivity (Postgres, MySQL, SQLite)
- **Streamlit** — frontend UI
- **Plotly** — charts

---

## Features

- Connect any Postgres, MySQL, or SQLite database
- Schema Explorer — see all tables and columns, get AI-suggested questions
- Click a suggested question to run it instantly
- Export results as CSV, Excel, or JSON
- Query history in the sidebar
- Rate limiting, structured JSON logging, request ID tracing

---

## Running locally

**With Docker (easiest):**

```bash
cp .env.template .env
# Add your OPENAI_API_KEY to .env
docker compose up --build
```

Open http://localhost:8501.

**Without Docker:**

```bash
uv sync
cp .env.template .env
# Terminal 1
make api
# Terminal 2
make frontend
```

Open http://localhost:8501, fill in your DB credentials, and start asking questions.

---

## Environment variables

| Variable | Description |
|---|---|
| `OPENAI_API_KEY` | Required for SQL generation |
| `DATABASE_URL` | Default DB for the backend |
| `API_BASE_URL` | Frontend → backend URL |
| `DEMO_DATABASE_URL` | Enables the "Use Demo DB" button |

Copy `.env.template` to `.env` and fill in the values.

---

## Testing

```bash
make test
```

39 tests, all using in-memory SQLite — no API key or live DB needed.

---

## Project structure

```
src/agentic_sql/
  agents/          # LangGraph pipeline nodes
  api/             # FastAPI routes
  db/              # Engine, schema inspection, ERD generation
  execution/       # SQL executor
frontend/          # Streamlit UI
scripts/           # DB seed scripts
tests/             # pytest suite
```
