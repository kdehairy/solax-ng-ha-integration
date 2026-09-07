.PHONY: init
init:
	uv sync

.PHONY: verify
verify: init
	uv run black --check .
	uv run isort --check-only --profile black .
	uv run mypy .
	uv run flake8 --ignore=E501,E704 custom_components tests
	uv run pylint -d 'C0111' custom_components tests
	uv run pytest --cov=custom_components.solax --cov-fail-under=100 --cov-branch --cov-report=term-missing .

.PHONY: test
test:
	uv run pytest --cov=custom_components.solax --cov-fail-under=100 --cov-branch --cov-report=term-missing .

.PHONY: clean
clean: clean-pyc

.PHONY: clean-pyc
clean-pyc:
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '*.pyo' -exec rm -f {} +
	find . -name '*~' -exec rm -f {} +
	find . -name '__pycache__' -exec rm -rf {} +

.PHONY: clean-test
clean-test:
	rm -rf .pytest_cache .mypy_cache .coverage