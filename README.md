# FastMCP File Server

A versatile secure file server that provides AI assistants with safe file operations. Supports multiple connection modes and access levels for various deployment scenarios.

## What it does

This server provides AI assistants with secure file operations:
- Create and edit text files
- Read file contents  
- Delete files
- List directory contents

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
make setup
```

2. Start the server:
```bash
make run
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

### Option 2: HTTP Mode

First start the HTTP server:
```bash
export MCP_ADMIN_KEY="your-secret-token"
make run-http
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
make run-http

# In another terminal, expose via ngrok
ngrok http 8082
```

Then use the ngrok URL (e.g., `https://abc123.ngrok.io/mcp`) in your web-based AI system with:
```
Authorization: Bearer your-secret-token
```

This allows any web-based AI system to securely access your local files through the public URL.

## Using with Claude

Once configured, you can ask Claude to:
- "Create a file called notes.txt with my meeting notes"
- "Read the contents of my todo list"
- "List all files in the directory"
- "Delete the old backup file"

## Security

- All file operations are restricted to the `allowed/` directory
- Cannot access files outside the protected area
- File types and sizes can be limited through configuration

## Optional Configuration

You can customize the server by setting environment variables before starting:

```bash
export MCP_ALLOWED_PATH="./my-files"          # Change the safe directory
export MCP_ADMIN_KEY="your-secret-token"     # Enable HTTP authentication
```

## Troubleshooting

**Server won't start:**
```bash
make setup   # Reinstall dependencies
```

**Claude Desktop not connecting:**
1. Check that all paths in the configuration are absolute (full paths)
2. Restart Claude Desktop after changing configuration
3. Verify the server starts without errors using `make run`