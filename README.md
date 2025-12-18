Agentic SQL Explorer
====================

Natural‑language to SQL with optional visualization. FastAPI backend orchestrates schema inspection, SQL generation/validation, execution, and viz suggestion; Streamlit frontend lets non‑technical users connect a database, ask questions, test connectivity, and view results.

## Key features
- Structured DB connection form (Postgres/MySQL/SQLite), no raw URLs required; built‑in “Test connection”.
- Requires OpenAI for SQL generation; set `OPENAI_API_KEY`.
- LangGraph‑based coordinator: schema agent → SQL agent → validation → execution → visualization agent.
- Docker Compose for one‑shot startup (API + frontend + Postgres).

## Quick start (Docker)
1) Copy env and adjust as needed:
   ```bash
   cp .env.template .env
   ```
   Set `OPENAI_API_KEY` if you want real LLM SQL generation.
2) If host port 5432 is taken, change the Postgres port mapping in `docker-compose.yml` or stop the host Postgres.
3) Build/run:
   ```bash
   docker compose up --build
   ```
4) Seed sample tables in the container DB (optional demo):
   ```bash
   docker compose exec db psql -U postgres -d postgres -c "
   CREATE TABLE IF NOT EXISTS artists (id SERIAL PRIMARY KEY, name TEXT);
   CREATE TABLE IF NOT EXISTS albums (id SERIAL PRIMARY KEY, artist_id INT REFERENCES artists(id), title TEXT);
   INSERT INTO artists (name) VALUES ('Artist A'), ('Artist B') ON CONFLICT DO NOTHING;
   INSERT INTO albums (artist_id, title) VALUES (1,'Album One'),(1,'Album Two'),(2,'Album Three') ON CONFLICT DO NOTHING;
   "
   ```
5) Open the UI at http://localhost:8501. Use:
   - DB type: `postgresql`
   - Host: `db`
   - Port: `5432`
   - Username/Password: from `.env` (defaults `postgres`/`postgres`)
   - Database: `postgres`
   - Question example: “List all album titles and their artist names.”

## Local (without Docker)
1) Create a venv and install deps (uv preferred):
   ```bash
   uv sync
   # or: pip install -e .
   ```
2) Copy env: `cp .env.template .env` and set `DATABASE_URL` and optionally `OPENAI_API_KEY`.
3) Run backend:
   ```bash
   uvicorn agentic_sql.main:app --reload --app-dir src
   ```
4) Run frontend:
   ```bash
   streamlit run frontend/app.py
   ```
5) Open http://localhost:8501 and fill the form with your DB credentials/host. Use “Test connection” before running queries.

## Environment
- `.env.template` documents required vars: `DATABASE_URL`, `API_BASE_URL`, `OPENAI_API_KEY`, and Postgres container creds. Copy to `.env` and fill real values.

## Testing
```bash
pytest
```

## Project structure
- `src/agentic_sql`: FastAPI app and agents (schema, SQL, validation, execution, visualization).
- `frontend/`: Streamlit UI.
- `docker-compose.yml`: API + frontend + Postgres.
- `.env.template`: sample configuration.

