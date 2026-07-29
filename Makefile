.PHONY: install install-api test cov lint format run api

install:
	pip install -e ".[dev]"

install-api:
	pip install -e ".[dev,api]"

api:
	uvicorn api.app:app --reload

test:
	pytest

cov:
	pytest --cov=src --cov-report=term-missing

lint:
	ruff check . --fix