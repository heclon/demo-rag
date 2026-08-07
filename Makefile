# Common tasks. `make up` is the only one you need to see the demo.
.DEFAULT_GOAL := help
.PHONY: help up down logs reset dev-api dev-web install ingest test lint format check

API := services/api
VENV := $(API)/.venv
PY := $(VENV)/bin/python

help: ## Show this help
	@grep -hE '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

## ---------- Docker: the download-and-run path ----------

up: ## Build and run everything (Postgres, OpenSearch, ingest, API, web)
	docker compose up --build

down: ## Stop all containers
	docker compose down

reset: ## Stop everything and delete the database volume
	docker compose down -v

logs: ## Tail the API logs (shows agent routing decisions)
	docker compose logs -f api

## ---------- Local development: hot reload ----------

install: ## Create the Python venv and install JS + Python dependencies
	python3 -m venv $(VENV)
	$(VENV)/bin/pip install --quiet --upgrade pip
	$(VENV)/bin/pip install --quiet -r $(API)/requirements-dev.txt
	npm --prefix apps/frontend install --no-audit --no-fund

dev-api: ## Run the API with auto-reload (needs: docker compose up postgres opensearch)
	cd $(API) && .venv/bin/uvicorn app.main:app --reload --port 8000

dev-web: ## Run the Next.js dev server on :3000
	npm --prefix apps/frontend run dev

ingest: ## Load products, build embeddings, index reviews
	cd $(API) && .venv/bin/python scripts/ingest.py

## ---------- Quality ----------

test: ## Run the backend test suite
	cd $(API) && .venv/bin/python -m pytest -q

lint: ## Lint Python and typecheck TypeScript
	cd $(API) && .venv/bin/ruff check app tests scripts
	cd $(API) && .venv/bin/black --check app tests scripts
	npm --prefix apps/frontend run typecheck

format: ## Auto-format Python
	cd $(API) && .venv/bin/black app tests scripts
	cd $(API) && .venv/bin/ruff check --fix app tests scripts

check: lint test ## Everything CI would run
