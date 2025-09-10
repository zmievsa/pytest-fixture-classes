SHELL := /bin/bash

help:
	@echo "Available Commands:"
	@echo ""
	@echo "format: apply all available formatters"
	@echo ""
	@echo "test: run all tests"
	@echo ""


py_warn = PYTHONDEVMODE=1


# 'shopt -s globstar' allows us to run **/*.py globs. By default bash can't do recursive globs 
format:
	shopt -s globstar; \
	uv run -q pyupgrade **/*.py --py37-plus --exit-zero-even-if-changed; \
	uv run -q autoflake . --in-place --recursive --remove-all-unused-imports --ignore-init-module-imports --verbose; \
	uv run -q isort .; \
	uv run -q black .;

test:
	uv run -q pytest -v --cov=pytest_fixture_classes --cov-report=term-missing:skip-covered --cov-report=xml tests;
