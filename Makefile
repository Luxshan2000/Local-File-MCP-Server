# FastMCP File Server - Development Tools

.PHONY: help install setup test run demo clean status all

# Default target
help:
	@echo "FastMCP File Server - Available Commands:"
	@echo "  help        - Show this help message"
	@echo "  install     - Install FastMCP and dependencies"
	@echo "  setup       - Complete setup (install + create directories)"
	@echo "  test        - Run comprehensive test suite"
	@echo "  run         - Start the FastMCP server"
	@echo "  demo        - Run interactive demo client"
	@echo "  clean       - Clean up temporary files"
	@echo "  status      - Show project status"
	@echo "  all         - Run setup + test + demo"

# Install FastMCP
install:
	@echo "🔧 Setting up FastMCP File Server..."
	@if [ ! -d "venv" ]; then \
		echo "Creating virtual environment..."; \
		python3 -m venv venv; \
	fi
	@echo "Installing FastMCP..."
	./venv/bin/pip install --upgrade pip
	./venv/bin/pip install fastmcp
	@echo "✅ FastMCP installed successfully!"

# Complete setup
setup: install
	@echo "🚀 Setting up directories..."
	@mkdir -p allowed
	@touch allowed/.gitkeep
	@echo "✅ Setup complete! Ready to use."

# Run comprehensive tests
test:
	@echo "🧪 Running FastMCP test suite..."
	@if [ -d "venv" ]; then \
		./venv/bin/python tests/test_fastmcp_server.py; \
	else \
		echo "❌ Virtual environment not found. Run 'make install' first."; \
	fi

# Start the FastMCP server
run:
	@echo "🚀 Starting FastMCP File Server..."
	@if [ -d "venv" ]; then \
		./venv/bin/python src/fastmcp_server.py; \
	else \
		echo "❌ Virtual environment not found. Run 'make install' first."; \
	fi

# Run demo client
demo:
	@echo "🎮 Running demo client..."
	@if [ -d "venv" ]; then \
		cd scripts && ../venv/bin/python test_client.py; \
	else \
		echo "❌ Virtual environment not found. Run 'make install' first."; \
	fi

# Clean temporary files
clean:
	@echo "🧹 Cleaning up..."
	rm -rf __pycache__ src/__pycache__ tests/__pycache__ scripts/__pycache__
	rm -rf .pytest_cache *.pyc
	find allowed/ -name "*.txt" -o -name "*.json" -o -name "*.md" | grep -v ".gitkeep" | xargs rm -f 2>/dev/null || true
	@echo "✅ Cleanup complete!"

# Show project status
status:
	@echo "📊 FastMCP File Server Status:"
	@echo "Virtual Environment: $$([ -d venv ] && echo '✅ Exists' || echo '❌ Missing (run make install)')"
	@echo "FastMCP Installed: $$([ -f venv/bin/python ] && ./venv/bin/python -c 'import fastmcp; print("✅ Ready")' 2>/dev/null || echo '❌ Missing (run make install)')"
	@echo "Allowed Directory: $$([ -d allowed ] && echo '✅ allowed/' || echo '❌ Missing (run make setup)')"
	@echo "Server File: $$([ -f src/fastmcp_server.py ] && echo '✅ src/fastmcp_server.py' || echo '❌ Missing')"

# Run everything
all: setup test demo
	@echo "🎉 All tasks completed successfully!"