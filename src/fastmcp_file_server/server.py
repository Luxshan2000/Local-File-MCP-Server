import os
import re
import shutil
import stat
import zipfile
import hashlib
import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Annotated
from functools import wraps
import difflib

from fastmcp import FastMCP
from fastmcp.server.auth import StaticTokenVerifier
from fastmcp.server.dependencies import get_access_token
from dotenv import load_dotenv

load_dotenv()
# Configuration from environment
ALLOWED_PATH = os.getenv("MCP_ALLOWED_PATH", "./allowed")
MAX_FILE_SIZE = int(os.getenv("MCP_MAX_FILE_SIZE", "10485760"))  # 10MB
ALLOWED_EXTENSIONS = os.getenv(
    "MCP_ALLOWED_EXTENSIONS",
    ".txt,.json,.md,.csv,.log,.xml,.yaml,.yml,.conf,.cfg,.zip,.pdf,.jpg,.png",
).split(",")
HTTP_PORT = int(os.getenv("MCP_HTTP_PORT", "8082"))

# Multi-tier access keys
MCP_READ_KEY = os.getenv("MCP_READ_KEY")
MCP_WRITE_KEY = os.getenv("MCP_WRITE_KEY")
MCP_ADMIN_KEY = os.getenv("MCP_ADMIN_KEY")

# Build token configuration
tokens = {}
if MCP_READ_KEY:
    tokens[MCP_READ_KEY] = {"client_id": "read-only-user", "scopes": ["read:files"]}
if MCP_WRITE_KEY:
    tokens[MCP_WRITE_KEY] = {
        "client_id": "write-user",
        "scopes": ["read:files", "write:files", "edit:files"],
    }
if MCP_ADMIN_KEY:
    tokens[MCP_ADMIN_KEY] = {
        "client_id": "admin-user",
        "scopes": ["read:files", "write:files", "edit:files", "delete:files"],
    }

# Initialize with authentication if tokens are configured
if tokens:
    verifier = StaticTokenVerifier(tokens=tokens, required_scopes=["read:files"])
    mcp = FastMCP("Local File Server", auth=verifier)
else:
    mcp = FastMCP("Local File Server")

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
                    raise ValueError(
                        f"Insufficient permissions: requires {', '.join(missing_scopes)}"
                    )
            return func(*args, **kwargs)

        return wrapper

    return decorator


def validates_paths(*path_params, check_extensions=True):
    """Unified decorator to validate one or more file paths and optionally extensions"""

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # If no path_params specified, default to single "file_path"
            params_to_validate = path_params if path_params else ("file_path",)

            validated_paths = {}

            for i, path_param in enumerate(params_to_validate):
                # Get the path value - try kwargs first, then args
                path_value = None

                if path_param in kwargs:
                    path_value = kwargs[path_param]
                elif len(args) > i:
                    path_value = args[i]
                else:
                    raise ValueError(f"Path parameter '{path_param}' not found")

                # Handle default "." case by using base_dir
                if path_value == ".":
                    validated_path = base_dir
                else:
                    # Validate and resolve path within ALLOWED_PATH base
                    validated_path = validate_path(path_value)

                # Validate extension if required (skip for directories or when disabled)
                if check_extensions and "dir" not in path_param.lower():
                    if not validate_file_extension(path_value):
                        raise ValueError(
                            f"File extension not allowed for {path_param}. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
                        )

                validated_paths[path_param] = validated_path

            # Update paths in kwargs or args
            if all(param in kwargs for param in params_to_validate):
                # All parameters are in kwargs
                for param in params_to_validate:
                    kwargs[param] = validated_paths[param]
                return func(*args, **kwargs)
            else:
                # Some or all parameters are positional
                new_args = tuple(
                    (
                        validated_paths[params_to_validate[i]]
                        if i < len(params_to_validate)
                        else args[i]
                    )
                    for i in range(len(args))
                )
                return func(*new_args, **kwargs)

        return wrapper

    return decorator


print("FastMCP File Server initialized")
print(f"Base directory: {base_dir}")
print(f"Max file size: {MAX_FILE_SIZE / (1024*1024):.1f}MB")


def validate_path(file_path: str) -> Path:
    """Validate and resolve file path within allowed directory"""
    clean_path = file_path.lstrip("/")
    full_path = (base_dir / clean_path).resolve()

    if not str(full_path).startswith(str(base_dir)):
        raise ValueError("Path outside allowed directory")

    return full_path


def validate_file_extension(file_path: str) -> bool:
    """Validate file extension if restrictions are configured"""
    if not ALLOWED_EXTENSIONS or ALLOWED_EXTENSIONS == [""]:
        return True

    file_ext = Path(file_path).suffix.lower()
    return file_ext in ALLOWED_EXTENSIONS


@mcp.tool()
@requires_scopes("write:files")
@validates_paths("file_path")
def create_file(
    file_path: Annotated[str, "Path to create the file"],
    content: Annotated[str, "Content to write"],
) -> str:
    """Create a new file with the given content"""
    # file_path is now a validated Path object
    if file_path.exists():
        rel_path = file_path.relative_to(base_dir)
        raise ValueError(f"File already exists: {rel_path}")

    if len(content.encode("utf-8")) > MAX_FILE_SIZE:
        raise ValueError(
            f"File size exceeds limit of {MAX_FILE_SIZE / (1024*1024):.1f}MB"
        )

    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(content, encoding="utf-8")

    rel_path = file_path.relative_to(base_dir)
    return f"Successfully created {rel_path} with {len(content)} characters"


@mcp.tool()
@requires_scopes("read:files")
@validates_paths("file_path", check_extensions=False)
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
@validates_paths("file_path")
def write_file(
    file_path: Annotated[str, "Path to write the file"],
    content: Annotated[str, "Content to write"],
) -> str:
    """Write content to an existing file"""
    # file_path is now a validated Path object
    if not file_path.exists():
        rel_path = file_path.relative_to(base_dir)
        raise ValueError(f"File does not exist: {rel_path}")

    if len(content.encode("utf-8")) > MAX_FILE_SIZE:
        raise ValueError(
            f"File size exceeds limit of {MAX_FILE_SIZE / (1024*1024):.1f}MB"
        )

    file_path.write_text(content, encoding="utf-8")

    rel_path = file_path.relative_to(base_dir)
    return f"Successfully wrote {len(content)} characters to {rel_path}"


@mcp.tool()
@requires_scopes("delete:files")
@validates_paths("file_path", check_extensions=False)
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
@validates_paths("directory_path", check_extensions=False)
def list_files(directory_path: Annotated[str, "Directory path to list"] = ".") -> str:
    """List files and directories in the given path"""
    # directory_path is now a validated Path object
    target_path = directory_path

    if not target_path.exists():
        raise ValueError(
            f"Directory does not exist: {target_path.relative_to(base_dir)}"
        )

    if target_path.is_file():
        raise ValueError(f"Path is a file: {target_path.relative_to(base_dir)}")

    items = []
    for item in sorted(target_path.iterdir()):
        rel_path = item.relative_to(base_dir)
        item_type = "directory" if item.is_dir() else "file"
        items.append(f"{item_type}: {rel_path}")

    relative_display = (
        target_path.relative_to(base_dir) if target_path != base_dir else "."
    )
    return f"Contents of {relative_display}:\n" + "\n".join(items)


# Line-based operations
@mcp.tool()
@requires_scopes("read:files")
@validates_paths("file_path", check_extensions=False)
def read_lines(
    file_path: Annotated[str, "Path to read the file"],
    start_line: Annotated[int, "Starting line number (1-based)"],
    end_line: Annotated[int, "Ending line number (1-based, inclusive)"],
) -> str:
    """Read specific line ranges from a file"""
    if not file_path.exists():
        rel_path = file_path.relative_to(base_dir)
        raise ValueError(f"File does not exist: {rel_path}")

    if file_path.is_dir():
        rel_path = file_path.relative_to(base_dir)
        raise ValueError(f"Path is a directory: {rel_path}")

    try:
        lines = file_path.read_text(encoding="utf-8").splitlines()

        # Convert to 0-based indexing
        start_idx = max(0, start_line - 1)
        end_idx = min(len(lines), end_line)

        if start_idx >= len(lines):
            raise ValueError(
                f"Start line {start_line} exceeds file length ({len(lines)} lines)"
            )

        selected_lines = lines[start_idx:end_idx]
        rel_path = file_path.relative_to(base_dir)

        result = f"Lines {start_line}-{end_line} from {rel_path}:\n"
        for i, line in enumerate(selected_lines, start=start_line):
            result += f"{i}: {line}\n"

        return result.rstrip()

    except UnicodeDecodeError:
        rel_path = file_path.relative_to(base_dir)
        raise ValueError(f"File is not text readable: {rel_path}")


@mcp.tool()
@requires_scopes("write:files")
@validates_paths("file_path")
def write_lines(
    file_path: Annotated[str, "Path to write the file"],
    lines_array: Annotated[list, "Array of lines to write"],
    start_line: Annotated[int, "Starting line number (1-based) to replace from"],
) -> str:
    """Insert/replace specific lines in a file"""
    if not file_path.exists():
        rel_path = file_path.relative_to(base_dir)
        raise ValueError(f"File does not exist: {rel_path}")

    try:
        existing_lines = file_path.read_text(encoding="utf-8").splitlines()
    except UnicodeDecodeError:
        rel_path = file_path.relative_to(base_dir)
        raise ValueError(f"File is not text readable: {rel_path}")

    # Convert to 0-based indexing
    start_idx = start_line - 1

    if start_idx < 0:
        raise ValueError("Line number must be >= 1")

    # Replace lines starting from start_idx
    new_lines = (
        existing_lines[:start_idx]
        + lines_array
        + existing_lines[start_idx + len(lines_array) :]
    )

    new_content = "\n".join(new_lines)
    if len(new_content.encode("utf-8")) > MAX_FILE_SIZE:
        raise ValueError(
            f"File size exceeds limit of {MAX_FILE_SIZE / (1024*1024):.1f}MB"
        )

    file_path.write_text(new_content, encoding="utf-8")

    rel_path = file_path.relative_to(base_dir)
    return f"Successfully wrote {len(lines_array)} lines to {rel_path} starting at line {start_line}"


@mcp.tool()
@requires_scopes("write:files")
@validates_paths("file_path")
def insert_lines(
    file_path: Annotated[str, "Path to write the file"],
    content: Annotated[str, "Content to insert"],
    line_number: Annotated[int, "Line number (1-based) to insert after"],
) -> str:
    """Insert content at specific line number"""
    if not file_path.exists():
        rel_path = file_path.relative_to(base_dir)
        raise ValueError(f"File does not exist: {rel_path}")

    try:
        existing_lines = file_path.read_text(encoding="utf-8").splitlines()
    except UnicodeDecodeError:
        rel_path = file_path.relative_to(base_dir)
        raise ValueError(f"File is not text readable: {rel_path}")

    # Convert to 0-based indexing
    insert_idx = line_number - 1

    if insert_idx < 0:
        raise ValueError("Line number must be >= 1")

    # Insert content lines
    content_lines = content.splitlines()
    new_lines = (
        existing_lines[:insert_idx] + content_lines + existing_lines[insert_idx:]
    )

    new_content = "\n".join(new_lines)
    if len(new_content.encode("utf-8")) > MAX_FILE_SIZE:
        raise ValueError(
            f"File size exceeds limit of {MAX_FILE_SIZE / (1024*1024):.1f}MB"
        )

    file_path.write_text(new_content, encoding="utf-8")

    rel_path = file_path.relative_to(base_dir)
    return f"Successfully inserted {len(content_lines)} lines to {rel_path} at line {line_number}"


@mcp.tool()
@requires_scopes("write:files")
@validates_paths("file_path")
def delete_lines(
    file_path: Annotated[str, "Path to write the file"],
    start_line: Annotated[int, "Starting line number (1-based)"],
    end_line: Annotated[int, "Ending line number (1-based, inclusive)"],
) -> str:
    """Delete line ranges from a file"""
    if not file_path.exists():
        rel_path = file_path.relative_to(base_dir)
        raise ValueError(f"File does not exist: {rel_path}")

    try:
        existing_lines = file_path.read_text(encoding="utf-8").splitlines()
    except UnicodeDecodeError:
        rel_path = file_path.relative_to(base_dir)
        raise ValueError(f"File is not text readable: {rel_path}")

    # Convert to 0-based indexing
    start_idx = start_line - 1
    end_idx = end_line

    if start_idx < 0 or start_line > end_line:
        raise ValueError("Invalid line range")

    if start_idx >= len(existing_lines):
        raise ValueError(
            f"Start line {start_line} exceeds file length ({len(existing_lines)} lines)"
        )

    # Delete lines in range
    new_lines = existing_lines[:start_idx] + existing_lines[end_idx:]

    new_content = "\n".join(new_lines)
    file_path.write_text(new_content, encoding="utf-8")

    deleted_count = end_line - start_line + 1
    rel_path = file_path.relative_to(base_dir)
    return f"Successfully deleted {deleted_count} lines from {rel_path} (lines {start_line}-{end_line})"


@mcp.tool()
@requires_scopes("write:files")
@validates_paths("file_path")
def append_lines(
    file_path: Annotated[str, "Path to write the file"],
    content: Annotated[str, "Content to append"],
) -> str:
    """Add lines to end of file"""
    if not file_path.exists():
        rel_path = file_path.relative_to(base_dir)
        raise ValueError(f"File does not exist: {rel_path}")

    try:
        existing_content = file_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        rel_path = file_path.relative_to(base_dir)
        raise ValueError(f"File is not text readable: {rel_path}")

    # Add newline if file doesn't end with one
    separator = "" if existing_content.endswith("\n") else "\n"
    new_content = existing_content + separator + content

    if len(new_content.encode("utf-8")) > MAX_FILE_SIZE:
        raise ValueError(
            f"File size exceeds limit of {MAX_FILE_SIZE / (1024*1024):.1f}MB"
        )

    file_path.write_text(new_content, encoding="utf-8")

    lines_added = len(content.splitlines())
    rel_path = file_path.relative_to(base_dir)
    return f"Successfully appended {lines_added} lines to {rel_path}"


# Search & Replace operations
@mcp.tool()
@requires_scopes("read:files")
@validates_paths("file_path", check_extensions=False)
def search_in_file(
    file_path: Annotated[str, "Path to search in"],
    pattern: Annotated[str, "Text pattern to search for"],
    regex: Annotated[bool, "Whether to use regex pattern matching"] = False,
) -> str:
    """Find text/patterns in a file"""
    if not file_path.exists():
        rel_path = file_path.relative_to(base_dir)
        raise ValueError(f"File does not exist: {rel_path}")

    if file_path.is_dir():
        rel_path = file_path.relative_to(base_dir)
        raise ValueError(f"Path is a directory: {rel_path}")

    try:
        content = file_path.read_text(encoding="utf-8")
        lines = content.splitlines()
    except UnicodeDecodeError:
        rel_path = file_path.relative_to(base_dir)
        raise ValueError(f"File is not text readable: {rel_path}")

    matches = []

    for line_num, line in enumerate(lines, 1):
        if regex:
            try:
                if re.search(pattern, line):
                    matches.append(f"{line_num}: {line}")
            except re.error as e:
                raise ValueError(f"Invalid regex pattern: {e}")
        else:
            if pattern in line:
                matches.append(f"{line_num}: {line}")

    rel_path = file_path.relative_to(base_dir)
    if matches:
        return f"Found {len(matches)} matches in {rel_path}:\n" + "\n".join(matches)
    else:
        return f"No matches found for '{pattern}' in {rel_path}"


@mcp.tool()
@requires_scopes("write:files")
@validates_paths("file_path")
def replace_in_file(
    file_path: Annotated[str, "Path to write the file"],
    search: Annotated[str, "Text to search for"],
    replace: Annotated[str, "Text to replace with"],
    all: Annotated[bool, "Replace all occurrences"] = True,
) -> str:
    """Find and replace text in a file"""
    if not file_path.exists():
        rel_path = file_path.relative_to(base_dir)
        raise ValueError(f"File does not exist: {rel_path}")

    try:
        content = file_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        rel_path = file_path.relative_to(base_dir)
        raise ValueError(f"File is not text readable: {rel_path}")

    # Count occurrences before replacement
    count = content.count(search)
    if count == 0:
        rel_path = file_path.relative_to(base_dir)
        return f"No occurrences of '{search}' found in {rel_path}"

    # Perform replacement
    if all:
        new_content = content.replace(search, replace)
        replaced_count = count
    else:
        new_content = content.replace(search, replace, 1)
        replaced_count = 1

    if len(new_content.encode("utf-8")) > MAX_FILE_SIZE:
        raise ValueError(
            f"File size exceeds limit of {MAX_FILE_SIZE / (1024*1024):.1f}MB"
        )

    file_path.write_text(new_content, encoding="utf-8")

    rel_path = file_path.relative_to(base_dir)
    return f"Successfully replaced {replaced_count} occurrence(s) of '{search}' in {rel_path}"


@mcp.tool()
@requires_scopes("write:files")
@validates_paths("file_path")
def find_and_replace_lines(
    file_path: Annotated[str, "Path to write the file"],
    line_pattern: Annotated[str, "Pattern to match entire lines"],
    replacement: Annotated[str, "Replacement text for matched lines"],
) -> str:
    """Replace entire lines that match a pattern"""
    if not file_path.exists():
        rel_path = file_path.relative_to(base_dir)
        raise ValueError(f"File does not exist: {rel_path}")

    try:
        lines = file_path.read_text(encoding="utf-8").splitlines()
    except UnicodeDecodeError:
        rel_path = file_path.relative_to(base_dir)
        raise ValueError(f"File is not text readable: {rel_path}")

    new_lines = []
    replaced_count = 0

    for line in lines:
        if line_pattern in line:
            new_lines.append(replacement)
            replaced_count += 1
        else:
            new_lines.append(line)

    if replaced_count == 0:
        rel_path = file_path.relative_to(base_dir)
        return f"No lines matching '{line_pattern}' found in {rel_path}"

    new_content = "\n".join(new_lines)
    if len(new_content.encode("utf-8")) > MAX_FILE_SIZE:
        raise ValueError(
            f"File size exceeds limit of {MAX_FILE_SIZE / (1024*1024):.1f}MB"
        )

    file_path.write_text(new_content, encoding="utf-8")

    rel_path = file_path.relative_to(base_dir)
    return f"Successfully replaced {replaced_count} line(s) matching '{line_pattern}' in {rel_path}"


# File management operations
@mcp.tool()
@requires_scopes("write:files")
@validates_paths("source_path", "dest_path")
def copy_file(
    source_path: Annotated[str, "Source file path"],
    dest_path: Annotated[str, "Destination file path"],
) -> str:
    """Copy files"""
    # Both paths are now validated Path objects
    if not source_path.exists():
        rel_source = source_path.relative_to(base_dir)
        raise ValueError(f"Source file does not exist: {rel_source}")

    if source_path.is_dir():
        rel_source = source_path.relative_to(base_dir)
        raise ValueError(f"Source is a directory: {rel_source}")

    if dest_path.exists():
        rel_dest = dest_path.relative_to(base_dir)
        raise ValueError(f"Destination already exists: {rel_dest}")

    # Create destination directory if needed
    dest_path.parent.mkdir(parents=True, exist_ok=True)

    # Copy file
    shutil.copy2(source_path, dest_path)

    rel_source = source_path.relative_to(base_dir)
    rel_dest = dest_path.relative_to(base_dir)
    return f"Successfully copied {rel_source} to {rel_dest}"


@mcp.tool()
@requires_scopes("write:files")
@validates_paths("source_path", "dest_path")
def move_file(
    source_path: Annotated[str, "Source file path"],
    dest_path: Annotated[str, "Destination file path"],
) -> str:
    """Move/rename files"""
    # Both paths are now validated Path objects
    if not source_path.exists():
        rel_source = source_path.relative_to(base_dir)
        raise ValueError(f"Source file does not exist: {rel_source}")

    if source_path.is_dir():
        rel_source = source_path.relative_to(base_dir)
        raise ValueError(f"Source is a directory: {rel_source}")

    if dest_path.exists():
        rel_dest = dest_path.relative_to(base_dir)
        raise ValueError(f"Destination already exists: {rel_dest}")

    # Create destination directory if needed
    dest_path.parent.mkdir(parents=True, exist_ok=True)

    # Move file
    shutil.move(source_path, dest_path)

    rel_source = source_path.relative_to(base_dir)
    rel_dest = dest_path.relative_to(base_dir)
    return f"Successfully moved {rel_source} to {rel_dest}"


@mcp.tool()
@requires_scopes("read:files")
@validates_paths("file_path", check_extensions=False)
def get_file_info(file_path: Annotated[str, "Path to get info for"]) -> str:
    """Get file size, modified date, and permissions"""
    if not file_path.exists():
        rel_path = file_path.relative_to(base_dir)
        raise ValueError(f"File does not exist: {rel_path}")

    try:
        stat_info = file_path.stat()
        rel_path = file_path.relative_to(base_dir)

        # File type
        file_type = "directory" if file_path.is_dir() else "file"

        # Size
        if file_path.is_file():
            size = stat_info.st_size
            size_str = f"{size} bytes"
            if size > 1024:
                size_str += f" ({size / 1024:.1f} KB)"
            if size > 1024 * 1024:
                size_str += f" ({size / (1024 * 1024):.1f} MB)"
        else:
            size_str = "N/A (directory)"

        # Modified time
        modified_time = datetime.fromtimestamp(stat_info.st_mtime)
        modified_str = modified_time.strftime("%Y-%m-%d %H:%M:%S")

        # Permissions
        mode = stat_info.st_mode
        perms = stat.filemode(mode)

        return f"""File info for {rel_path}:
Type: {file_type}
Size: {size_str}
Modified: {modified_str}
Permissions: {perms}"""

    except Exception as e:
        rel_path = file_path.relative_to(base_dir)
        raise ValueError(f"Cannot get info for {rel_path}: {e}")


@mcp.tool()
@requires_scopes("read:files")
@validates_paths("file_path", check_extensions=False)
def file_exists(file_path: Annotated[str, "Path to check"]) -> str:
    """Check if file exists"""
    exists = file_path.exists()
    rel_path = file_path.relative_to(base_dir)

    if exists:
        file_type = "directory" if file_path.is_dir() else "file"
        return f"{rel_path} exists ({file_type})"
    else:
        return f"{rel_path} does not exist"


# Directory operations
@mcp.tool()
@requires_scopes("write:files")
@validates_paths("dir_path", check_extensions=False)
def create_directory(dir_path: Annotated[str, "Directory path to create"]) -> str:
    """Create folders"""
    if dir_path.exists():
        rel_path = dir_path.relative_to(base_dir)
        raise ValueError(f"Directory already exists: {rel_path}")

    # Create directory
    dir_path.mkdir(parents=True, exist_ok=True)

    rel_path = dir_path.relative_to(base_dir)
    return f"Successfully created directory: {rel_path}"


@mcp.tool()
@requires_scopes("delete:files")
@validates_paths("dir_path", check_extensions=False)
def delete_directory(
    dir_path: Annotated[str, "Directory path to delete"],
    recursive: Annotated[bool, "Delete recursively"] = False,
) -> str:
    """Remove folders"""
    if not dir_path.exists():
        rel_path = dir_path.relative_to(base_dir)
        raise ValueError(f"Directory does not exist: {rel_path}")

    if not dir_path.is_dir():
        rel_path = dir_path.relative_to(base_dir)
        raise ValueError(f"Path is not a directory: {rel_path}")

    # Check if directory is empty for non-recursive delete
    if not recursive:
        try:
            contents = list(dir_path.iterdir())
            if contents:
                rel_path = dir_path.relative_to(base_dir)
                raise ValueError(
                    f"Directory not empty: {rel_path}. Use recursive=true to force delete"
                )
        except OSError:
            pass

    # Delete directory
    if recursive:
        shutil.rmtree(dir_path)
    else:
        dir_path.rmdir()

    rel_path = dir_path.relative_to(base_dir)
    return f"Successfully deleted directory: {rel_path}"


@mcp.tool()
@requires_scopes("read:files")
@validates_paths("dir_path", check_extensions=False)
def list_files_recursive(
    dir_path: Annotated[str, "Directory path to list recursively"],
    pattern: Annotated[str, "File pattern to match (optional)"] = None,
) -> str:
    """Deep directory listing with optional pattern matching"""
    if not dir_path.exists():
        rel_path = dir_path.relative_to(base_dir)
        raise ValueError(f"Directory does not exist: {rel_path}")

    if not dir_path.is_dir():
        rel_path = dir_path.relative_to(base_dir)
        raise ValueError(f"Path is not a directory: {rel_path}")

    items = []

    # Walk through directory recursively
    for item in dir_path.rglob("*"):
        rel_path = item.relative_to(base_dir)

        # Apply pattern filter if provided
        if pattern and not item.match(pattern):
            continue

        item_type = "directory" if item.is_dir() else "file"

        # Add size info for files
        if item.is_file():
            try:
                size = item.stat().st_size
                if size > 1024 * 1024:
                    size_str = f" ({size / (1024 * 1024):.1f}MB)"
                elif size > 1024:
                    size_str = f" ({size / 1024:.1f}KB)"
                else:
                    size_str = f" ({size}B)"
                items.append(f"{item_type}: {rel_path}{size_str}")
            except (OSError, ValueError):
                items.append(f"{item_type}: {rel_path}")
        else:
            items.append(f"{item_type}: {rel_path}/")

    base_rel = dir_path.relative_to(base_dir) if dir_path != base_dir else "."
    pattern_str = f" (pattern: {pattern})" if pattern else ""

    if items:
        return f"Recursive listing of {base_rel}{pattern_str}:\n" + "\n".join(items)
    else:
        return f"No items found in {base_rel}{pattern_str}"


@mcp.tool()
@requires_scopes("write:files")
@validates_paths("source_path", "dest_path", check_extensions=False)
def move_directory(
    source_path: Annotated[str, "Source directory path"],
    dest_path: Annotated[str, "Destination directory path"],
) -> str:
    """Move folders"""
    # Both paths are now validated Path objects
    if not source_path.exists():
        rel_source = source_path.relative_to(base_dir)
        raise ValueError(f"Source directory does not exist: {rel_source}")

    if not source_path.is_dir():
        rel_source = source_path.relative_to(base_dir)
        raise ValueError(f"Source is not a directory: {rel_source}")

    if dest_path.exists():
        rel_dest = dest_path.relative_to(base_dir)
        raise ValueError(f"Destination already exists: {rel_dest}")

    # Create parent directory if needed
    dest_path.parent.mkdir(parents=True, exist_ok=True)

    # Move directory
    shutil.move(source_path, dest_path)

    rel_source = source_path.relative_to(base_dir)
    rel_dest = dest_path.relative_to(base_dir)
    return f"Successfully moved directory {rel_source} to {rel_dest}"


# Batch operations
@mcp.tool()
@requires_scopes("read:files")
def batch_read(
    file_paths_array: Annotated[list, "Array of file paths to read"],
) -> str:
    """Read multiple files at once"""
    if not file_paths_array:
        raise ValueError("File paths array cannot be empty")

    results = []
    errors = []

    for file_path_str in file_paths_array:
        try:
            # Validate path
            validated_path = validate_path(file_path_str)

            if not validated_path.exists():
                rel_path = validated_path.relative_to(base_dir)
                errors.append(f"{rel_path}: File does not exist")
                continue

            if validated_path.is_dir():
                rel_path = validated_path.relative_to(base_dir)
                errors.append(f"{rel_path}: Path is a directory")
                continue

            try:
                content = validated_path.read_text(encoding="utf-8")
                rel_path = validated_path.relative_to(base_dir)
                results.append(f"=== {rel_path} ===\n{content}")
            except UnicodeDecodeError:
                rel_path = validated_path.relative_to(base_dir)
                errors.append(f"{rel_path}: File is not text readable")

        except Exception as e:
            errors.append(f"{file_path_str}: {str(e)}")

    output_parts = []
    if results:
        output_parts.append(
            f"Successfully read {len(results)} file(s):\n\n" + "\n\n".join(results)
        )

    if errors:
        output_parts.append(f"Errors ({len(errors)}):\n" + "\n".join(errors))

    if not results and not errors:
        return "No files processed"

    return "\n\n".join(output_parts)


@mcp.tool()
@requires_scopes("write:files")
def batch_create(
    files_content_array: Annotated[list, "Array of objects with file_path and content"],
) -> str:
    """Create multiple files at once"""
    if not files_content_array:
        raise ValueError("Files content array cannot be empty")

    created = []
    errors = []

    for file_data in files_content_array:
        try:
            if (
                not isinstance(file_data, dict)
                or "file_path" not in file_data
                or "content" not in file_data
            ):
                errors.append(
                    "Invalid file data: must have 'file_path' and 'content' fields"
                )
                continue

            file_path_str = file_data["file_path"]
            content = file_data["content"]

            # Validate path and extension
            validated_path = validate_path(file_path_str)
            if not validate_file_extension(file_path_str):
                rel_path = validated_path.relative_to(base_dir)
                errors.append(f"{rel_path}: File extension not allowed")
                continue

            if validated_path.exists():
                rel_path = validated_path.relative_to(base_dir)
                errors.append(f"{rel_path}: File already exists")
                continue

            if len(content.encode("utf-8")) > MAX_FILE_SIZE:
                rel_path = validated_path.relative_to(base_dir)
                errors.append(f"{rel_path}: File size exceeds limit")
                continue

            # Create file
            validated_path.parent.mkdir(parents=True, exist_ok=True)
            validated_path.write_text(content, encoding="utf-8")

            rel_path = validated_path.relative_to(base_dir)
            created.append(f"{rel_path} ({len(content)} characters)")

        except Exception as e:
            file_path_str = (
                file_data.get("file_path", "unknown")
                if isinstance(file_data, dict)
                else "unknown"
            )
            errors.append(f"{file_path_str}: {str(e)}")

    output_parts = []
    if created:
        output_parts.append(
            f"Successfully created {len(created)} file(s):\n" + "\n".join(created)
        )

    if errors:
        output_parts.append(f"Errors ({len(errors)}):\n" + "\n".join(errors))

    if not created and not errors:
        return "No files processed"

    return "\n\n".join(output_parts)


@mcp.tool()
@requires_scopes("delete:files")
def batch_delete(
    file_paths_array: Annotated[list, "Array of file paths to delete"],
) -> str:
    """Delete multiple files at once"""
    if not file_paths_array:
        raise ValueError("File paths array cannot be empty")

    deleted = []
    errors = []

    for file_path_str in file_paths_array:
        try:
            # Validate path
            validated_path = validate_path(file_path_str)

            if not validated_path.exists():
                rel_path = validated_path.relative_to(base_dir)
                errors.append(f"{rel_path}: File does not exist")
                continue

            if validated_path.is_dir():
                rel_path = validated_path.relative_to(base_dir)
                errors.append(
                    f"{rel_path}: Cannot delete directory (use delete_directory)"
                )
                continue

            # Delete file
            validated_path.unlink()

            rel_path = validated_path.relative_to(base_dir)
            deleted.append(str(rel_path))

        except Exception as e:
            errors.append(f"{file_path_str}: {str(e)}")

    output_parts = []
    if deleted:
        output_parts.append(
            f"Successfully deleted {len(deleted)} file(s):\n" + "\n".join(deleted)
        )

    if errors:
        output_parts.append(f"Errors ({len(errors)}):\n" + "\n".join(errors))

    if not deleted and not errors:
        return "No files processed"

    return "\n\n".join(output_parts)


@mcp.tool()
@requires_scopes("read:files")
@validates_paths("directory", check_extensions=False)
def find_files(
    directory: Annotated[str, "Directory to search in"],
    name_pattern: Annotated[str, "File name pattern to match (glob pattern)"],
    content_pattern: Annotated[str, "Content pattern to search for (optional)"] = None,
) -> str:
    """Search for files by name and optionally by content"""
    if not directory.exists():
        rel_path = directory.relative_to(base_dir)
        raise ValueError(f"Directory does not exist: {rel_path}")

    if not directory.is_dir():
        rel_path = directory.relative_to(base_dir)
        raise ValueError(f"Path is not a directory: {rel_path}")

    # Find files matching name pattern
    matched_files = []
    try:
        for file_path in directory.rglob(name_pattern):
            if file_path.is_file():
                matched_files.append(file_path)
    except Exception as e:
        raise ValueError(f"Invalid name pattern: {e}")

    if not content_pattern:
        # Return name matches only
        if matched_files:
            results = []
            for file_path in matched_files:
                rel_path = file_path.relative_to(base_dir)
                try:
                    size = file_path.stat().st_size
                    if size > 1024 * 1024:
                        size_str = f" ({size / (1024 * 1024):.1f}MB)"
                    elif size > 1024:
                        size_str = f" ({size / 1024:.1f}KB)"
                    else:
                        size_str = f" ({size}B)"
                    results.append(f"{rel_path}{size_str}")
                except (OSError, ValueError):
                    results.append(str(rel_path))

            base_rel = directory.relative_to(base_dir) if directory != base_dir else "."
            return (
                f"Found {len(matched_files)} file(s) matching '{name_pattern}' in {base_rel}:\n"
                + "\n".join(results)
            )
        else:
            base_rel = directory.relative_to(base_dir) if directory != base_dir else "."
            return f"No files matching '{name_pattern}' found in {base_rel}"

    # Search content in matched files
    content_matches = []
    content_errors = []

    for file_path in matched_files:
        try:
            content = file_path.read_text(encoding="utf-8")
            lines = content.splitlines()

            matching_lines = []
            for line_num, line in enumerate(lines, 1):
                if content_pattern in line:
                    matching_lines.append(f"  {line_num}: {line}")

            if matching_lines:
                rel_path = file_path.relative_to(base_dir)
                content_matches.append(
                    f"{rel_path} ({len(matching_lines)} matches):\n"
                    + "\n".join(matching_lines)
                )

        except UnicodeDecodeError:
            rel_path = file_path.relative_to(base_dir)
            content_errors.append(f"{rel_path}: Not text readable")
        except Exception as e:
            rel_path = file_path.relative_to(base_dir)
            content_errors.append(f"{rel_path}: {str(e)}")

    output_parts = []
    base_rel = directory.relative_to(base_dir) if directory != base_dir else "."

    if content_matches:
        output_parts.append(
            f"Found content matches for '{content_pattern}' in {len(content_matches)} file(s) from {base_rel}:\n\n"
            + "\n\n".join(content_matches)
        )

    if content_errors:
        output_parts.append("Content search errors:\n" + "\n".join(content_errors))

    if not content_matches and not content_errors:
        return f"No content matches for '{content_pattern}' found in files matching '{name_pattern}' in {base_rel}"

    return "\n\n".join(output_parts)


# Diff/Comparison operations
@mcp.tool()
@requires_scopes("read:files")
@validates_paths("file1_path", "file2_path", check_extensions=False)
def compare_files(
    file1_path: Annotated[str, "First file path"],
    file2_path: Annotated[str, "Second file path"],
) -> str:
    """Compare two files for differences"""
    # Both paths are now validated Path objects
    if not file1_path.exists():
        rel_path1 = file1_path.relative_to(base_dir)
        raise ValueError(f"First file does not exist: {rel_path1}")

    if not file2_path.exists():
        rel_path2 = file2_path.relative_to(base_dir)
        raise ValueError(f"Second file does not exist: {rel_path2}")

    if file1_path.is_dir():
        rel_path1 = file1_path.relative_to(base_dir)
        raise ValueError(f"First path is a directory: {rel_path1}")

    if file2_path.is_dir():
        rel_path2 = file2_path.relative_to(base_dir)
        raise ValueError(f"Second path is a directory: {rel_path2}")

    try:
        content1 = file1_path.read_text(encoding="utf-8")
        content2 = file2_path.read_text(encoding="utf-8")
    except UnicodeDecodeError as e:
        raise ValueError(f"File is not text readable: {e}")

    rel_path1 = file1_path.relative_to(base_dir)
    rel_path2 = file2_path.relative_to(base_dir)

    # Basic comparison
    if content1 == content2:
        return f"Files are identical: {rel_path1} and {rel_path2}"

    # Calculate statistics
    lines1 = content1.splitlines()
    lines2 = content2.splitlines()

    # Count differences
    differ = difflib.SequenceMatcher(None, lines1, lines2)
    similarity = differ.ratio() * 100

    # Find basic stats
    added_lines = len(lines2) - len(lines1)

    return f"""Files differ: {rel_path1} vs {rel_path2}
Similarity: {similarity:.1f}%
Lines: {len(lines1)} vs {len(lines2)} ({added_lines:+d})
File sizes: {len(content1)} vs {len(content2)} characters

Use get_file_diff() to see detailed differences."""


@mcp.tool()
@requires_scopes("read:files")
@validates_paths("file1_path", "file2_path", check_extensions=False)
def get_file_diff(
    file1_path: Annotated[str, "First file path"],
    file2_path: Annotated[str, "Second file path"],
    max_lines=500,
    format: Annotated[str, "Diff format: 'unified', 'context', or 'ndiff'"] = "unified",
) -> str:
    """Show detailed differences between two files"""
    # Both paths are now validated Path objects
    if not file1_path.exists():
        rel_path1 = file1_path.relative_to(base_dir)
        raise ValueError(f"First file does not exist: {rel_path1}")

    if not file2_path.exists():
        rel_path2 = file2_path.relative_to(base_dir)
        raise ValueError(f"Second file does not exist: {rel_path2}")

    if file1_path.is_dir():
        rel_path1 = file1_path.relative_to(base_dir)
        raise ValueError(f"First path is a directory: {rel_path1}")

    if file2_path.is_dir():
        rel_path2 = file2_path.relative_to(base_dir)
        raise ValueError(f"Second path is a directory: {rel_path2}")

    try:
        content1 = file1_path.read_text(encoding="utf-8")
        content2 = file2_path.read_text(encoding="utf-8")
    except UnicodeDecodeError as e:
        raise ValueError(f"File is not text readable: {e}")

    rel_path1 = file1_path.relative_to(base_dir)
    rel_path2 = file2_path.relative_to(base_dir)

    # Quick identical check
    if content1 == content2:
        return f"Files are identical: {rel_path1} and {rel_path2}"

    lines1 = content1.splitlines(keepends=True)
    lines2 = content2.splitlines(keepends=True)

    # Generate diff based on format
    if format == "unified":
        diff_lines = list(
            difflib.unified_diff(
                lines1,
                lines2,
                fromfile=str(rel_path1),
                tofile=str(rel_path2),
                lineterm="",
            )
        )
    elif format == "context":
        diff_lines = list(
            difflib.context_diff(
                lines1,
                lines2,
                fromfile=str(rel_path1),
                tofile=str(rel_path2),
                lineterm="",
            )
        )
    elif format == "ndiff":
        diff_lines = list(difflib.ndiff(lines1, lines2))
    else:
        raise ValueError("Invalid format. Use 'unified', 'context', or 'ndiff'")

    if not diff_lines:
        return f"Files are identical: {rel_path1} and {rel_path2}"

    # Limit output size for very large diffs
    if len(diff_lines) > max_lines:
        diff_output = "".join(diff_lines[:max_lines])
        diff_output += f"\n... (truncated after {max_lines} lines, {len(diff_lines) - max_lines} more lines)"
    else:
        diff_output = "".join(diff_lines)

    return (
        f"Diff between {rel_path1} and {rel_path2} ({format} format):\n\n{diff_output}"
    )


# Archive operations
@mcp.tool()
@requires_scopes("write:files")
@validates_paths("zip_path")
def create_zip(
    zip_path: Annotated[str, "Path for the zip file to create"],
    source_paths: Annotated[list, "Array of file/directory paths to include"],
) -> str:
    """Create a zip archive from files and directories"""
    if not source_paths:
        raise ValueError("Source paths array cannot be empty")

    # Validate zip file extension
    if not zip_path.suffix.lower() == ".zip":
        rel_path = zip_path.relative_to(base_dir)
        raise ValueError(f"Zip file must have .zip extension: {rel_path}")

    if zip_path.exists():
        rel_path = zip_path.relative_to(base_dir)
        raise ValueError(f"Zip file already exists: {rel_path}")

    # Validate all source paths
    validated_sources = []
    for source_path_str in source_paths:
        try:
            validated_source = validate_path(source_path_str)
            if not validated_source.exists():
                rel_source = validated_source.relative_to(base_dir)
                raise ValueError(f"Source does not exist: {rel_source}")
            validated_sources.append(validated_source)
        except Exception as e:
            raise ValueError(f"Invalid source path '{source_path_str}': {e}")

    # Create zip file
    zip_path.parent.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for source_path in validated_sources:
            if source_path.is_file():
                # Add file
                rel_source = source_path.relative_to(base_dir)
                zip_file.write(source_path, rel_source)
            elif source_path.is_dir():
                # Add directory recursively
                for file_path in source_path.rglob("*"):
                    if file_path.is_file():
                        rel_source = file_path.relative_to(base_dir)
                        zip_file.write(file_path, rel_source)

    # Get created zip info
    zip_size = zip_path.stat().st_size
    rel_zip = zip_path.relative_to(base_dir)

    return f"Successfully created {rel_zip} ({zip_size} bytes) with {len(validated_sources)} source(s)"


@mcp.tool()
@requires_scopes("write:files")
@validates_paths("zip_path", check_extensions=False)
def extract_zip(
    zip_path: Annotated[str, "Path to the zip file"],
    extract_to: Annotated[str, "Directory to extract to (optional)"] = None,
) -> str:
    """Extract a zip archive"""
    if not zip_path.exists():
        rel_path = zip_path.relative_to(base_dir)
        raise ValueError(f"Zip file does not exist: {rel_path}")

    if zip_path.is_dir():
        rel_path = zip_path.relative_to(base_dir)
        raise ValueError(f"Path is a directory: {rel_path}")

    if not zip_path.suffix.lower() == ".zip":
        rel_path = zip_path.relative_to(base_dir)
        raise ValueError(f"File is not a zip archive: {rel_path}")

    # Determine extraction directory
    if extract_to:
        extract_dir = validate_path(extract_to)
    else:
        # Extract to same directory as zip file
        extract_dir = zip_path.parent

    extract_dir.mkdir(parents=True, exist_ok=True)

    try:
        with zipfile.ZipFile(zip_path, "r") as zip_file:
            # Validate all paths in archive are safe
            for member in zip_file.namelist():
                # Check for directory traversal
                if ".." in member or member.startswith("/"):
                    raise ValueError(f"Unsafe path in archive: {member}")

                # Validate extraction path
                extract_path = extract_dir / member
                try:
                    extract_path.resolve().relative_to(base_dir.resolve())
                except ValueError:
                    raise ValueError(
                        f"Archive would extract outside allowed directory: {member}"
                    )

            # Extract all files
            zip_file.extractall(extract_dir)

            # Count extracted items
            extracted_count = len(zip_file.namelist())

    except zipfile.BadZipFile:
        rel_path = zip_path.relative_to(base_dir)
        raise ValueError(f"Invalid or corrupted zip file: {rel_path}")
    except Exception as e:
        raise ValueError(f"Extraction failed: {e}")

    rel_zip = zip_path.relative_to(base_dir)
    rel_extract = extract_dir.relative_to(base_dir)

    return (
        f"Successfully extracted {rel_zip} to {rel_extract} ({extracted_count} items)"
    )


# File integrity operations
@mcp.tool()
@requires_scopes("read:files")
@validates_paths("file_path", check_extensions=False)
def get_file_hash(
    file_path: Annotated[str, "Path to calculate hash for"],
    algorithm: Annotated[
        str, "Hash algorithm: 'md5', 'sha1', 'sha256', 'sha512'"
    ] = "sha256",
) -> str:
    """Calculate file hash for integrity verification"""
    if not file_path.exists():
        rel_path = file_path.relative_to(base_dir)
        raise ValueError(f"File does not exist: {rel_path}")

    if file_path.is_dir():
        rel_path = file_path.relative_to(base_dir)
        raise ValueError(f"Path is a directory: {rel_path}")

    # Validate algorithm
    if algorithm not in ["md5", "sha1", "sha256", "sha512"]:
        raise ValueError("Invalid algorithm. Use 'md5', 'sha1', 'sha256', or 'sha512'")

    try:
        # Create hash object
        hash_obj = hashlib.new(algorithm)

        # Read file in chunks to handle large files
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_obj.update(chunk)

        file_hash = hash_obj.hexdigest()
        file_size = file_path.stat().st_size
        rel_path = file_path.relative_to(base_dir)

        return f"Hash ({algorithm}) for {rel_path}:\n{file_hash}\nFile size: {file_size} bytes"

    except Exception as e:
        rel_path = file_path.relative_to(base_dir)
        raise ValueError(f"Cannot calculate hash for {rel_path}: {e}")


# Non-destructive writing operations
@mcp.tool()
@requires_scopes("write:files")
@validates_paths("file_path")
def append_to_file(
    file_path: Annotated[str, "Path to append to"],
    content: Annotated[str, "Content to append"],
    add_newline: Annotated[bool, "Add newline before content"] = True,
) -> str:
    """Append content to end of file without overwriting"""
    if not file_path.exists():
        rel_path = file_path.relative_to(base_dir)
        raise ValueError(f"File does not exist: {rel_path}")

    if file_path.is_dir():
        rel_path = file_path.relative_to(base_dir)
        raise ValueError(f"Path is a directory: {rel_path}")

    try:
        # Read existing content to check size
        existing_content = file_path.read_text(encoding="utf-8")

        # Prepare content to append
        if add_newline and existing_content and not existing_content.endswith("\n"):
            append_content = "\n" + content
        else:
            append_content = content

        # Check total size after append
        new_total_size = len(existing_content.encode("utf-8")) + len(
            append_content.encode("utf-8")
        )
        if new_total_size > MAX_FILE_SIZE:
            raise ValueError(
                f"File size would exceed limit of {MAX_FILE_SIZE / (1024*1024):.1f}MB"
            )

        # Append to file
        with open(file_path, "a", encoding="utf-8") as f:
            f.write(append_content)

        lines_added = len(content.splitlines())
        rel_path = file_path.relative_to(base_dir)

        return f"Successfully appended {len(content)} characters ({lines_added} lines) to {rel_path}"

    except UnicodeDecodeError:
        rel_path = file_path.relative_to(base_dir)
        raise ValueError(f"File is not text readable: {rel_path}")
    except Exception as e:
        rel_path = file_path.relative_to(base_dir)
        raise ValueError(f"Cannot append to {rel_path}: {e}")


# File conversion operations
@mcp.tool()
@requires_scopes("write:files")
@validates_paths("file_path", "output_path")
def convert_to_pdf(
    file_path: Annotated[str, "Source file path to convert"],
    output_path: Annotated[str, "Output PDF file path"],
) -> str:
    """Convert text documents to PDF"""
    # Both paths are now validated Path objects
    if not file_path.exists():
        rel_source = file_path.relative_to(base_dir)
        raise ValueError(f"Source file does not exist: {rel_source}")

    if file_path.is_dir():
        rel_source = file_path.relative_to(base_dir)
        raise ValueError(f"Source is a directory: {rel_source}")

    if not output_path.suffix.lower() == ".pdf":
        rel_output = output_path.relative_to(base_dir)
        raise ValueError(f"Output file must have .pdf extension: {rel_output}")

    if output_path.exists():
        rel_output = output_path.relative_to(base_dir)
        raise ValueError(f"Output file already exists: {rel_output}")

    try:
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.units import inch

        # Read source content
        content = file_path.read_text(encoding="utf-8")
        lines = content.splitlines()

        # Create destination directory if needed
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Create PDF
        c = canvas.Canvas(str(output_path), pagesize=letter)
        width, height = letter

        # Set up text formatting
        c.setFont("Helvetica", 10)
        line_height = 12
        margin = inch
        y_position = height - margin

        for line in lines:
            # Check if we need a new page
            if y_position < margin:
                c.showPage()
                c.setFont("Helvetica", 10)
                y_position = height - margin

            # Handle long lines by wrapping
            if len(line) > 80:
                words = line.split()
                current_line = ""
                for word in words:
                    if len(current_line + " " + word) > 80:
                        c.drawString(margin, y_position, current_line)
                        y_position -= line_height
                        current_line = word
                        if y_position < margin:
                            c.showPage()
                            c.setFont("Helvetica", 10)
                            y_position = height - margin
                    else:
                        current_line = (
                            current_line + " " + word if current_line else word
                        )

                if current_line:
                    c.drawString(margin, y_position, current_line)
                    y_position -= line_height
            else:
                c.drawString(margin, y_position, line)
                y_position -= line_height

        c.save()

        pdf_size = output_path.stat().st_size
        rel_source = file_path.relative_to(base_dir)
        rel_output = output_path.relative_to(base_dir)

        return f"Successfully converted {rel_source} to PDF: {rel_output} ({pdf_size} bytes)"

    except ImportError:
        raise ValueError("PDF conversion requires reportlab: uv add reportlab")
    except UnicodeDecodeError:
        rel_source = file_path.relative_to(base_dir)
        raise ValueError(f"Source file is not text readable: {rel_source}")
    except Exception as e:
        raise ValueError(f"PDF conversion failed: {e}")


@mcp.tool()
@requires_scopes("write:files")
@validates_paths("image_path", "output_path")
def convert_image_format(
    image_path: Annotated[str, "Source image file path"],
    output_path: Annotated[str, "Output image file path"],
    format: Annotated[str, "Output format: 'JPEG', 'PNG', 'BMP', 'GIF', 'TIFF'"],
) -> str:
    """Convert image between different formats"""
    # Both paths are now validated Path objects
    if not image_path.exists():
        rel_source = image_path.relative_to(base_dir)
        raise ValueError(f"Source image does not exist: {rel_source}")

    if image_path.is_dir():
        rel_source = image_path.relative_to(base_dir)
        raise ValueError(f"Source is a directory: {rel_source}")

    if output_path.exists():
        rel_output = output_path.relative_to(base_dir)
        raise ValueError(f"Output file already exists: {rel_output}")

    # Validate format
    valid_formats = ["JPEG", "PNG", "BMP", "GIF", "TIFF"]
    format_upper = format.upper()
    if format_upper not in valid_formats:
        raise ValueError(f"Invalid format. Use: {', '.join(valid_formats)}")

    try:
        from PIL import Image

        # Open and convert image
        with Image.open(image_path) as img:
            # Handle different format requirements
            if format_upper == "JPEG" and img.mode in ("RGBA", "LA", "P"):
                # Convert to RGB for JPEG
                img = img.convert("RGB")
            elif format_upper == "PNG" and img.mode == "CMYK":
                # Convert CMYK to RGB for PNG
                img = img.convert("RGB")

            # Create destination directory if needed
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # Save in new format
            img.save(output_path, format=format_upper)

        output_size = output_path.stat().st_size
        rel_source = image_path.relative_to(base_dir)
        rel_output = output_path.relative_to(base_dir)

        return f"Successfully converted {rel_source} to {format_upper}: {rel_output} ({output_size} bytes)"

    except ImportError:
        raise ValueError("Image conversion requires Pillow: uv add pillow")
    except Exception as e:
        raise ValueError(f"Image conversion failed: {e}")


@mcp.tool()
@requires_scopes("write:files")
@validates_paths("csv_path", "json_path")
def csv_to_json(
    csv_path: Annotated[str, "Source CSV file path"],
    json_path: Annotated[str, "Output JSON file path"],
) -> str:
    """Convert CSV file to JSON format"""
    # Both paths are now validated Path objects
    if not csv_path.exists():
        rel_source = csv_path.relative_to(base_dir)
        raise ValueError(f"CSV file does not exist: {rel_source}")

    if csv_path.is_dir():
        rel_source = csv_path.relative_to(base_dir)
        raise ValueError(f"Source is a directory: {rel_source}")

    if not csv_path.suffix.lower() == ".csv":
        rel_source = csv_path.relative_to(base_dir)
        raise ValueError(f"Source file must be .csv: {rel_source}")

    if not json_path.suffix.lower() == ".json":
        rel_output = json_path.relative_to(base_dir)
        raise ValueError(f"Output file must be .json: {rel_output}")

    if json_path.exists():
        rel_output = json_path.relative_to(base_dir)
        raise ValueError(f"Output file already exists: {rel_output}")

    try:
        # Read CSV and convert to JSON
        data = []
        with open(csv_path, "r", encoding="utf-8") as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                data.append(row)

        # Create destination directory if needed
        json_path.parent.mkdir(parents=True, exist_ok=True)

        # Write JSON
        with open(json_path, "w", encoding="utf-8") as jsonfile:
            json.dump(data, jsonfile, indent=2, ensure_ascii=False)

        output_size = json_path.stat().st_size
        rel_source = csv_path.relative_to(base_dir)
        rel_output = json_path.relative_to(base_dir)

        return f"Successfully converted {rel_source} to JSON: {rel_output} ({len(data)} records, {output_size} bytes)"

    except Exception as e:
        raise ValueError(f"CSV to JSON conversion failed: {e}")


@mcp.tool()
@requires_scopes("write:files")
@validates_paths("json_path", "csv_path")
def json_to_csv(
    json_path: Annotated[str, "Source JSON file path"],
    csv_path: Annotated[str, "Output CSV file path"],
) -> str:
    """Convert JSON file to CSV format"""
    # Both paths are now validated Path objects
    if not json_path.exists():
        rel_source = json_path.relative_to(base_dir)
        raise ValueError(f"JSON file does not exist: {rel_source}")

    if json_path.is_dir():
        rel_source = json_path.relative_to(base_dir)
        raise ValueError(f"Source is a directory: {rel_source}")

    if not json_path.suffix.lower() == ".json":
        rel_source = json_path.relative_to(base_dir)
        raise ValueError(f"Source file must be .json: {rel_source}")

    if not csv_path.suffix.lower() == ".csv":
        rel_output = csv_path.relative_to(base_dir)
        raise ValueError(f"Output file must be .csv: {rel_output}")

    if csv_path.exists():
        rel_output = csv_path.relative_to(base_dir)
        raise ValueError(f"Output file already exists: {rel_output}")

    try:
        # Read JSON data
        with open(json_path, "r", encoding="utf-8") as jsonfile:
            data = json.load(jsonfile)

        # Validate JSON structure for CSV conversion
        if not isinstance(data, list):
            raise ValueError("JSON must be an array of objects for CSV conversion")

        if not data:
            raise ValueError("JSON array is empty")

        if not all(isinstance(item, dict) for item in data):
            raise ValueError("All items in JSON array must be objects")

        # Get all unique keys from all records
        all_keys = set()
        for item in data:
            all_keys.update(item.keys())

        fieldnames = sorted(all_keys)

        # Create destination directory if needed
        csv_path.parent.mkdir(parents=True, exist_ok=True)

        # Write CSV
        with open(csv_path, "w", newline="", encoding="utf-8") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(data)

        output_size = csv_path.stat().st_size
        rel_source = json_path.relative_to(base_dir)
        rel_output = csv_path.relative_to(base_dir)

        return f"Successfully converted {rel_source} to CSV: {rel_output} ({len(data)} records, {len(fieldnames)} columns, {output_size} bytes)"

    except json.JSONDecodeError as e:
        rel_source = json_path.relative_to(base_dir)
        raise ValueError(f"Invalid JSON in {rel_source}: {e}")
    except Exception as e:
        raise ValueError(f"JSON to CSV conversion failed: {e}")