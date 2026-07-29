.PHONY: install test cov lint format run

install:
	pip install -e ".[dev]"

test:
	pytest

cov:
	pytest --cov=src --cov-report=term-missing

lint:
	ruff check . --fix
	ruff format .

run:
	python -m compliance_copilot.cli examples/sample_data/sample_input.json
