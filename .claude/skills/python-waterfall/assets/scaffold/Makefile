# Task runner for the project. Every target runs through uv, so the locked
# environment is always the one being tested. `make check` is the per-module gate.
.DEFAULT_GOAL := help
.PHONY: help sync fmt lint typecheck test test-unit coverage rtm audit check build clean

help: ## List targets
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  %-10s %s\n", $$1, $$2}'

sync: ## Install the locked environment (incl. dev group)
	uv sync --locked

fmt: ## Format and auto-fix
	uv run ruff format .
	uv run ruff check --fix .

lint: ## Format check + lint
	uv run ruff format --check .
	uv run ruff check .

typecheck: ## mypy --strict
	uv run mypy

test: ## All tests
	uv run pytest

test-unit: ## Fast tests only (no integration / e2e); none collected yet is OK
	uv run pytest -m "not integration and not e2e" || [ $$? -eq 5 ]

coverage: ## All tests with branch coverage (fails under the target)
	uv run pytest --cov --cov-report=term-missing --cov-report=xml

rtm: ## Requirement -> test outcomes (also writes rtm.json)
	uv run pytest --rtm --rtm-json=rtm.json -q

audit: ## Known-vulnerability scan of the locked dependencies (OSV)
	uv audit --locked --preview-features audit-command

check: lint typecheck test-unit ## The per-module gate: lint + types + fast tests

build: ## Build sdist + wheel into dist/
	uv build

clean: ## Remove caches and build output
	rm -rf dist build .coverage coverage.xml rtm.json .pytest_cache .mypy_cache .ruff_cache
