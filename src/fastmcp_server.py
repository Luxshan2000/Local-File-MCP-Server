import os
import re
import shutil
import stat
from datetime import datetime
from pathlib import Path
from typing import Annotated
from functools import wraps

from fastmcp import FastMCP
from fastmcp.server.auth import StaticTokenVerifier
from fastmcp.server.dependencies import get_access_token
from dotenv import load_dotenv

load_dotenv()
# Configuration from environment
ALLOWED_PATH = os.getenv("MCP_ALLOWED_PATH", "./allowed")
MAX_FILE_SIZE = int(os.getenv("MCP_MAX_FILE_SIZE", "10485760"))  # 10MB
ALLOWED_EXTENSIONS = os.getenv(
    "MCP_ALLOWED_EXTENSIONS", ".txt,.json,.md,.csv,.log,.xml,.yaml,.yml,.conf,.cfg"
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


def validates_path_and_extension(
    path_param: str = "file_path", check_extension: bool = True
):
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
                raise ValueError(
                    f"File extension not allowed. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
                )

            # Update the path in args or kwargs
            if path_param in kwargs:
                kwargs[path_param] = validated_path
                return func(*args, **kwargs)
            else:
                new_args = (validated_path,) + args[1:]
                return func(*new_args, **kwargs)

        return wrapper

    return decorator


def validates_two_paths(
    source_param: str = "source_path",
    dest_param: str = "dest_path",
    check_extensions: bool = True,
):
    """Decorator to validate both source and destination paths"""

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Validate source path (first parameter)
            if len(args) > 0:
                source_value = args[0]
            elif source_param in kwargs:
                source_value = kwargs[source_param]
            else:
                raise ValueError(f"Source parameter '{source_param}' not found")

            validated_source = validate_path(source_value)

            # Validate destination path (second parameter)
            if len(args) > 1:
                dest_value = args[1]
            elif dest_param in kwargs:
                dest_value = kwargs[dest_param]
            else:
                raise ValueError(f"Destination parameter '{dest_param}' not found")

            validated_dest = validate_path(dest_value)

            # Validate extensions if required
            if check_extensions:
                if not validate_file_extension(dest_value):
                    raise ValueError(
                        f"Destination file extension not allowed. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
                    )

            # Update paths in args or kwargs
            if source_param in kwargs and dest_param in kwargs:
                kwargs[source_param] = validated_source
                kwargs[dest_param] = validated_dest
                return func(*args, **kwargs)
            else:
                new_args = (validated_source, validated_dest) + args[2:]
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
@validates_path_and_extension()
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
@validates_path_and_extension(check_extension=False)
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
@validates_path_and_extension()
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
@validates_path_and_extension()
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
@validates_path_and_extension()
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
@validates_path_and_extension()
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
@validates_path_and_extension(check_extension=False)
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
@validates_path_and_extension()
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
@validates_path_and_extension()
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
@validates_two_paths()
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
@validates_two_paths()
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
@validates_path_and_extension(check_extension=False)
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
@validates_path_and_extension(check_extension=False)
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
@validates_path_and_extension("dir_path", check_extension=False)
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
@validates_path_and_extension("dir_path", check_extension=False)
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
@validates_path_and_extension("dir_path", check_extension=False)
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
@validates_two_paths("source_path", "dest_path", check_extensions=False)
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


if __name__ == "__main__":
    import sys

    # Check if HTTP flag is provided
    if "--http" in sys.argv:
        port = HTTP_PORT
        if "--port" in sys.argv:
            port_idx = sys.argv.index("--port")
            if port_idx + 1 < len(sys.argv):
                port = int(sys.argv[port_idx + 1])

        print(f"Starting FastMCP HTTP server on port {port}")
        if tokens:
            print("Multi-tier authentication enabled")
            print("Configure tokens using: MCP_READ_KEY, MCP_WRITE_KEY, MCP_ADMIN_KEY")

        mcp.run(transport="http", port=port)
    else:
        # Default to stdio for MCP clients like Claude Desktop
        mcp.run()
