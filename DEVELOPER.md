# Developer Guide

This guide covers development setup, testing, and contribution guidelines for FastMCP File Server.

## 🛠️ Development Setup

### Prerequisites

- Python 3.10 or higher
- [uv](https://docs.astral.sh/uv/) package manager (recommended)
- Git

### Initial Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/Luxshan2000/Local-File-MCP-Server.git
   cd Local-File-MCP-Server
   ```

2. **Install dependencies:**
   ```bash
   # Using uv (recommended)
   uv sync
   
   # Or using pip
   pip install -e ".[dev]"
   ```

3. **Create development environment:**
   ```bash
   # Copy example environment file
   cp .env.example .env
   
   # Edit .env with your development settings
   export MCP_ALLOWED_PATH="$(pwd)/allowed"
   mkdir -p allowed
   ```

## 🚀 Development Commands

### Available Scripts

| Command | Description |
|---------|-------------|
| `uv run server` | Start stdio server for development |
| `uv run server-http` | Start HTTP server for development |
| `uv run test` | Run the test suite |
| `uv run format` | Format code with black |
| `uv run lint` | Check code with ruff |
| `uv run lint-fix` | Auto-fix linting issues |

### Running Development Servers

```bash
# Stdio mode (for Claude Desktop testing)
uv run server

# HTTP mode (for web integration testing)
export MCP_ADMIN_KEY="dev-token-123"
uv run server-http

# HTTP mode with custom port
export MCP_HTTP_PORT=9000
uv run server-http
```

## 🧪 Testing

### Running Tests

```bash
# Run all tests
uv run test

# Run with verbose output
uv run pytest -v

# Run specific test file
uv run pytest tests/test_fastmcp_server.py

# Run with coverage
uv run pytest --cov=src/fastmcp_file_server
```

### Test Environment

Tests use a temporary directory structure created in `/tmp/fastmcp_test_*`. Each test gets a fresh, isolated environment.

### Writing Tests

Place new tests in the `tests/` directory. Follow the existing patterns:

```python
import pytest
from fastmcp_file_server.server import FastMCPFileServer

@pytest.fixture
def test_server():
    """Create a test server instance."""
    return FastMCPFileServer()

def test_your_feature(test_server):
    """Test your new feature."""
    # Your test code here
    pass
```

## 📁 Project Structure

```
local_file_mcp_server/
├── src/
│   └── fastmcp_file_server/
│       ├── __init__.py          # Package initialization
│       ├── cli.py               # Command-line interface
│       └── server.py            # Main server implementation
├── tests/
│   ├── __init__.py
│   └── test_fastmcp_server.py   # Test suite
├── allowed/                     # Default safe directory
├── pyproject.toml              # Package configuration
├── README.md                   # User documentation
├── DEVELOPER.md               # This file
├── LICENSE                    # Apache 2.0 license
├── .env.example              # Environment template
└── uv.lock                   # Dependency lock file
```

## 🔧 Code Style

### Formatting and Linting

We use black for code formatting and ruff for linting:

```bash
# Format code
uv run format

# Check linting
uv run lint

# Auto-fix linting issues
uv run lint-fix
```

### Code Standards

- **Line length**: 88 characters (black default)
- **Target Python**: 3.10+
- **Type hints**: Use type hints for all public functions
- **Docstrings**: Use Google-style docstrings for public APIs
- **Error handling**: Always handle exceptions gracefully

### Example Code Style

```python
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

def process_file(
    file_path: str, 
    options: Optional[Dict[str, str]] = None
) -> List[str]:
    """Process a file with optional configuration.
    
    Args:
        file_path: Path to the file to process
        options: Optional processing configuration
        
    Returns:
        List of processed lines
        
    Raises:
        FileNotFoundError: If file doesn't exist
        PermissionError: If file is not accessible
    """
    if options is None:
        options = {}
        
    try:
        # Implementation here
        pass
    except Exception as e:
        logger.error(f"Failed to process {file_path}: {e}")
        raise
```

## 🚀 Building and Releasing

### Building the Package

```bash
# Build wheel and source distribution
uv build

# Check built files
ls dist/
```

### Version Management

Update version in `pyproject.toml`:

```toml
[project]
name = "fastmcp-file-server"
version = "1.1.0"  # Update this
```

### Release Checklist

1. **Pre-release checks:**
   ```bash
   uv run test        # All tests pass
   uv run lint        # No linting errors
   uv run format      # Code is formatted
   ```

2. **Update documentation:**
   - Update CHANGELOG.md with new features
   - Update version in pyproject.toml
   - Update README.md if needed

3. **Build and test:**
   ```bash
   uv build
   uv run server --version  # Test installation
   ```

4. **Create release:**
   ```bash
   git tag v1.1.0
   git push origin v1.1.0
   ```

## 🤝 Contributing

### Contribution Workflow

1. **Fork and clone** the repository
2. **Create a feature branch:** `git checkout -b feature/amazing-feature`
3. **Make your changes** following the code style guidelines
4. **Add tests** for new functionality
5. **Run the test suite:** `uv run test`
6. **Format and lint:** `uv run format && uv run lint`
7. **Commit changes:** `git commit -m "feat: add amazing feature"`
8. **Push to branch:** `git push origin feature/amazing-feature`
9. **Open a Pull Request**

### Commit Message Format

Use conventional commits:

```
feat: add new file conversion feature
fix: resolve authentication bug in HTTP mode
docs: update API documentation
test: add tests for archive operations
refactor: simplify error handling logic
```

### Types of Contributions

- **Bug fixes**: Fix existing functionality
- **Features**: Add new capabilities
- **Documentation**: Improve docs, examples, or guides
- **Tests**: Expand test coverage
- **Performance**: Optimize existing code
- **Security**: Address security concerns

## 🐛 Debugging

### Debug Mode

Enable debug logging:

```bash
export MCP_LOG_LEVEL=DEBUG
uv run server
```

### Common Debug Scenarios

**Server startup issues:**
```bash
# Check dependencies
uv sync

# Verify Python version
python --version

# Check environment variables
env | grep MCP_
```

**Authentication problems:**
```bash
# Test HTTP endpoint manually
curl -H "Authorization: Bearer your-token" http://localhost:8082/mcp
```

**File permission issues:**
```bash
# Check directory permissions
ls -la allowed/

# Verify path accessibility
cd "$MCP_ALLOWED_PATH" && pwd
```

## 📚 Additional Resources

- [Model Context Protocol Specification](https://modelcontextprotocol.io/)
- [FastMCP Framework Documentation](https://github.com/jlowin/fastmcp)
- [Claude Desktop MCP Integration](https://docs.anthropic.com/claude/docs/mcp)

## 💬 Getting Help

- **Issues**: Report bugs or request features on [GitHub Issues](https://github.com/Luxshan2000/Local-File-MCP-Server/issues)
- **Discussions**: Ask questions in [GitHub Discussions](https://github.com/Luxshan2000/Local-File-MCP-Server/discussions)
- **Security**: Report security issues privately to the maintainers

## 📝 Development Notes

### Architecture Overview

The server is built on the FastMCP framework and consists of:

- **CLI Interface** (`cli.py`): Command-line entry points for both stdio and HTTP modes
- **Server Core** (`server.py`): Main server implementation with all file operation tools
- **Security Layer**: Path validation, authentication, and access control

### Key Design Principles

1. **Security First**: All operations are sandboxed to allowed directories
2. **Flexibility**: Support multiple deployment modes (stdio, HTTP, public)
3. **Simplicity**: Easy to install, configure, and use
4. **Extensibility**: Clean architecture for adding new file operations

### Adding New Features

To add a new file operation tool:

1. Add the tool method to `FastMCPFileServer` class in `server.py`
2. Use the `@tool` decorator with proper description
3. Add appropriate error handling and logging
4. Write comprehensive tests
5. Update documentation