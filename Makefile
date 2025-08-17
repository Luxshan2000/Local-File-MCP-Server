# FastMCP File Server - Development Tools

.PHONY: help setup test run run-http clean status format lint

# Default target
help:
	@echo "FastMCP File Server - Available Commands:"
	@echo "  help        - Show this help message"
	@echo "  setup       - Install dependencies and create directories"
	@echo "  test        - Run test suite"
	@echo "  run         - Start server (stdio mode)"
	@echo "  run-http    - Start server (HTTP mode)"
	@echo "  format      - Format code with black"
	@echo "  lint        - Check code with ruff"
	@echo "  lint-fix    - Fix linting issues"
	@echo "  clean       - Clean up temporary files"
	@echo "  status      - Show project status"

# Complete setup
setup:
	@echo "Setting up FastMCP File Server..."
	uv sync
	@mkdir -p allowed
	@echo "Setup complete! Ready to use."

# Run tests
test:
	@echo "Running test suite..."
	uv run -m pytest tests/

# Start server (stdio)
run:
	@echo "Starting FastMCP File Server (stdio)..."
	uv run src/fastmcp_server.py

# Start server (HTTP)
run-http:
	@echo "Starting FastMCP File Server (HTTP)..."
	uv run src/fastmcp_server.py --http

# Format code
format:
	@echo "Formatting code..."
	uv run black src/ tests/

# Lint code
lint:
	@echo "Checking code..."
	uv run ruff check src/ tests/

# Fix linting issues
lint-fix:
	@echo "Fixing linting issues..."
	uv run ruff check --fix src/ tests/

# Clean temporary files
clean:
	@echo "Cleaning up..."
	rm -rf __pycache__ src/__pycache__ tests/__pycache__
	rm -rf .pytest_cache *.pyc .uv_cache
	find allowed/ -name "*.txt" -o -name "*.json" -o -name "*.md" | grep -v ".gitkeep" | xargs rm -f 2>/dev/null || true
	@echo "Cleanup complete!"

# Show project status
status:
	@echo "FastMCP File Server Status:"
	@echo "Dependencies: $$(uv sync --dry-run >/dev/null 2>&1 && echo 'Ready' || echo 'Missing (run make setup)')"
	@echo "Allowed Directory: $$([ -d allowed ] && echo 'allowed/' || echo 'Missing (run make setup)')"
	@echo "Server File: $$([ -f src/fastmcp_server.py ] && echo 'src/fastmcp_server.py' || echo 'Missing')"