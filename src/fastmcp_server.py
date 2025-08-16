#!/usr/bin/env python3
"""
MCP File Server using FastMCP - Much simpler implementation!
Provides secure file operations within a sandboxed directory
"""

import os
from pathlib import Path
from typing import Annotated

from fastmcp import FastMCP
from fastmcp.server.auth import StaticTokenVerifier

# Configuration from environment
ALLOWED_PATH = os.getenv("MCP_ALLOWED_PATH", "./allowed")
MAX_FILE_SIZE = int(os.getenv("MCP_MAX_FILE_SIZE", "10485760"))  # 10MB
ALLOWED_EXTENSIONS = os.getenv("MCP_ALLOWED_EXTENSIONS", ".txt,.json,.md,.csv,.log,.xml,.yaml,.yml,.conf,.cfg").split(",")

# Multi-tier access keys
MCP_READ_KEY = os.getenv("MCP_READ_KEY")
MCP_WRITE_KEY = os.getenv("MCP_WRITE_KEY") 
MCP_ADMIN_KEY = os.getenv("MCP_ADMIN_KEY")

# Build token configuration
tokens = {}
if MCP_READ_KEY:
    tokens[MCP_READ_KEY] = {
        "client_id": "read-only-user",
        "scopes": ["read:files"]
    }
if MCP_WRITE_KEY:
    tokens[MCP_WRITE_KEY] = {
        "client_id": "write-user", 
        "scopes": ["read:files", "write:files", "edit:files"]
    }
if MCP_ADMIN_KEY:
    tokens[MCP_ADMIN_KEY] = {
        "client_id": "admin-user",
        "scopes": ["read:files", "write:files", "edit:files", "delete:files"]
    }

# Initialize with authentication if tokens are configured
if tokens:
    verifier = StaticTokenVerifier(
        tokens=tokens,
        required_scopes=["read:files"]
    )
    mcp = FastMCP("Local File Server", auth=verifier)
    print(f"🔐 Multi-tier authentication enabled")
    for token, config in tokens.items():
        print(f"🛡️  {config['client_id']}: {', '.join(config['scopes'])} (Token: {token})")
else:
    mcp = FastMCP("Local File Server")
    print(f"⚠️  No API keys configured - running without authentication")

# Set up base directory
base_dir = Path(ALLOWED_PATH).resolve()
base_dir.mkdir(parents=True, exist_ok=True)

print(f"🚀 FastMCP File Server initialized")
print(f"📁 Base directory: {base_dir}")
print(f"📝 Max file size: {MAX_FILE_SIZE / (1024*1024):.1f}MB")


def validate_path(file_path: str) -> Path:
    """Validate and resolve file path within allowed directory"""
    clean_path = file_path.lstrip("/")
    full_path = (base_dir / clean_path).resolve()
    
    if not str(full_path).startswith(str(base_dir)):
        raise ValueError("Path outside allowed directory")
    
    return full_path


def validate_file_extension(file_path: str) -> bool:
    """Validate file extension if restrictions are configured"""
    if not ALLOWED_EXTENSIONS or ALLOWED_EXTENSIONS == ['']:
        return True
    
    file_ext = Path(file_path).suffix.lower()
    return file_ext in ALLOWED_EXTENSIONS


@mcp.tool()
def create_file(file_path: Annotated[str, "Path to create the file"], content: Annotated[str, "Content to write"]) -> str:
    """Create a new file with the given content"""
    full_path = validate_path(file_path)
    
    if full_path.exists():
        raise ValueError(f"File already exists: {file_path}")
    
    if not validate_file_extension(file_path):
        raise ValueError(f"File extension not allowed. Allowed: {', '.join(ALLOWED_EXTENSIONS)}")
    
    if len(content.encode("utf-8")) > MAX_FILE_SIZE:
        raise ValueError(f"File size exceeds limit of {MAX_FILE_SIZE / (1024*1024):.1f}MB")
    
    full_path.parent.mkdir(parents=True, exist_ok=True)
    full_path.write_text(content, encoding="utf-8")
    
    return f"Successfully created {file_path} with {len(content)} characters"


@mcp.tool()
def read_file(file_path: Annotated[str, "Path to read the file"]) -> str:
    """Read the contents of a file"""
    full_path = validate_path(file_path)
    
    if not full_path.exists():
        raise ValueError(f"File does not exist: {file_path}")
    
    if full_path.is_dir():
        raise ValueError(f"Path is a directory: {file_path}")
    
    try:
        content = full_path.read_text(encoding="utf-8")
        return f"File: {file_path}\n\n{content}"
    except UnicodeDecodeError:
        raise ValueError(f"File is not text readable: {file_path}")


@mcp.tool()
def write_file(file_path: Annotated[str, "Path to write the file"], content: Annotated[str, "Content to write"]) -> str:
    """Write content to an existing file"""
    full_path = validate_path(file_path)
    
    if not full_path.exists():
        raise ValueError(f"File does not exist: {file_path}")
    
    if not validate_file_extension(file_path):
        raise ValueError(f"File extension not allowed. Allowed: {', '.join(ALLOWED_EXTENSIONS)}")
    
    if len(content.encode("utf-8")) > MAX_FILE_SIZE:
        raise ValueError(f"File size exceeds limit of {MAX_FILE_SIZE / (1024*1024):.1f}MB")
    
    full_path.write_text(content, encoding="utf-8")
    
    return f"Successfully wrote {len(content)} characters to {file_path}"


@mcp.tool()
def delete_file(file_path: Annotated[str, "Path to delete the file"]) -> str:
    """Delete a file"""
    full_path = validate_path(file_path)
    
    if not full_path.exists():
        raise ValueError(f"File does not exist: {file_path}")
    
    if full_path.is_dir():
        raise ValueError(f"Cannot delete directory: {file_path}")
    
    full_path.unlink()
    
    return f"Successfully deleted {file_path}"


@mcp.tool()
def list_files(directory_path: Annotated[str, "Directory path to list"] = ".") -> str:
    """List files and directories in the given path"""
    target_path = validate_path(directory_path) if directory_path != "." else base_dir
    
    if not target_path.exists():
        raise ValueError(f"Directory does not exist: {directory_path}")
    
    if target_path.is_file():
        raise ValueError(f"Path is a file: {directory_path}")
    
    items = []
    for item in sorted(target_path.iterdir()):
        rel_path = item.relative_to(base_dir)
        item_type = "directory" if item.is_dir() else "file"
        items.append(f"{item_type}: {rel_path}")
    
    return f"Contents of allowed/{directory_path}:\n" + "\n".join(items)


if __name__ == "__main__":
    import sys
    
    # Check if HTTP flag is provided
    if "--http" in sys.argv:
        port = 8082
        if "--port" in sys.argv:
            port_idx = sys.argv.index("--port")
            if port_idx + 1 < len(sys.argv):
                port = int(sys.argv[port_idx + 1])
        
        print(f"🌐 Starting FastMCP HTTP server on port {port}")
        if tokens:
            print(f"🛡️  Multi-tier authentication enabled")
            print(f"📋 Configure tokens using: MCP_READ_KEY, MCP_WRITE_KEY, MCP_ADMIN_KEY")
        
        mcp.run(transport="http", port=port)
    else:
        # Default to stdio for MCP clients like Claude Desktop
        mcp.run()