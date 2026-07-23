# Makefile
VENV_DIR := .venv
UV := uv
LINTER := ruff  # Replace this with the packages you need
LOGURU_LEVEL := INFO
export

all: lint test
.PHONY: all requirements-dev test lint build pypi run-crawl run-missing docker-build docker-up docker-down docker-logs

.venv:
	@echo "Initializing virtual environment..."
	$(UV) venv

requirements-dev: .venv
	@echo "Generating & installing dev requirements..."
	$(UV) run pip compile --extra dev pyproject.toml > requirements-dev.txt
	$(UV) run pip install -r requirements-dev.txt
	$(UV) run pip install -e .

test:
	$(UV) run pytest src/vietlott/tests

lint: .venv
	@echo "Linting..."
	$(UV) run ruff check --select I --fix ./src
	$(UV) run ruff format ./src

build: lint test
	@echo "Building..."
	$(UV) run python -m build

pypi: build
	@echo "Publishing..."
	$(UV) run python -m twine upload --repository testpypi dist/*

run-crawl: .venv
	@echo "Running crawl scripts..."
	LOGURU_LEVEL=$(LOGURU_LEVEL) PYTHONPATH=src $(UV) run python src/vietlott/cli/crawl.py keno
	LOGURU_LEVEL=$(LOGURU_LEVEL) PYTHONPATH=src $(UV) run python src/vietlott/cli/crawl.py power_535
	LOGURU_LEVEL=$(LOGURU_LEVEL) PYTHONPATH=src $(UV) run python src/vietlott/cli/crawl.py power_655

run-missing: .venv
	@echo "Running missing scripts..."
	LOGURU_LEVEL=$(LOGURU_LEVEL) PYTHONPATH=src $(UV) run python src/vietlott/cli/missing.py keno
	LOGURU_LEVEL=$(LOGURU_LEVEL) PYTHONPATH=src $(UV) run python src/vietlott/cli/missing.py power_535

docker-build:                              ## Build the Docker image
	docker build -t vietlott-strategy-builder .

docker-up:                                 ## Run the full stack via docker compose
	docker compose up --build

docker-down:                               ## Stop the stack
	docker compose down

docker-logs:                               ## Tail logs
	docker compose logs -f
