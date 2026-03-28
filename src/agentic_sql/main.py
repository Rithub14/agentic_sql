import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from starlette.middleware.base import BaseHTTPMiddleware

from agentic_sql.api.routes import router as query_router
from agentic_sql.limiter import limiter
from agentic_sql.logger import configure_logging, get_logger

configure_logging()
logger = get_logger(__name__)


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Attaches a unique request_id to every request and echoes it in the response."""

    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Agentic SQL API starting up")
    yield
    logger.info("Agentic SQL API shutting down")


app = FastAPI(
    title="Agentic SQL Explorer",
    version="1.0.0",
    description=(
        "Natural-language-to-SQL multi-agent system. "
        "Converts plain-English questions into safe, validated SQL queries "
        "and returns results with visualization suggestions."
    ),
    lifespan=lifespan,
)

# Middleware — order matters: RequestID runs outermost
app.add_middleware(RequestIDMiddleware)

# Rate-limit error handler
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.include_router(query_router, prefix="/api")


@app.get("/health", tags=["ops"])
def health_check():
    return {"status": "ok"}
