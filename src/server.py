#!/usr/bin/env python3

import json
import sys
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
import hmac
import logging


def load_env_config():
    """Load configuration from .env file if it exists."""
    config = {
        "API_KEY": "secure-mcp-key-123",
        "PORT": 8082,
        "HOST": "localhost",
        "ALLOWED_PATH": "./allowed",
        "CREATE_ALLOWED_DIR": True,
        "MAX_FILE_SIZE": 10485760,  # 10MB
        "ALLOWED_EXTENSIONS": [
            ".txt",
            ".json",
            ".md",
            ".csv",
            ".log",
            ".xml",
            ".yaml",
            ".yml",
            ".conf",
            ".cfg",
        ],
        "ENABLE_SUBDIRECTORIES": True,
        "LOG_LEVEL": "INFO",
        "LOG_REQUESTS": True,
    }

    env_path = Path(__file__).parent.parent / ".env"

    if env_path.exists():
        with open(env_path, "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    key = key.strip()
                    value = value.strip()

                    # Convert values to appropriate types
                    if key == "MCP_API_KEY":
                        config["API_KEY"] = value
                    elif key == "MCP_PORT":
                        config["PORT"] = int(value)
                    elif key == "MCP_HOST":
                        config["HOST"] = value
                    elif key == "MCP_ALLOWED_PATH":
                        config["ALLOWED_PATH"] = value
                    elif key == "MCP_CREATE_ALLOWED_DIR":
                        config["CREATE_ALLOWED_DIR"] = value.lower() == "true"
                    elif key == "MCP_MAX_FILE_SIZE":
                        config["MAX_FILE_SIZE"] = int(value)
                    elif key == "MCP_ALLOWED_EXTENSIONS":
                        config["ALLOWED_EXTENSIONS"] = [
                            ext.strip() for ext in value.split(",")
                        ]
                    elif key == "MCP_ENABLE_SUBDIRECTORIES":
                        config["ENABLE_SUBDIRECTORIES"] = value.lower() == "true"
                    elif key == "MCP_LOG_LEVEL":
                        config["LOG_LEVEL"] = value
                    elif key == "MCP_LOG_REQUESTS":
                        config["LOG_REQUESTS"] = value.lower() == "true"

    return config


# Load configuration
CONFIG = load_env_config()

# Setup logging
logging.basicConfig(
    level=getattr(logging, CONFIG["LOG_LEVEL"]),
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class MCPFileServer(BaseHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        # Set base directory from config
        self.base_dir = Path(CONFIG["ALLOWED_PATH"]).resolve()
        if CONFIG["CREATE_ALLOWED_DIR"]:
            self.base_dir.mkdir(parents=True, exist_ok=True)

        self.config = CONFIG
        super().__init__(*args, **kwargs)

    def validate_api_key(self, provided_key):
        """Validate API key"""
        return hmac.compare_digest(self.config["API_KEY"], provided_key)

    def validate_file_extension(self, file_path: str) -> bool:
        """Validate file extension if restrictions are configured."""
        if not self.config["ALLOWED_EXTENSIONS"]:
            return True  # No restrictions

        file_ext = Path(file_path).suffix.lower()
        return file_ext in self.config["ALLOWED_EXTENSIONS"]

    def validate_file_size(self, content: str) -> bool:
        """Validate file size against configured limits."""
        content_size = len(content.encode("utf-8"))
        return content_size <= self.config["MAX_FILE_SIZE"]

    def log_request_info(self, method: str, path: str, success: bool = True):
        """Log request information if enabled."""
        if self.config["LOG_REQUESTS"]:
            status = "SUCCESS" if success else "FAILED"
            client_ip = self.client_address[0]
            logger.info(f"{method} {path} - {status} - {client_ip}")

    def validate_path(self, file_path):
        """Validate and resolve file path within allowed directory"""
        try:
            clean_path = file_path.lstrip("/")
            full_path = (self.base_dir / clean_path).resolve()

            if not str(full_path).startswith(str(self.base_dir)):
                raise ValueError("Path outside allowed directory")

            return full_path
        except Exception as e:
            raise ValueError(f"Invalid path: {str(e)}")

    def do_POST(self):
        """Handle POST requests"""
        try:
            self.log_request_info("POST", self.path)

            # Read request body first to get request_id if available
            content_length = int(self.headers["Content-Length"])
            post_data = self.rfile.read(content_length)

            try:
                request_data = json.loads(post_data.decode("utf-8"))
            except json.JSONDecodeError:
                self.send_error_response(-32700, "Parse error")
                return

            request_id = request_data.get("id")

            # Check API key
            api_key = self.headers.get("X-API-Key") or self.headers.get(
                "Authorization", ""
            ).replace("Bearer ", "")
            if not self.validate_api_key(api_key):
                self.log_request_info("POST", self.path, False)
                self.send_error_response(-32001, "Invalid API key", request_id)
                return

            # Handle MCP request
            response = self.handle_mcp_request(request_data)
            self.send_json_response(response)

        except Exception as e:
            print(f"Error: {e}")
            try:
                request_id = (
                    request_data.get("id") if "request_data" in locals() else None
                )
            except:
                request_id = None
            self.send_error_response(-32000, f"Internal error: {str(e)}", request_id)

    def do_GET(self):
        """Handle GET requests"""
        if self.path == "/health":
            self.send_json_response(
                {"status": "healthy", "server": "local-file-mcp-server"}
            )
        else:
            self.send_error(404)

    def handle_mcp_request(self, request_data):
        """Handle MCP protocol requests"""
        method = request_data.get("method")
        request_id = request_data.get("id")

        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": "local-file-mcp-server", "version": "1.0.0"},
                },
            }

        elif method == "tools/list":
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "tools": [
                        {
                            "name": "local_file_mcp_server",
                            "description": (
                                "Read, write, create, delete, and list local "
                                "files within the allowed directory"
                            ),
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "operation": {
                                        "type": "string",
                                        "enum": [
                                            "read",
                                            "write",
                                            "create",
                                            "delete",
                                            "list",
                                        ],
                                        "description": "The file operation to perform",
                                    },
                                    "file_path": {
                                        "type": "string",
                                        "description": "Relative path to the file within the allowed directory",
                                    },
                                    "content": {
                                        "type": "string",
                                        "description": "Content to write (for write/create operations)",
                                    },
                                },
                                "required": ["operation", "file_path"],
                            },
                        }
                    ]
                },
            }

        elif method == "tools/call":
            params = request_data.get("params", {})
            tool_name = params.get("name")
            arguments = params.get("arguments", {})

            if tool_name == "local_file_mcp_server":
                return self.execute_file_operation(request_id, arguments)
            else:
                return self.error_response(
                    request_id, -32602, f"Unknown tool: {tool_name}"
                )

        else:
            return self.error_response(
                request_id, -32601, f"Method not found: {method}"
            )

    def execute_file_operation(self, request_id, arguments):
        """Execute file operations"""
        try:
            operation = arguments.get("operation")
            file_path = arguments.get("file_path", "")
            content = arguments.get("content", "")

            if not operation or not file_path:
                return self.error_response(
                    request_id, -32602, "Operation and file_path are required"
                )

            try:
                full_path = self.validate_path(file_path)
            except ValueError as e:
                return self.error_response(request_id, -32602, str(e))

            # Validate file extension for create/write operations
            if operation in ["create", "write"] and not self.validate_file_extension(
                file_path
            ):
                allowed_ext = ", ".join(self.config["ALLOWED_EXTENSIONS"])
                return self.error_response(
                    request_id,
                    -32602,
                    f"File extension not allowed. Allowed: {allowed_ext}",
                )

            # Validate file size for create/write operations
            if (
                operation in ["create", "write"]
                and content
                and not self.validate_file_size(content)
            ):
                max_size = self.config["MAX_FILE_SIZE"] / (1024 * 1024)  # Convert to MB
                return self.error_response(
                    request_id, -32602, f"File size exceeds limit of {max_size:.1f}MB"
                )

            if operation == "read":
                if not full_path.exists():
                    return self.error_response(
                        request_id, -32000, f"File does not exist: {file_path}"
                    )
                if full_path.is_dir():
                    return self.error_response(
                        request_id, -32000, f"Path is a directory: {file_path}"
                    )

                try:
                    file_content = full_path.read_text(encoding="utf-8")
                    result = f"File: {file_path}\n\n{file_content}"
                except UnicodeDecodeError:
                    return self.error_response(
                        request_id, -32000, f"File is not text readable: {file_path}"
                    )

            elif operation == "write":
                if not full_path.exists():
                    return self.error_response(
                        request_id, -32000, f"File does not exist: {file_path}"
                    )

                full_path.write_text(content, encoding="utf-8")
                result = f"Successfully wrote {len(content)} characters to {file_path}"

            elif operation == "create":
                if full_path.exists():
                    return self.error_response(
                        request_id, -32000, f"File already exists: {file_path}"
                    )

                full_path.parent.mkdir(parents=True, exist_ok=True)
                full_path.write_text(content, encoding="utf-8")
                result = (
                    f"Successfully created {file_path} with {len(content)} characters"
                )

            elif operation == "delete":
                if not full_path.exists():
                    return self.error_response(
                        request_id, -32000, f"File does not exist: {file_path}"
                    )
                if full_path.is_dir():
                    return self.error_response(
                        request_id, -32000, f"Cannot delete directory: {file_path}"
                    )

                full_path.unlink()
                result = f"Successfully deleted {file_path}"

            elif operation == "list":
                target_path = full_path if file_path != "." else self.base_dir

                if not target_path.exists():
                    return self.error_response(
                        request_id, -32000, f"Directory does not exist: {file_path}"
                    )
                if target_path.is_file():
                    return self.error_response(
                        request_id, -32000, f"Path is a file: {file_path}"
                    )

                items = []
                for item in sorted(target_path.iterdir()):
                    rel_path = item.relative_to(self.base_dir)
                    item_type = "directory" if item.is_dir() else "file"
                    items.append(f"{item_type}: {rel_path}")

                result = f"Contents of allowed/{file_path}:\n" + "\n".join(items)

            else:
                return self.error_response(
                    request_id, -32602, f"Unknown operation: {operation}"
                )

            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {"content": [{"type": "text", "text": result}]},
            }

        except Exception as e:
            return self.error_response(
                request_id, -32000, f"File operation failed: {str(e)}"
            )

    def error_response(self, request_id, code, message):
        """Create error response"""
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {"code": code, "message": message},
        }

    def send_json_response(self, data):
        """Send JSON response"""
        response = json.dumps(data).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(response)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
        self.send_header(
            "Access-Control-Allow-Headers", "Content-Type, X-API-Key, Authorization"
        )
        self.end_headers()
        self.wfile.write(response)

    def send_error_response(self, code, message, request_id=None):
        """Send error response"""
        error_data = self.error_response(request_id, code, message)
        self.send_json_response(error_data)

    def do_OPTIONS(self):
        """Handle OPTIONS requests for CORS"""
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
        self.send_header(
            "Access-Control-Allow-Headers", "Content-Type, X-API-Key, Authorization"
        )
        self.end_headers()


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Local File MCP Server with .env support"
    )
    parser.add_argument(
        "--port", type=int, help=f'Port to listen on (default: {CONFIG["PORT"]})'
    )
    parser.add_argument("--host", help=f'Host to bind to (default: {CONFIG["HOST"]})')
    parser.add_argument("--api-key", help="API key for authentication")

    args = parser.parse_args()

    # Override config with command line args if provided
    host = args.host or CONFIG["HOST"]
    port = args.port or CONFIG["PORT"]
    if args.api_key:
        CONFIG["API_KEY"] = args.api_key

    # Show startup information
    print("🚀 Local File MCP Server")
    print("=" * 50)
    print(f"📁 Allowed directory: {Path(CONFIG['ALLOWED_PATH']).resolve()}")
    print(f"🔑 API Key: {CONFIG['API_KEY'][:8]}{'*' * (len(CONFIG['API_KEY']) - 8)}")
    print(f"🌐 Server: http://{host}:{port}")
    print(f"❤️  Health check: http://{host}:{port}/health")
    print(f"📝 Max file size: {CONFIG['MAX_FILE_SIZE'] / (1024*1024):.1f}MB")
    print(
        f"📄 Allowed extensions: {', '.join(CONFIG['ALLOWED_EXTENSIONS']) if CONFIG['ALLOWED_EXTENSIONS'] else 'All'}"
    )
    print(
        f"🗂️  Subdirectories: {'Enabled' if CONFIG['ENABLE_SUBDIRECTORIES'] else 'Disabled'}"
    )
    print(
        f"📊 Logging: {CONFIG['LOG_LEVEL']} {'(requests logged)' if CONFIG['LOG_REQUESTS'] else ''}"
    )

    # Create server
    server = HTTPServer((host, port), MCPFileServer)

    try:
        print(f"\n✅ Server running on {host}:{port}")
        print("Press Ctrl+C to stop the server")
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 Server shutting down...")
        server.shutdown()
    except OSError as e:
        if e.errno == 48:  # Address already in use
            print(f"❌ Error: Port {port} is already in use")
            print(
                f"Try using a different port: python3 {sys.argv[0]} --port {port + 1}"
            )
        else:
            print(f"❌ Server error: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        logger.error(f"Server startup failed: {e}")


if __name__ == "__main__":
    main()
