export

PYTEST_ARGS?=-v

.PHONY: clean setup-poetry install lint fix build docs tests

clean:
	rm -rf dist/

setup-poetry:
	pip install poetry

install:
	poetry install --with dev

lint:
	poetry run ruff check
	poetry run ruff format --diff

fix:
	poetry run ruff check --fix
	poetry run ruff format

build:
	poetry build -f wheel && poetry build -f sdist

docs:
	cd docs && pip install -r requirements.txt && make clean html

tests:
	poetry run pytest tests $(PYTEST_ARGS)
