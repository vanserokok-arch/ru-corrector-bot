.PHONY: help install dev-install test lint format run docker-build docker-up docker-down clean

help:
	@echo "Available commands:"
	@echo "  make install      - Install production dependencies"
	@echo "  make dev-install  - Install development dependencies"
	@echo "  make test         - Run tests"
	@echo "  make lint         - Run code linters"
	@echo "  make format       - Format code with black"
	@echo "  make run          - Run the API server locally"
	@echo "  make docker-build - Build Docker image"
	@echo "  make docker-up    - Start services with docker-compose"
	@echo "  make docker-down  - Stop services"
	@echo "  make clean        - Clean up temporary files"

install:
	pip install -r requirements.txt

dev-install: install
	pip install pytest pytest-asyncio httpx ruff black mypy

test:
	pytest -v

lint:
	ruff check src/ tests/
	black --check src/ tests/

format:
	black src/ tests/

run:
	cd src && python -m ru_corrector.app

docker-build:
	docker-compose build

docker-up:
	docker-compose up -d

docker-down:
	docker-compose down

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	rm -f diff.html
