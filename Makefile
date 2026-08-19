.DEFAULT_GOAL := help
PY ?= python3
PORT ?= 5001

.PHONY: help install test run batch build-data check-data lint docker-build docker-run clean

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

install: ## Install Python dependencies
	$(PY) -m pip install -r requirements.txt

test: ## Run the full test suite
	$(PY) -m pytest -q

run: ## Start the Flask dev server (PORT overridable)
	PORT=$(PORT) $(PY) server.py

batch: ## Run the batch compliance report pipeline (writes reports/)
	$(PY) main.py

build-data: ## Regenerate the canonical data/employees.json
	$(PY) scripts/build_employees.py

check-data: ## Fail if data/employees.json is stale (used in CI)
	$(PY) scripts/build_employees.py --check

lint: ## Byte-compile all Python as a quick syntax check
	$(PY) -m compileall -q src server.py main.py scripts

docker-build: ## Build the production container image
	docker build -t attendance-compliance .

docker-run: ## Run the production container (maps $(PORT))
	docker run --rm -p $(PORT):8000 --env-file .env attendance-compliance

clean: ## Remove caches and generated reports
	rm -rf reports .pytest_cache
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
