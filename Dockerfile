FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml uv.lock ./
COPY src ./src
COPY frontend ./frontend
COPY README.md .

# Install uv to leverage the lockfile, then install deps into system site-packages
RUN pip install --no-cache-dir uv \
    && uv pip install --system --no-cache .

# Copy any remaining files (tests, config)
COPY . .

# --------------------
# API service
# --------------------
FROM base AS api
EXPOSE 8000
CMD ["uvicorn", "agentic_sql.main:app", "--host", "0.0.0.0", "--port", "8000"]

# --------------------
# Frontend service
# --------------------
FROM base AS frontend
EXPOSE 8501
CMD ["streamlit", "run", "frontend/app.py", "--server.port=8501", "--server.address=0.0.0.0"]
