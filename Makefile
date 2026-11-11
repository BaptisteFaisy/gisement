# Gisement - developer commands. CI runs the same targets (5 min budget).

PYTHON ?= python3
PYTEST ?= $(PYTHON) -m pytest
RUFF   ?= $(PYTHON) -m ruff
SRC    := src tests eval infra scripts

.PHONY: help install lint format test smoke demo eval assets limits all clean

help:
	@echo "make install  - dev dependencies"
	@echo "make lint     - ruff check + format --check"
	@echo "make format   - ruff format (writes)"
	@echo "make limits   - < 500 lines per file, < 50 per function"
	@echo "make test     - offline unit + integration tests"
	@echo "make smoke    - run the whole pipeline on the frozen demo corpus"
	@echo "make demo     - regenerate the synthetic dataset, then smoke"
	@echo "make eval     - evaluation harness (classification, k>=5, economics)"
	@echo "make all      - lint + limits + test (what CI runs)"

install:
	$(PYTHON) -m pip install --user -e ".[dev,api]"

lint:
	$(RUFF) check $(SRC)
	$(RUFF) format --check $(SRC)

format:
	$(RUFF) format $(SRC)
	$(RUFF) check --fix $(SRC)

limits:
	$(PYTHON) scripts/check_limits.py

test:
	PYTHONPATH=src $(PYTEST) -m "not slow"

smoke:
	PYTHONPATH=src $(PYTHON) -m gisement.cli smoke

demo:
	PYTHONPATH=src $(PYTHON) -m gisement.cli demo

eval:
	PYTHONPATH=src $(PYTHON) -m gisement.cli eval

assets:
	PYTHONPATH=src $(PYTHON) -m gisement.cli assets --out infra/quick

all: lint limits test

clean:
	rm -rf .pytest_cache .ruff_cache build dist *.egg-info demo/donnees/genere
