# Makefile for MCP File Server

.PHONY: help install test run clean dev-setup lint format

# Default target
help:
	@echo "MCP File Server - Available Commands:"
	@echo "  help        - Show this help message"
	@echo "  install     - Install dependencies"
	@echo "  dev-setup   - Set up development environment"
	@echo "  generate-key - Generate secure API key"
	@echo "  test        - Run all tests"
	@echo "  test-cov    - Run tests with coverage"
	@echo "  run         - Start the server"
	@echo "  lint        - Run linting checks"
	@echo "  format      - Format code"
	@echo "  clean       - Clean up temporary files"

# Install dependencies (creates venv if needed)
install:
	@if [ ! -d "venv" ]; then \
		echo "Creating virtual environment..."; \
		python3 -m venv venv; \
	fi
	@echo "Installing dependencies in virtual environment..."
	./venv/bin/pip install -r requirements.txt

# Development setup
dev-setup: install generate-key
	@echo "✅ Development environment ready!"
	@echo "To activate venv: source venv/bin/activate"

# Generate secure API key
generate-key:
	python3 scripts/generate_key.py

# Run tests
test:
	@if [ -d "venv" ]; then \
		./venv/bin/python -m pytest tests/ -v; \
	else \
		echo "⚠️  Virtual environment not found. Run 'make install' first or use 'python3 -m pytest tests/ -v'"; \
		python3 -m pytest tests/ -v 2>/dev/null || echo "❌ pytest not installed globally. Run 'make install' first."; \
	fi

# Run tests with coverage
test-cov:
	@if [ -d "venv" ]; then \
		./venv/bin/python -m pytest tests/ -v --cov=src --cov-report=html --cov-report=term; \
	else \
		echo "⚠️  Virtual environment not found. Run 'make install' first."; \
	fi

# Start the server
run:
	python3 src/server.py

# Lint code
lint:
	@if [ -d "venv" ]; then \
		./venv/bin/flake8 src/ tests/ scripts/ || echo "⚠️  flake8 not installed in venv"; \
		./venv/bin/mypy src/ --ignore-missing-imports || echo "⚠️  mypy not installed in venv"; \
	else \
		echo "⚠️  Virtual environment not found. Run 'make install' first."; \
		echo "Or install globally: pip3 install flake8 mypy"; \
	fi

# Format code
format:
	@if [ -d "venv" ]; then \
		./venv/bin/black src/ tests/ scripts/ || echo "⚠️  black not installed in venv"; \
	else \
		echo "⚠️  Virtual environment not found. Run 'make install' first."; \
		echo "Or install globally: pip3 install black"; \
	fi

# Clean temporary files
clean:
	rm -rf __pycache__ .pytest_cache .coverage htmlcov venv
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true

# Run demo client
demo:
	@echo "Starting demo (make sure server is running first)..."
	@read -p "Enter API key: " api_key; \
	python3 scripts/test_client.py http://localhost:8082 "$$api_key"