# FastMCP File Server

[![PyPI version](https://badge.fury.io/py/fastmcp-file-server.svg)](https://badge.fury.io/py/fastmcp-file-server)
[![Python](https://img.shields.io/pypi/pyversions/fastmcp-file-server.svg)](https://pypi.org/project/fastmcp-file-server/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Downloads](https://pepy.tech/badge/fastmcp-file-server)](https://pepy.tech/project/fastmcp-file-server)
[![Downloads/Month](https://pepy.tech/badge/fastmcp-file-server/month)](https://pepy.tech/project/fastmcp-file-server)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

A versatile, secure file server implementing the Model Context Protocol (MCP) that provides AI assistants with safe file operations. Features multiple connection modes, configurable access levels, and comprehensive security controls for various deployment scenarios.

## 🚀 Features

- **Comprehensive File Operations**: Create, read, write, delete, copy, move, rename files and directories
- **Advanced Text Manipulation**: Line-specific operations, search and replace, pattern matching
- **File Analysis**: Size, permissions, timestamps, hash verification, diff generation
- **Batch Operations**: Handle multiple files efficiently in single operations
- **Archive Support**: Create and extract ZIP files
- **Format Conversion**: Text to PDF, image format conversion, CSV ↔ JSON
- **Multiple Connection Modes**: stdio, HTTP, and public access via ngrok
- **Tiered Access Control**: Read-only, Read/Write, and Admin permission levels
- **Security First**: All operations restricted to configured safe directories

## 📦 Installation

### From PyPI (Recommended)

```bash
# Using uv (recommended)
uv tool install fastmcp-file-server

# Using pip
pip install fastmcp-file-server
```

### From Source

```bash
git clone https://github.com/Luxshan2000/Local-File-MCP-Server.git
cd Local-File-MCP-Server
uv sync
```

## 🔧 Quick Start

### Basic Usage

```bash
# Set allowed directory
export MCP_ALLOWED_PATH="/path/to/your/files"

# Start stdio server (for Claude Desktop)
fastmcp-file-server

# Start HTTP server
fastmcp-file-server-http
```

### With Authentication

```bash
# Set admin key for HTTP mode
export MCP_ADMIN_KEY="your-secret-token"
export MCP_HTTP_PORT=8082
fastmcp-file-server-http
```

## ⚙️ Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MCP_ALLOWED_PATH` | `./allowed` | Directory path for file operations |
| `MCP_HTTP_PORT` | `8082` | HTTP server port |
| `MCP_ADMIN_KEY` | `None` | Authentication token for HTTP mode |
| `MCP_MAX_FILE_SIZE` | `10MB` | Maximum file size limit |
| `MCP_READ_ONLY` | `false` | Enable read-only mode |
| `MCP_LOG_LEVEL` | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) |

### Configuration Files

Create a `.env` file in your project root:

```bash
# Required: Safe directory for file operations
MCP_ALLOWED_PATH=/absolute/path/to/your/files

# Optional: HTTP server settings
MCP_HTTP_PORT=8082
MCP_ADMIN_KEY=your-secret-token-here

# Optional: Security settings
MCP_MAX_FILE_SIZE=50MB
MCP_READ_ONLY=false
MCP_LOG_LEVEL=INFO
```

## 🔗 Integration

### Claude Desktop Integration

**Configuration file locations:**
- **macOS**: `~/Library/Application Support/Claude/config.json`
- **Windows**: `%APPDATA%\Claude\config.json`

#### Stdio Mode (Direct Integration)

```json
{
  "mcpServers": {
    "local-file-server": {
      "command": "fastmcp-file-server",
      "env": {
        "MCP_ALLOWED_PATH": "/absolute/path/to/your/allowed/directory"
      }
    }
  }
}
```

#### HTTP Mode (Local Server)

1. Start the HTTP server:
```bash
export MCP_ADMIN_KEY="your-secret-token"
fastmcp-file-server-http
```

2. Configure Claude Desktop:
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

#### HTTP Mode with mcp-remote Proxy

For environments requiring a proxy:

```bash
# Install mcp-remote
npm install -g mcp-remote
```

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

### Public Access with ngrok

For web-based AI systems (ChatGPT, etc.):

```bash
# Terminal 1: Start authenticated HTTP server
export MCP_ADMIN_KEY="your-secret-token"
export MCP_HTTP_PORT=8082
fastmcp-file-server-http

# Terminal 2: Expose publicly via ngrok
ngrok http 8082
```

Use the ngrok URL in your web-based AI system:
- **URL**: `https://abc123.ngrok.io/mcp`
- **Header**: `Authorization: Bearer your-secret-token`

## 🔒 Security

### Token Management

**⚠️ Important Security Notes:**

- **With Keys**: When `MCP_ADMIN_KEY` is set, all HTTP requests require the `Authorization: Bearer <token>` header
- **Without Keys**: If `MCP_ADMIN_KEY` is unset, the server runs without authentication (use only in secure environments)
- **Temporary Exposure**: For ngrok or temporary remote access, always use strong tokens and revoke access when done
- **Key Rotation**: Regularly rotate your `MCP_ADMIN_KEY`, especially after temporary exposures

### Best Practices

1. **Never commit secrets**: Use `.env` files (added to `.gitignore`)
2. **Use strong tokens**: Generate cryptographically secure random tokens
3. **Limit access scope**: Set `MCP_ALLOWED_PATH` to the minimum required directory
4. **Monitor usage**: Check logs for unauthorized access attempts
5. **Temporary access**: Unset `MCP_ADMIN_KEY` and restart after temporary exposures

### Access Levels

- **No Key Set**: Server runs without authentication (local use only)
- **Key Set**: All operations require valid Bearer token
- **Read-Only Mode**: Set `MCP_READ_ONLY=true` to prevent modifications

## 💡 Usage Examples

### File Operations
```
# Basic operations
"Create a file called notes.txt with my meeting notes"
"Read lines 10-20 from config.py"
"Copy config.json to backup/config_backup.json"

# Advanced operations
"Search for 'TODO' comments in all Python files"
"Replace 'old_function' with 'new_function' in utils.py"
"Create a ZIP archive of all source files"
"Convert report.txt to PDF format"
"Calculate SHA256 hash of important_file.pdf"
```

### Batch Operations
```
"Read all .py files in the src/ directory"
"Create these 5 configuration files with their content"
"Delete all .tmp files in the workspace"
"Find all JavaScript files containing 'console.log'"
```

## 🛠️ Development

See [DEVELOPER.md](DEVELOPER.md) for detailed development setup and contribution guidelines.

### Quick Development Setup

```bash
# Clone repository
git clone https://github.com/Luxshan2000/Local-File-MCP-Server.git
cd Local-File-MCP-Server

# Install dependencies
uv sync

# Run development server
uv run server          # stdio mode
uv run server-http     # HTTP mode

# Run tests and linting
uv run test
uv run lint
uv run format
```

## 📊 API Reference

### Available Tools

| Tool | Description | Access Level |
|------|-------------|--------------|
| `read_file` | Read file contents or specific line ranges | Read-only |
| `write_file` | Create or overwrite files | Read/Write |
| `append_file` | Append content to existing files | Read/Write |
| `delete_file` | Remove files and directories | Admin |
| `copy_file` | Copy files and directories | Read/Write |
| `move_file` | Move/rename files and directories | Read/Write |
| `list_directory` | List directory contents with filtering | Read-only |
| `create_directory` | Create new directories | Read/Write |
| `get_file_info` | Get file metadata and permissions | Read-only |
| `search_files` | Search for files by name patterns | Read-only |
| `search_content` | Search file contents with regex | Read-only |
| `replace_content` | Find and replace text in files | Read/Write |
| `insert_lines` | Insert text at specific line numbers | Read/Write |
| `delete_lines` | Remove specific line ranges | Read/Write |
| `compare_files` | Generate diffs between files | Read-only |
| `create_archive` | Create ZIP archives | Read/Write |
| `extract_archive` | Extract ZIP archives | Read/Write |
| `calculate_hash` | Generate file hashes (MD5, SHA1, SHA256) | Read-only |
| `convert_document` | Convert text to PDF | Read/Write |
| `convert_image` | Convert between image formats | Read/Write |
| `convert_data` | Convert between CSV and JSON | Read/Write |

## 🐛 Troubleshooting

### Common Issues

**Server won't start:**
```bash
# Reinstall dependencies
uv sync

# Check Python version
python --version  # Requires Python 3.10+
```

**Claude Desktop not connecting:**
1. Verify all paths in configuration are absolute (full paths)
2. Restart Claude Desktop after changing configuration
3. Check server starts without errors: `uv run server`
4. Ensure `MCP_ALLOWED_PATH` directory exists and is accessible

**HTTP authentication fails:**
1. Verify `MCP_ADMIN_KEY` is set before starting server
2. Check Authorization header format: `Bearer your-secret-token`
3. Ensure token matches exactly (no extra spaces)

**Permission denied errors:**
1. Check file/directory permissions
2. Verify `MCP_ALLOWED_PATH` is accessible
3. Ensure user has read/write permissions in the allowed directory

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🤝 Contributing

We welcome contributions! Please see [DEVELOPER.md](DEVELOPER.md) for development setup and [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) for community guidelines.

## 🔗 Links

- **Repository**: https://github.com/Luxshan2000/Local-File-MCP-Server
- **PyPI Package**: https://pypi.org/project/fastmcp-file-server/
- **Issues**: https://github.com/Luxshan2000/Local-File-MCP-Server/issues
- **Model Context Protocol**: https://modelcontextprotocol.io/

## ⭐ Support

If you find this project useful, please consider giving it a star on GitHub!