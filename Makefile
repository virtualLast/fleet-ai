PIP ?= .venv/bin/pip
RUFF ?= .venv/bin/ruff
MYPY ?= .venv/bin/mypy
PYTEST ?= .venv/bin/pytest

.PHONY: install lint format fix type-check test check

install:
	$(PIP) install -r requirements.txt

lint:
	$(RUFF) check .

format:
	$(RUFF) format .

fix:
	$(RUFF) check --fix .
	$(RUFF) format .

type-check:
	$(MYPY) .

test:
	$(PYTEST)

check: lint type-check test
