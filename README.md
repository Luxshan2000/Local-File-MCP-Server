# 🚀 FastMCP File Server

A secure **Model Context Protocol (MCP)** server built with **FastMCP** that provides safe file operations for AI agents within a sandboxed environment.

> **⚡ Quick Start**: Run `make setup` to install everything, then `make test` to verify it works!

## 📋 Features

- **🔒 Secure & Sandboxed** - All file operations restricted to `allowed/` directory  
- **⚡ FastMCP Powered** - Built with FastMCP supporting both stdio and HTTP transports
- **📝 Complete CRUD** - Create, read, write, delete, and list files
- **🛡️ Path Protection** - Prevents directory traversal attacks
- **🎯 MCP 2024-11-05** - Follows latest MCP protocol standards
- **🧪 Comprehensive Tests** - Full test suite included

## 🛠️ Quick Setup

### Prerequisites
- Python 3.7+ installed
- Terminal/Command Prompt access

### Installation

```bash
# Clone/download this project
cd local_file_mcp_server

# Install and setup everything
make setup

# Run tests to verify
make test

# Try the demo
make demo
```

That's it! Your server is ready to use.

## 🎮 Usage

### Start the Server

**For Claude Desktop (stdio transport):**
```bash
make run
```

**For HTTP access (port 8082):**
```bash
make run-http
```

**For HTTP with multi-tier Bearer token authentication:**
```bash
# Configure access keys with different permission levels
export MCP_READ_KEY="readonly-token-123"
export MCP_WRITE_KEY="readwrite-token-456" 
export MCP_ADMIN_KEY="admin-token-789"

./venv/bin/python src/fastmcp_server.py --http --port 8082
```

### Run Tests
```bash
make test
```

### Interactive Demo
```bash
make demo
```

### Test HTTP Server
```bash
# In terminal 1:
make run-http

# In terminal 2:  
make test-http
```

### View Status
```bash
make status
```

## 🔌 Integration Options

### Claude Desktop Integration

**Location:**
- **macOS**: `~/Library/Application Support/Claude/config.json`
- **Windows**: `%APPDATA%\Claude\config.json`

**Configuration:**
```json
{
  "mcpServers": {
    "local-file-server": {
      "command": "/absolute/path/to/local_file_mcp_server/venv/bin/python",
      "args": [
        "/absolute/path/to/local_file_mcp_server/src/fastmcp_server.py"
      ],
      "env": {
        "MCP_ALLOWED_PATH": "/absolute/path/to/local_file_mcp_server/allowed"
      }
    }
  }
}
```

Replace `/absolute/path/to/local_file_mcp_server` with your actual project path.

### HTTP API Access (Alternative)

For direct HTTP access without Claude Desktop, start the HTTP server:

**Option 1: Standard HTTP server (no authentication)**
```bash
make run-http
```

**Option 2: HTTP server with multi-tier Bearer token authentication**
```bash
# Configure access keys with different permission levels
export MCP_READ_KEY="readonly-token-123"      # Read-only access
export MCP_WRITE_KEY="readwrite-token-456"    # Read, write, edit access  
export MCP_ADMIN_KEY="admin-token-789"        # Full access including delete

# Start HTTP server with multi-tier authentication
./venv/bin/python src/fastmcp_server.py --http --port 8082
```

Then access the server at: `http://localhost:8082/mcp` (FastMCP streamable HTTP/SSE)

**Multi-Tier Authentication:**
- Supports three access levels with different scopes:
  - **Read-only**: `MCP_READ_KEY` - View files only (`read:files`)
  - **Read/Write**: `MCP_WRITE_KEY` - Read, write, edit files (`read:files`, `write:files`, `edit:files`)
  - **Admin**: `MCP_ADMIN_KEY` - Full access including delete (`read:files`, `write:files`, `edit:files`, `delete:files`)
- All HTTP requests must include: `Authorization: Bearer <your-token>`
- Returns 401 for missing/invalid headers, 403 for insufficient permissions

## 📁 Available Tools

The server provides these file operations:

| Tool | Description | Example |
|------|-------------|---------|
| **`create_file`** | Create new file with content | `create_file("notes.txt", "Hello!")` |
| **`read_file`** | Read file contents | `read_file("notes.txt")` |
| **`write_file`** | Update existing file | `write_file("notes.txt", "Updated!")` |
| **`delete_file`** | Remove file | `delete_file("notes.txt")` |
| **`list_files`** | List directory contents | `list_files(".")` |

All operations are sandboxed to the `allowed/` directory for security.

## 🔒 Security Features

- **Sandboxed Directory**: All operations restricted to `allowed/` only
- **Path Traversal Protection**: Prevents `../` attacks
- **File Extension Validation**: Configurable allowed extensions  
- **Size Limits**: Configurable file size limits
- **No Code Execution**: Pure file operations only
- **Custom Bearer Token Authentication**: Optional middleware for HTTP requests

### Multi-Tier Authentication System

The server supports role-based access control with three permission levels:

**Access Levels:**
- **🔍 Read-Only** (`MCP_READ_KEY`): Can only view and list files
- **✏️ Read/Write** (`MCP_WRITE_KEY`): Can read, create, and modify files  
- **🔧 Admin** (`MCP_ADMIN_KEY`): Full access including file deletion

**Usage Examples:**
```bash
# Read-only access
curl -H "Authorization: Bearer readonly-token-123" \
     -H "Content-Type: application/json" \
     -d '{"jsonrpc":"2.0","method":"tools/call","id":1,"params":{"name":"read_file","arguments":{"path":"test.txt"}}}' \
     http://localhost:8082/mcp

# Admin access (all operations)
curl -H "Authorization: Bearer admin-token-789" \
     -H "Content-Type: application/json" \
     -d '{"jsonrpc":"2.0","method":"tools/call","id":1,"params":{"name":"delete_file","arguments":{"path":"temp.txt"}}}' \
     http://localhost:8082/mcp
```

## ⚙️ Configuration

Set environment variables to customize:

```bash
export MCP_ALLOWED_PATH="./allowed"           # Base directory
export MCP_MAX_FILE_SIZE="10485760"           # 10MB limit  
export MCP_ALLOWED_EXTENSIONS=".txt,.json,.md"  # Allowed file types

# Multi-tier authentication keys
export MCP_READ_KEY="readonly-token-123"      # Read-only access
export MCP_WRITE_KEY="readwrite-token-456"    # Read/write/edit access
export MCP_ADMIN_KEY="admin-token-789"        # Full access including delete
```

## 📊 Project Structure

```
local_file_mcp_server/
├── 📄 README.md                    # This documentation
├── 🔧 Makefile                     # Development commands
├── 🔧 requirements.txt             # Dependencies (for dev tools)
├── 🔧 claude-config.json           # Ready-to-use Claude Desktop config
│
├── 📁 src/
│   ├── fastmcp_server.py           # Main FastMCP server (dual transport)
│   └── auth_wrapper.py             # Custom Bearer token authentication middleware
│
├── 📁 tests/
│   └── test_fastmcp_server.py      # Comprehensive test suite
│
├── 📁 scripts/
│   ├── test_client.py              # Interactive demo client (stdio)
│   └── test_http_client.py         # HTTP connectivity test
│
├── 📁 allowed/                     # 🔒 Sandboxed directory
│   └── .gitkeep
│
└── 📁 venv/                        # Virtual environment (created by setup)
```

## 🧪 Testing

Run the comprehensive test suite:

```bash
make test
```

The tests verify:
- ✅ Server initialization
- ✅ Tool listing
- ✅ File operations (CRUD)
- ✅ Error handling
- ✅ Security (path traversal protection)

## 🚀 Available Commands

| Command | Description |
|---------|-------------|
| `make help` | Show all available commands |
| `make setup` | Install FastMCP and setup directories |
| `make test` | Run comprehensive test suite (stdio) |
| `make test-http` | Test HTTP server connectivity |
| `make run` | Start server (stdio for Claude Desktop) |
| `make run-http` | Start server (HTTP on port 8082) |
| `make demo` | Run interactive demo client (stdio) |
| `make clean` | Clean up temporary files |
| `make status` | Show project status |
| `make all` | Run setup + test + demo |

## 🤝 Integration Examples

### Basic Usage (Python)
```python
# The server exposes these tools via MCP:
# - create_file(file_path, content)
# - read_file(file_path)  
# - write_file(file_path, content)
# - delete_file(file_path)
# - list_files(directory_path=".")
```

### With Claude Desktop
Once configured, ask Claude:
- "Create a file called notes.txt with my ideas"
- "Read the contents of config.json"
- "List all files in the directory"
- "Delete the old backup file"

## ❓ Troubleshooting

### Server won't start
```bash
make status  # Check what's missing
make setup   # Re-run setup
```

### Tests failing
```bash
make clean   # Clean up
make setup   # Fresh install
make test    # Try again
```

### Claude Desktop issues
1. Check that paths in `claude-config.json` are **absolute**
2. Restart Claude Desktop after config changes
3. Check Claude Desktop logs for errors

## 📚 Documentation

- **FastMCP**: [https://gofastmcp.com](https://gofastmcp.com)
- **MCP Protocol**: [https://modelcontextprotocol.io](https://modelcontextprotocol.io)
- **Claude Desktop**: [https://claude.ai/download](https://claude.ai/download)

## 🎉 Ready to Use!

Your FastMCP File Server is now ready to provide secure file operations to AI agents through the Model Context Protocol. Enjoy building with it! 🚀