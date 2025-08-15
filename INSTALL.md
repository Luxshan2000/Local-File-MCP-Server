# 🚀 Local File MCP Server - Installation Guide

## Quick Installation (5 minutes)

### Step 1: Download
```bash
# Download and extract the project folder
cd /path/to/your/projects/
# Place the local_file_mcp_server folder here
```

### Step 2: Generate API Key
```bash
cd local_file_mcp_server
python3 scripts/generate_key.py
```
Save the generated API key - you'll need it!

### Step 3: Test Installation
```bash
# Start server
python3 src/server.py

# In another terminal, test it
curl http://localhost:8082/health
```

## 🔗 Claude Desktop Integration

### 1. Find your config file:
- **macOS**: `~/Library/Application Support/Claude/config.json`
- **Windows**: `%APPDATA%\Claude\config.json`

### 2. Add this configuration:
```json
{
  "mcpServers": {
    "local-file-server": {
      "command": "python3",
      "args": [
        "/FULL/PATH/TO/local_file_mcp_server/src/server.py",
        "--api-key", "YOUR-GENERATED-API-KEY-HERE"
      ]
    }
  }
}
```

**⚠️ Important:**
- Replace `/FULL/PATH/TO/` with the actual path to your project
- Replace `YOUR-GENERATED-API-KEY-HERE` with your generated key

### 3. Restart Claude Desktop

### 4. Test with Claude
Ask Claude: "Can you list the files in my local directory?"

## 📁 File Operations Available

| Operation | Description | Example |
|-----------|-------------|---------|
| **create** | Create new file | "Create a file called notes.txt" |
| **read** | Read file contents | "Show me the contents of notes.txt" |
| **write** | Update existing file | "Add 'Hello World' to notes.txt" |
| **delete** | Remove file | "Delete the notes.txt file" |
| **list** | Show directory contents | "List all files in the directory" |

## 🔒 Security Features

- ✅ All operations restricted to `allowed/` directory
- ✅ API key authentication required
- ✅ No code execution - only file operations
- ✅ Path traversal protection (can't access `../` paths)
- ✅ File extension restrictions configurable
- ✅ File size limits configurable

## ⚙️ Advanced Configuration

### Environment Variables
Create a `.env` file for custom settings:
```bash
MCP_PORT=8082
MCP_HOST=localhost
MCP_API_KEY=your-api-key
MCP_ALLOWED_PATH=./allowed
MCP_MAX_FILE_SIZE=10485760  # 10MB
MCP_ALLOWED_EXTENSIONS=.txt,.json,.md,.log
```

### Development Setup
```bash
# Install development dependencies
make install

# Run tests
make test

# Format code
make format

# Run demo
make demo
```

## 🌐 Remote Access (Optional)

### Using ngrok for public access:
```bash
# Install ngrok from https://ngrok.com
brew install ngrok  # macOS
# or download from website

# Start server
python3 src/server.py

# In another terminal
ngrok http 8082
```

Use the provided ngrok URL in your MCP config.

## 📋 Troubleshooting

**Server won't start:**
- Check if port 8082 is free: `lsof -i :8082`
- Use different port: `python3 src/server.py --port 8083`

**Claude can't connect:**
- Verify config.json syntax with JSON validator
- Check file paths are absolute, not relative
- Restart Claude Desktop after config changes
- Check server logs for errors

**Permission denied:**
- Ensure Python has write access to project directory
- Check that `allowed/` directory exists

**Authentication errors:**
- Verify API key matches between server and config
- Check for extra spaces in configuration

## 🆘 Getting Help

1. **Check server logs** - Look for error messages in terminal
2. **Test health endpoint** - `curl http://localhost:8082/health`
3. **Verify API key** - Ensure it matches in all configurations
4. **Check file paths** - Use absolute paths in MCP config
5. **Review documentation** - See README.md for detailed examples

## 📊 Success Checklist

- [ ] Python 3.7+ installed
- [ ] Project downloaded and extracted
- [ ] API key generated with `scripts/generate_key.py`
- [ ] Server starts without errors: `python3 src/server.py`
- [ ] Health check passes: `curl http://localhost:8082/health`
- [ ] Claude config.json updated with correct paths and API key
- [ ] Claude Desktop restarted
- [ ] Test file operation with Claude: "List my local files"

**🎉 Once all items are checked, your MCP file server is ready!**