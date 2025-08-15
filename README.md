# 🚀 Local File MCP Server

A secure **Model Context Protocol (MCP)** server that provides safe file operations for AI agents within a sandboxed environment.

> **⚡ Quick Start**: Run `./setup.sh` for automated setup, then add the generated config to Claude Desktop!

## 📋 What You Get

- **🤖 Claude Integration** - Works seamlessly with Claude Desktop
- **🔒 Secure & Sandboxed** - All file operations restricted to `allowed/` directory  
- **⚡ Zero Dependencies** - Uses only Python standard library
- **🛡️ Production Ready** - API key authentication, logging, error handling
- **📝 Complete CRUD** - Create, read, write, delete, and list files
- **🔧 Easy Setup** - Automated installation script included

## 🎯 Overview

This MCP server enables AI agents (like Claude) to safely interact with files on your local machine. All operations are restricted to a designated `allowed/` directory, ensuring your system remains secure while providing powerful file manipulation capabilities.

## ✨ Key Features

- ✅ **MCP 2024-11-05 Protocol Compliant** - Works with all MCP-compatible agents
- 🔒 **API Key Authentication** - Secure access control with configurable keys
- 📁 **Sandboxed Operations** - All file access restricted to `allowed/` subdirectory
- 🛡️ **Path Traversal Protection** - Prevents access outside allowed directory
- 📝 **Complete File Operations** - Read, write, create, delete, and list files
- 🌐 **HTTP REST API** - Easy integration via standard HTTP requests
- ❤️ **Health Monitoring** - Built-in health check endpoint
- 🚫 **No Code Execution** - Pure file operations only, no script execution
- 🔧 **Zero Dependencies** - Simple version uses only Python standard library

## 🛠️ Quick Setup

### Prerequisites
- Python 3.7+ installed on your system  
- Terminal/Command Prompt access

### Installation

1. **Download this project** to your machine
   ```bash
   # Download and extract the ZIP file, then navigate to folder
   cd local_file_mcp_server
   ```

2. **Generate a secure API key** (recommended)
   ```bash
   python3 scripts/generate_key.py
   ```
   This creates a `.env` file with a secure 64-character API key.

3. **Start the server**
   ```bash
   python3 src/server.py
   ```
   
That's it! Your server is running and ready to use.

### Alternative Setup Methods

**🔧 Using Makefile (if you have `make` installed):**
```bash
make dev-setup  # Generate key and setup
make run        # Start server
```

**⚡ Quick Setup Script (Recommended for beginners):**
```bash
./setup.sh  # Automated setup with guided configuration
```

**🐳 Manual Configuration:**
Create your own `.env` file based on `.env.example` and customize settings.

**⚡ Command Line Override:**
```bash
python3 src/server.py --port 8084 --api-key your-custom-key
```

## ⚙️ Configuration Options

| Parameter | Default Value | Description |
|-----------|---------------|-------------|
| **API Key** | `secure-mcp-key-123` | Authentication key for API access |
| **Port** | `8082` | HTTP server port |
| **Host** | `localhost` | Server bind address |
| **Base Directory** | `./allowed/` | Sandboxed directory for operations |

### Environment Variables
You can also configure via environment variables:
```bash
export MCP_API_KEY="your-custom-key"
export MCP_PORT="8082"
export MCP_HOST="0.0.0.0"  # To accept external connections
```

## 🔌 API Usage Guide

### Base URL Structure
- **Local**: `http://localhost:8082`
- **Public (via ngrok)**: `https://your-subdomain.ngrok-free.app`

### Authentication
All API requests (except health check) require authentication:
```bash
# Header method (recommended)
-H "X-API-Key: secure-mcp-key-123"

# Alternative: Authorization header
-H "Authorization: Bearer secure-mcp-key-123"
```

### 🏥 Health Check
Check if the server is running:
```bash
curl http://localhost:8082/health
```
**Response:**
```json
{
  "status": "healthy",
  "server": "local-file-mcp-server"
}
```

### 🤝 MCP Protocol Endpoints

#### 1. Initialize Connection
Establish MCP connection and get server capabilities:
```bash
curl -X POST http://localhost:8082/mcp \
  -H "Content-Type: application/json" \
  -H "X-API-Key: secure-mcp-key-123" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize"
  }'
```

**Response:**
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "protocolVersion": "2024-11-05",
    "capabilities": {"tools": {}},
    "serverInfo": {
      "name": "local-file-mcp-server",
      "version": "1.0.0"
    }
  }
}
```

#### 2. List Available Tools
Get information about available file operations:
```bash
curl -X POST http://localhost:8082/mcp \
  -H "Content-Type: application/json" \
  -H "X-API-Key: secure-mcp-key-123" \
  -d '{
    "jsonrpc": "2.0",
    "id": 2,
    "method": "tools/list"
  }'
```

**Response:**
```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "result": {
    "tools": [{
      "name": "local_file_mcp_server",
      "description": "Read, write, create, delete, and list local files within the allowed directory",
      "inputSchema": {
        "type": "object",
        "properties": {
          "operation": {
            "type": "string",
            "enum": ["read", "write", "create", "delete", "list"],
            "description": "The file operation to perform"
          },
          "file_path": {
            "type": "string", 
            "description": "Relative path to the file within the allowed directory"
          },
          "content": {
            "type": "string",
            "description": "Content to write (for write/create operations)"
          }
        },
        "required": ["operation", "file_path"]
      }
    }]
  }
}
```

### 📁 File Operations

All file operations use the `tools/call` method with the `local_file_mcp_server` tool.

#### 📝 Create a File
Create a new file with content:
```bash
curl -X POST http://localhost:8082/mcp \
  -H "Content-Type: application/json" \
  -H "X-API-Key: secure-mcp-key-123" \
  -d '{
    "jsonrpc": "2.0",
    "id": 3,
    "method": "tools/call",
    "params": {
      "name": "local_file_mcp_server",
      "arguments": {
        "operation": "create",
        "file_path": "welcome.txt",
        "content": "Hello from MCP Server!\nThis is a test file."
      }
    }
  }'
```
**Response:**
```json
{
  "jsonrpc": "2.0",
  "id": 3,
  "result": {
    "content": [{
      "type": "text",
      "text": "Successfully created welcome.txt with 42 characters"
    }]
  }
}
```

#### 📖 Read a File
Read the contents of an existing file:
```bash
curl -X POST http://localhost:8082/mcp \
  -H "Content-Type: application/json" \
  -H "X-API-Key: secure-mcp-key-123" \
  -d '{
    "jsonrpc": "2.0",
    "id": 4,
    "method": "tools/call",
    "params": {
      "name": "local_file_mcp_server",
      "arguments": {
        "operation": "read",
        "file_path": "welcome.txt"
      }
    }
  }'
```
**Response:**
```json
{
  "jsonrpc": "2.0",
  "id": 4,
  "result": {
    "content": [{
      "type": "text",
      "text": "File: welcome.txt\n\nHello from MCP Server!\nThis is a test file."
    }]
  }
}
```

#### 📋 List Directory Contents
List all files and directories:
```bash
curl -X POST http://localhost:8082/mcp \
  -H "Content-Type: application/json" \
  -H "X-API-Key: secure-mcp-key-123" \
  -d '{
    "jsonrpc": "2.0",
    "id": 5,
    "method": "tools/call",
    "params": {
      "name": "local_file_mcp_server",
      "arguments": {
        "operation": "list",
        "file_path": "."
      }
    }
  }'
```
**Response:**
```json
{
  "jsonrpc": "2.0",
  "id": 5,
  "result": {
    "content": [{
      "type": "text",
      "text": "Contents of allowed/.:\nfile: test.txt\nfile: welcome.txt\ndirectory: docs"
    }]
  }
}
```

#### ✏️ Write to Existing File
Update the content of an existing file:
```bash
curl -X POST http://localhost:8082/mcp \
  -H "Content-Type: application/json" \
  -H "X-API-Key: secure-mcp-key-123" \
  -d '{
    "jsonrpc": "2.0",
    "id": 6,
    "method": "tools/call",
    "params": {
      "name": "local_file_mcp_server",
      "arguments": {
        "operation": "write",
        "file_path": "welcome.txt",
        "content": "Updated content!\nThis file has been modified via MCP."
      }
    }
  }'
```
**Response:**
```json
{
  "jsonrpc": "2.0",
  "id": 6,
  "result": {
    "content": [{
      "type": "text",
      "text": "Successfully wrote 48 characters to welcome.txt"
    }]
  }
}
```

#### 🗑️ Delete a File
Remove a file from the system:
```bash
curl -X POST http://localhost:8082/mcp \
  -H "Content-Type: application/json" \
  -H "X-API-Key: secure-mcp-key-123" \
  -d '{
    "jsonrpc": "2.0",
    "id": 7,
    "method": "tools/call",
    "params": {
      "name": "local_file_mcp_server",
      "arguments": {
        "operation": "delete",
        "file_path": "welcome.txt"
      }
    }
  }'
```
**Response:**
```json
{
  "jsonrpc": "2.0",
  "id": 7,
  "result": {
    "content": [{
      "type": "text",
      "text": "Successfully deleted welcome.txt"
    }]
  }
}
```

## 🌐 Exposing with ngrok (Public Access)

To make your MCP server accessible from anywhere on the internet:

### Step 1: Install ngrok
```bash
# Visit https://ngrok.com and create a free account
# Download ngrok for your platform
# Or use package managers:

# macOS
brew install ngrok

# Windows (with Chocolatey)
choco install ngrok

# Linux
sudo snap install ngrok
```

### Step 2: Start Your Local Server
```bash
cd local_file_mcp_server
python3 simple_mcp_server.py --port 8082
```
Keep this terminal running.

### Step 3: Expose with ngrok
In a **new terminal**:
```bash
ngrok http 8082
```

### Step 4: Get Your Public URL
ngrok will display something like:
```
Forwarding  https://abc123def456.ngrok-free.app -> http://localhost:8082
```

### Step 5: Test Public Access
```bash
curl -X POST https://abc123def456.ngrok-free.app/mcp \
  -H "Content-Type: application/json" \
  -H "X-API-Key: secure-mcp-key-123" \
  -H "ngrok-skip-browser-warning: true" \
  -d '{"jsonrpc": "2.0", "id": 1, "method": "tools/list"}'
```

> **Note**: Add `-H "ngrok-skip-browser-warning: true"` to avoid ngrok's browser warning page.

## 🔒 Security Features

| Feature | Description | Status |
|---------|-------------|--------|
| **🔐 API Key Authentication** | All requests require valid API key | ✅ Active |
| **📁 Sandboxed Directory** | All operations restricted to `allowed/` only | ✅ Active |
| **🛡️ Path Traversal Protection** | Prevents `../` attacks and directory escape | ✅ Active |
| **🚫 No Code Execution** | Pure file operations, no script/command execution | ✅ Active |
| **📝 Operation Validation** | Input validation for all parameters | ✅ Active |
| **🔍 Request Logging** | Server logs all requests for monitoring | ✅ Active |

### Security Best Practices
- ✅ Change the default API key before deployment
- ✅ Use HTTPS in production (ngrok provides this automatically)
- ✅ Monitor the `allowed/` directory for unauthorized changes
- ✅ Regularly rotate API keys
- ❌ Never expose the server without authentication
- ❌ Don't put sensitive files in the `allowed/` directory

## 📊 Available Operations Reference

| Operation | Description | Required Parameters | Optional | Example Use Case |
|-----------|-------------|-------------------|----------|------------------|
| **`read`** | Read file contents | `operation`, `file_path` | - | View configuration files, logs |
| **`write`** | Update existing file | `operation`, `file_path`, `content` | - | Modify settings, update data |
| **`create`** | Create new file | `operation`, `file_path`, `content` | - | Generate reports, save data |
| **`delete`** | Remove file | `operation`, `file_path` | - | Clean up temp files |
| **`list`** | Show directory contents | `operation`, `file_path` | - | Browse available files |

## ⚠️ Error Codes & Troubleshooting

| Code | Meaning | Common Causes | Solution |
|------|---------|---------------|----------|
| **-32700** | Parse error | Invalid JSON syntax | Check JSON formatting |
| **-32601** | Method not found | Wrong MCP method name | Use `initialize`, `tools/list`, or `tools/call` |
| **-32602** | Invalid params | Missing required parameters | Include `operation` and `file_path` |
| **-32001** | Invalid API key | Wrong or missing API key | Check `X-API-Key` header |
| **-32000** | Server error | File operation failed | Check file exists, permissions, path |

### Common Issues
❌ **"File does not exist"**: Make sure the file is in the `allowed/` directory
❌ **"Path outside allowed directory"**: Use relative paths only (no `../`)
❌ **"Permission denied"**: Check file/folder permissions in `allowed/`
❌ **"Address already in use"**: Change the port or stop other services

## 📁 Project Structure

```
local_file_mcp_server/
├── 📄 README.md                    # This comprehensive documentation
├── 📄 INSTALL.md                   # Quick installation guide
├── 🚀 setup.sh                     # Automated setup script
├── 🔧 Makefile                     # Build automation and shortcuts
├── 🔧 requirements.txt             # Python dependencies for testing/dev
├── 🔧 mcp-config.json              # Ready-to-use MCP configuration
├── 🔒 .env.example                 # Environment configuration template
├── 🔒 .env                         # Your actual config (created by generate_key.py)
├── 📄 .gitignore                   # Git ignore rules (protects .env)
│
├── 📁 src/                         # 🐍 Source code
│   ├── __init__.py                 # Package initialization
│   └── server.py                   # Main MCP server implementation
│
├── 📁 scripts/                     # 🔧 Utility scripts
│   ├── __init__.py                 # Package initialization  
│   ├── generate_key.py             # Secure API key generator
│   └── test_client.py              # Demo client for testing
│
├── 📁 tests/                       # 🧪 Test suite
│   ├── __init__.py                 # Package initialization
│   └── test_server.py              # Comprehensive server tests
│
└── 📁 allowed/                     # 🔒 SANDBOXED directory for file operations
    ├── .gitkeep                    # Keeps directory in git
    └── (your files here)           # Files created via API calls
```

## 🚀 Quick Start Checklist

- [ ] **Python 3.7+** installed on your system
- [ ] **Downloaded** this project folder
- [ ] **Generated API key**: `python3 scripts/generate_key.py`
- [ ] **Started server**: `python3 src/server.py`
- [ ] **Tested health**: `curl http://localhost:8082/health`
- [ ] **Tested API**: Use your generated API key
- [ ] **Optional**: Set up ngrok for public access
- [ ] **Optional**: Run tests: `make test` (requires `pip install -r requirements.txt`)

## 🔗 MCP Integration Configuration

### For Claude Desktop Application

Add this to your Claude Desktop `config.json`:

**Location:**
- **macOS**: `~/Library/Application Support/Claude/config.json`
- **Windows**: `%APPDATA%\Claude\config.json`

**Configuration:**
```json
{
  "mcpServers": {
    "local-file-server": {
      "command": "python3",
      "args": [
        "/path/to/local_file_mcp_server/src/server.py",
        "--port", "8082",
        "--api-key", "your-generated-api-key"
      ],
      "env": {
        "MCP_PORT": "8082",
        "MCP_HOST": "localhost"
      }
    }
  }
}
```

### For HTTP/WebSocket Integration

```json
{
  "mcpServers": {
    "local-file-server": {
      "transport": {
        "type": "http",
        "url": "http://localhost:8082/mcp",
        "headers": {
          "X-API-Key": "your-generated-api-key"
        }
      }
    }
  }
}
```

### Environment-Based Configuration

Create a `.env` file in your project:
```bash
# MCP File Server Configuration
MCP_PORT=8082
MCP_HOST=localhost
MCP_API_KEY=your-64-character-secure-key
MCP_ALLOWED_PATH=./allowed
MCP_CREATE_ALLOWED_DIR=true
MCP_MAX_FILE_SIZE=10485760
MCP_ALLOWED_EXTENSIONS=.txt,.json,.md,.csv,.log,.xml,.yaml,.yml,.conf,.cfg
MCP_ENABLE_SUBDIRECTORIES=true
MCP_LOG_LEVEL=INFO
MCP_LOG_REQUESTS=true
```

Then start with:
```bash
python3 src/server.py
```

### 🌐 Public Access Configuration

**1. Using ngrok (Development):**
```bash
# Start server locally
python3 src/server.py

# In another terminal, expose publicly
ngrok http 8082
```

**2. Production deployment:**
```json
{
  "mcpServers": {
    "local-file-server": {
      "transport": {
        "type": "https",
        "url": "https://your-domain.com/mcp",
        "headers": {
          "X-API-Key": "your-production-api-key"
        }
      }
    }
  }
}
```

### 🛠️ Integration Examples

**For MCP-compatible agents like Claude:**
- **Tool Name**: `local_file_mcp_server`
- **Supported Operations**: `create`, `read`, `write`, `delete`, `list`
- **File Restrictions**: Only within `allowed/` directory
- **Authentication**: Required via API key

**For developers:**
```bash
# Test the integration
python3 scripts/test_client.py http://localhost:8082 your-api-key

# Run comprehensive tests  
make test

# Monitor server logs
tail -f server.log
```

**Sample Integration Test:**
```python
import requests

# Test server connection
response = requests.get("http://localhost:8082/health")
print("Health:", response.json())

# Test MCP tool
mcp_request = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/call",
    "params": {
        "name": "local_file_mcp_server",
        "arguments": {
            "operation": "create",
            "file_path": "test.txt",
            "content": "Hello from MCP!"
        }
    }
}

response = requests.post(
    "http://localhost:8082/mcp",
    json=mcp_request,
    headers={"X-API-Key": "your-api-key"}
)
print("Result:", response.json())
```

Ready to integrate with MCP-compatible agents and AI systems! 🎉