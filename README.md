# FastMCP File Server

A versatile secure file server that provides AI assistants with safe file operations. Supports multiple connection modes and access levels for various deployment scenarios.

## What it does

This server provides AI assistants with comprehensive file operations:
- Create, read, write, and delete files
- Copy, move, and rename files and directories
- Read specific line ranges and manipulate lines
- Search and replace text within files
- Get file information (size, date, permissions)
- Create and manage directories
- Recursive directory listings with pattern matching
- Batch operations for handling multiple files efficiently
- Advanced file search with name and content pattern matching
- File comparison and diff generation with multiple formats
- Archive operations (create and extract ZIP files)
- File integrity verification with multiple hash algorithms
- Non-destructive file appending

**Connection Modes:**
- **stdio** - Direct integration with Claude Desktop
- **HTTP** - Local or remote access via web API
- **Public** - Expose via ngrok for web-based AI systems

**Access Levels:**
- **Read-only** - View and list files only
- **Read/Write** - Create and modify files
- **Admin** - Full access including deletion

All operations are restricted to a safe directory to protect your system.

## Setup

1. Install dependencies:
```bash
uv sync
```

2. Start the server:
```bash
uv run server          # stdio mode
# or
uv run server-http     # HTTP mode
```

## Claude Desktop Integration

**Configuration file location:**
- **macOS**: `~/Library/Application Support/Claude/config.json`
- **Windows**: `%APPDATA%\Claude\config.json`

### Option 1: Direct (stdio mode)

```json
{
  "mcpServers": {
    "local-file-server": {
      "command": "uv",
      "args": [
        "run",
        "--directory",
        "/absolute/path/to/local_file_mcp_server",
        "src/fastmcp_server.py"
      ],
      "env": {
        "MCP_ALLOWED_PATH": "/absolute/path/to/local_file_mcp_server/allowed"
      }
    }
  }
}
```

### Option 2: HTTP Mode

First start the HTTP server:
```bash
export MCP_ADMIN_KEY="your-secret-token"
uv run server-http
```

**If your environment supports HTTP directly:**
```json
{
  "mcpServers": {
    "local-file-server-http": {
      "transport": "http",
      "url": "http://127.0.0.1:8082/mcp",
      "headers": {
        "Authorization": "Bearer your-secret-token"
      }
    }
  }
}
```

**If you need mcp-remote proxy (install with `npm install -g mcp-remote`):**
```json
{
  "mcpServers": {
    "local-file-server-proxy": {
      "command": "npx",
      "args": [
        "mcp-remote",
        "http://127.0.0.1:8082/mcp",
        "--header",
        "Authorization:${AUTH_HEADER}"
      ],
      "env": {
        "AUTH_HEADER": "Bearer your-secret-token"
      }
    }
  }
}
```

Replace paths and tokens with your actual values. Restart Claude Desktop after configuration.

### Option 3: Public Access (ngrok)

For web-based AI systems, expose the HTTP server publicly:

```bash
# Start HTTP server with authentication
export MCP_ADMIN_KEY="your-secret-token"
export MCP_HTTP_PORT=8082
uv run server-http

# In another terminal, expose via ngrok
ngrok http $MCP_HTTP_PORT
```

Then use the ngrok URL (e.g., `https://abc123.ngrok.io/mcp`) in your web-based AI system with:
```
Authorization: Bearer your-secret-token
```

This allows any web-based AI system to securely access your local files through the public URL.

## Using with Claude

Once configured, you can ask Claude to:
- "Create a file called notes.txt with my meeting notes"
- "Read lines 10-20 from config.py"
- "Search for 'TODO' in all my files"
- "Replace 'old_function' with 'new_function' in utils.py"
- "Insert this code at line 15 in main.py"
- "Delete lines 5-10 from test.txt"
- "Append this log entry to debug.log"
- "Copy config.json to backup/config_backup.json"
- "Read all .py files in the src/ directory at once"
- "Create these 5 files with their content in one operation"
- "Find all .js files containing 'console.log' in the project"
- "Delete all temporary .tmp files in the workspace"
- "Compare config.json with config_backup.json"
- "Show me the diff between old_version.py and new_version.py"
- "Create a backup.zip archive of all my source files"
- "Extract the data.zip file to the imports/ directory"
- "Calculate the SHA256 hash of important_file.pdf"
- "Append this log entry to server.log without overwriting"

## Security

- All file operations are restricted to the `allowed/` directory
- Cannot access files outside the protected area
- File types and sizes can be limited through configuration

## Optional Configuration

You can customize the server by setting environment variables before starting:

```bash
export MCP_ALLOWED_PATH="./my-files"          # Change the safe directory
export MCP_HTTP_PORT=8082                     # HTTP server port
export MCP_ADMIN_KEY="your-secret-token"     # Enable HTTP authentication
```

## Development

Available uv scripts for development:

```bash
uv run server          # Start server (stdio mode)
uv run server-http     # Start server (HTTP mode)
uv run test            # Run tests
uv run format          # Format code with black
uv run lint            # Check code with ruff
uv run lint-fix        # Fix linting issues
```

## Troubleshooting

**Server won't start:**
```bash
uv sync   # Reinstall dependencies
```

**Claude Desktop not connecting:**
1. Check that all paths in the configuration are absolute (full paths)
2. Restart Claude Desktop after changing configuration
3. Verify the server starts without errors using `uv run src/fastmcp_server.py`