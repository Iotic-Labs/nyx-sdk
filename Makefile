export

PYTEST_ARGS?=-v

.PHONY: clean setup-poetry install lint fix build docs generate-secrets

clean:
	rm -rf dist/ docs/

setup-poetry:
	pip install poetry

install:
	poetry install --with dev --extras "langchain-openai langchain-cohere"

lint:
	poetry run ruff check
	poetry run ruff format --diff

fix:
	poetry run ruff check --fix
	poetry run ruff format

build:
	poetry build -f wheel && poetry build -f sdist

docs:
	poetry run python -m pdoc -d google --no-include-undocumented --output-dir docs nyx_client

tests:
	poetry run pytest test $(PYTEST_ARGS)
