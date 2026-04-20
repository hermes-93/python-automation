.PHONY: install test lint check-types run-health run-log help

PYTHON := python3
PIP := pip3

help:
	@echo "Available targets:"
	@echo "  install      Install all dependencies"
	@echo "  test         Run test suite with coverage"
	@echo "  lint         Run flake8 linter"
	@echo "  check-types  Run mypy type checker"
	@echo "  run-health   Demo: check GitHub and Google health"
	@echo "  run-log      Demo: analyze sample log file"

install:
	$(PIP) install -r requirements-dev.txt

test:
	$(PYTHON) -m pytest tests/ -v --cov=scripts --cov-report=term-missing

lint:
	$(PYTHON) -m flake8 scripts/ tests/ --max-line-length=120 --extend-ignore=E203,W503

check-types:
	$(PYTHON) -m mypy scripts/ --ignore-missing-imports

run-health:
	$(PYTHON) scripts/health_checker.py https://github.com https://google.com https://httpstat.us/500

run-log:
	$(PYTHON) scripts/log_analyzer.py examples/sample.log
