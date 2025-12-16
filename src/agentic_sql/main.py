# src/agentic_sql/main.py

from fastapi import FastAPI

from agentic_sql.api.routes import router as query_router

app = FastAPI(
    title="Agentic SQL System",
    version="0.1.0",
)

app.include_router(query_router, prefix="/api")


@app.get("/health")
def health_check():
    return {"status": "ok"}
