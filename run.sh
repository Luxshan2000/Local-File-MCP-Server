#!/bin/bash

# Activate virtual environment and run FastMCP server
cd "$(dirname "$0")"
source venv/bin/activate
python src/fastmcp_server.py