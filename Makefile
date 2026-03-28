VENV := .venv
PYTHON := $(VENV)/bin/python
UVICORN := $(VENV)/bin/uvicorn
STREAMLIT := $(VENV)/bin/streamlit
PYTEST := $(VENV)/bin/pytest
RUFF := $(VENV)/bin/ruff
BLACK := $(VENV)/bin/black

.PHONY: install api frontend test lint format docker-up docker-down help

## Install all dependencies into the virtual environment
install:
	uv sync
	uv pip install -e . --python $(PYTHON)
	uv pip install slowapi --python $(PYTHON)

## Run the FastAPI backend (reload watches src/ only — never .venv)
api:
	$(UVICORN) agentic_sql.main:app \
		--app-dir src \
		--reload \
		--reload-dir src \
		--host 127.0.0.1 \
		--port 8000

## Run the Streamlit frontend
frontend:
	$(STREAMLIT) run frontend/app.py \
		--server.port 8501 \
		--server.address 127.0.0.1

## Run the full test suite
test:
	$(PYTEST) tests/ -v

## Lint with ruff
lint:
	$(RUFF) check src/ tests/

## Format with black
format:
	$(BLACK) src/ tests/ frontend/

## Start the full Docker stack (API + frontend + Postgres)
docker-up:
	docker compose up --build

## Stop the Docker stack
docker-down:
	docker compose down

## Show available commands
help:
	@echo ""
	@echo "  make install     Install all dependencies"
	@echo "  make api         Run FastAPI backend (localhost:8000)"
	@echo "  make frontend    Run Streamlit frontend (localhost:8501)"
	@echo "  make test        Run test suite"
	@echo "  make lint        Lint with ruff"
	@echo "  make format      Format with black"
	@echo "  make docker-up   Start full Docker stack"
	@echo "  make docker-down Stop Docker stack"
	@echo ""
