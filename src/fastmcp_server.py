#!/usr/bin/env python3
"""
MCP File Server using FastMCP - Much simpler implementation!
Provides secure file operations within a sandboxed directory
"""

import os
from pathlib import Path
from typing import Annotated, List
from functools import wraps

from fastmcp import FastMCP
from fastmcp.server.auth import StaticTokenVerifier
from fastmcp.server.dependencies import get_access_token

# Configuration from environment
ALLOWED_PATH = os.getenv("MCP_ALLOWED_PATH", "./allowed")
MAX_FILE_SIZE = int(os.getenv("MCP_MAX_FILE_SIZE", "10485760"))  # 10MB
ALLOWED_EXTENSIONS = os.getenv("MCP_ALLOWED_EXTENSIONS", ".txt,.json,.md,.csv,.log,.xml,.yaml,.yml,.conf,.cfg").split(",")

# Multi-tier access keys
MCP_READ_KEY = os.getenv("MCP_READ_KEY",'test-read')
MCP_WRITE_KEY = os.getenv("MCP_WRITE_KEY",'test-write') 
MCP_ADMIN_KEY = os.getenv("MCP_ADMIN_KEY",'test-admin')

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

# Validation decorators
def requires_scopes(*required_scopes: str):
    """Decorator to register tools with required scopes"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Validate scope
            token = get_access_token()
            if token:
                user_scopes = set(token.scopes)
                required_scope_set = set(required_scopes)
                if not required_scope_set.issubset(user_scopes):
                    missing_scopes = required_scope_set - user_scopes
                    raise ValueError(f"Insufficient permissions: requires {', '.join(missing_scopes)}")
            return func(*args, **kwargs)
        return wrapper
    return decorator

def validates_path_and_extension(path_param: str = "file_path", check_extension: bool = True):
    """Decorator to validate file path and optionally extension"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Get the path value - try kwargs first, then args
            path_value = None
            path_index = 0
            
            if path_param in kwargs:
                path_value = kwargs[path_param]
            elif len(args) > path_index:
                path_value = args[path_index]
            else:
                raise ValueError(f"Path parameter '{path_param}' not found")
            
            # Handle default "." case by using base_dir
            if path_value == ".":
                validated_path = base_dir
            else:
                # Validate and resolve path within ALLOWED_PATH base
                validated_path = validate_path(path_value)
            
            # Validate extension if required
            if check_extension and not validate_file_extension(path_value):
                raise ValueError(f"File extension not allowed. Allowed: {', '.join(ALLOWED_EXTENSIONS)}")
            
            # Update the path in args or kwargs
            if path_param in kwargs:
                kwargs[path_param] = validated_path
                return func(*args, **kwargs)
            else:
                new_args = (validated_path,) + args[1:]
                return func(*new_args, **kwargs)
        return wrapper
    return decorator

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
@requires_scopes("write:files")
@validates_path_and_extension()
def create_file(file_path: Annotated[str, "Path to create the file"], content: Annotated[str, "Content to write"]) -> str:
    """Create a new file with the given content"""
    # file_path is now a validated Path object
    if file_path.exists():
        rel_path = file_path.relative_to(base_dir)
        raise ValueError(f"File already exists: {rel_path}")
    
    if len(content.encode("utf-8")) > MAX_FILE_SIZE:
        raise ValueError(f"File size exceeds limit of {MAX_FILE_SIZE / (1024*1024):.1f}MB")
    
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(content, encoding="utf-8")
    
    rel_path = file_path.relative_to(base_dir)
    return f"Successfully created {rel_path} with {len(content)} characters"


@mcp.tool()
@requires_scopes("read:files")
@validates_path_and_extension(check_extension=False)
def read_file(file_path: Annotated[str, "Path to read the file"]) -> str:
    """Read the contents of a file"""
    # file_path is now a validated Path object
    
    if not file_path.exists():
        rel_path = file_path.relative_to(base_dir)
        raise ValueError(f"File does not exist: {rel_path}")
    
    if file_path.is_dir():
        rel_path = file_path.relative_to(base_dir)
        raise ValueError(f"Path is a directory: {rel_path}")
    
    try:
        content = file_path.read_text(encoding="utf-8")
        rel_path = file_path.relative_to(base_dir)
        return f"File: {rel_path}\n\n{content}"
    except UnicodeDecodeError:
        rel_path = file_path.relative_to(base_dir)
        raise ValueError(f"File is not text readable: {rel_path}")


@mcp.tool()
@requires_scopes("write:files")
@validates_path_and_extension()
def write_file(file_path: Annotated[str, "Path to write the file"], content: Annotated[str, "Content to write"]) -> str:
    """Write content to an existing file"""
    # file_path is now a validated Path object
    if not file_path.exists():
        rel_path = file_path.relative_to(base_dir)
        raise ValueError(f"File does not exist: {rel_path}")
    
    if len(content.encode("utf-8")) > MAX_FILE_SIZE:
        raise ValueError(f"File size exceeds limit of {MAX_FILE_SIZE / (1024*1024):.1f}MB")
    
    file_path.write_text(content, encoding="utf-8")
    
    rel_path = file_path.relative_to(base_dir)
    return f"Successfully wrote {len(content)} characters to {rel_path}"


@mcp.tool()
@requires_scopes("delete:files")
@validates_path_and_extension(check_extension=False)
def delete_file(file_path: Annotated[str, "Path to delete the file"]) -> str:
    """Delete a file"""
    # file_path is now a validated Path object
    
    if not file_path.exists():
        rel_path = file_path.relative_to(base_dir)
        raise ValueError(f"File does not exist: {rel_path}")
    
    if file_path.is_dir():
        rel_path = file_path.relative_to(base_dir)
        raise ValueError(f"Cannot delete directory: {rel_path}")
    
    file_path.unlink()
    
    rel_path = file_path.relative_to(base_dir)
    return f"Successfully deleted {rel_path}"


@mcp.tool()
@requires_scopes("read:files")
@validates_path_and_extension("directory_path", check_extension=False)
def list_files(directory_path: Annotated[str, "Directory path to list"] = ".") -> str:
    """List files and directories in the given path"""
    # directory_path is now a validated Path object
    target_path = directory_path
    
    if not target_path.exists():
        raise ValueError(f"Directory does not exist: {target_path.relative_to(base_dir)}")
    
    if target_path.is_file():
        raise ValueError(f"Path is a file: {target_path.relative_to(base_dir)}")
    
    items = []
    for item in sorted(target_path.iterdir()):
        rel_path = item.relative_to(base_dir)
        item_type = "directory" if item.is_dir() else "file"
        items.append(f"{item_type}: {rel_path}")
    
    relative_display = target_path.relative_to(base_dir) if target_path != base_dir else "."
    return f"Contents of {relative_display}:\n" + "\n".join(items)


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