#!/bin/bash
# Quick setup script for Local File MCP Server

set -e

echo "🚀 Local File MCP Server - Quick Setup"
echo "======================================"

# Check Python version
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required but not installed."
    echo "Please install Python 3.7+ and try again."
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
echo "✅ Python $PYTHON_VERSION found"

# Check if we're in the right directory
if [ ! -f "src/server.py" ]; then
    echo "❌ Please run this script from the local_file_mcp_server directory"
    exit 1
fi

# Generate API key
echo ""
echo "📝 Generating secure API key..."
if [ -f ".env" ]; then
    echo "⚠️  .env file already exists."
    read -p "Overwrite existing .env? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Using existing .env file"
    else
        python3 scripts/generate_key.py
    fi
else
    python3 scripts/generate_key.py
fi

# Test server startup
echo ""
echo "🧪 Testing server startup..."
timeout 5s python3 src/server.py --port 8083 &
SERVER_PID=$!

sleep 2

# Test health endpoint
if curl -s http://localhost:8083/health > /dev/null; then
    echo "✅ Server test passed!"
    kill $SERVER_PID 2>/dev/null || true
else
    echo "❌ Server test failed"
    kill $SERVER_PID 2>/dev/null || true
    exit 1
fi

# Get current directory for config
CURRENT_DIR=$(pwd)

echo ""
echo "🎉 Setup Complete!"
echo ""
echo "📋 Next Steps:"
echo "1. Add this to your Claude Desktop config.json:"
echo ""
echo "{"
echo "  \"mcpServers\": {"
echo "    \"local-file-server\": {"
echo "      \"command\": \"python3\","
echo "      \"args\": ["
echo "        \"$CURRENT_DIR/src/server.py\""
echo "      ]"
echo "    }"
echo "  }"
echo "}"
echo ""
echo "2. Restart Claude Desktop"
echo "3. Test by asking Claude: 'List my local files'"
echo ""
echo "📍 Config file locations:"
echo "  macOS: ~/Library/Application Support/Claude/config.json"
echo "  Windows: %APPDATA%\\Claude\\config.json"
echo ""
echo "🔧 To start server manually: python3 src/server.py"
echo "❤️  Health check: curl http://localhost:8082/health"
echo ""
echo "📚 See README.md and INSTALL.md for detailed documentation"