import sys
import os
from pathlib import Path


def main():
    """Main entry point for stdio mode."""
    # Add the package directory to Python path
    package_dir = Path(__file__).parent
    if str(package_dir) not in sys.path:
        sys.path.insert(0, str(package_dir))

    from .server import mcp

    print("Starting FastMCP File Server (stdio mode)", file=sys.stderr)
    print("Allowed path:", os.getenv("MCP_ALLOWED_PATH", "./allowed"), file=sys.stderr)

    # Run in stdio mode for MCP clients like Claude Desktop
    try:
        mcp.run()
    except KeyboardInterrupt:
        print("\nServer stopped by user", file=sys.stderr)
    except Exception as e:
        print(f"Server error: {e}", file=sys.stderr)
        sys.exit(1)


def main_http():
    """Main entry point for HTTP mode."""
    # Add the package directory to Python path
    package_dir = Path(__file__).parent
    if str(package_dir) not in sys.path:
        sys.path.insert(0, str(package_dir))

    from .server import mcp, HTTP_PORT, tokens

    port = HTTP_PORT

    # Check for port argument
    if "--port" in sys.argv:
        try:
            port_idx = sys.argv.index("--port")
            if port_idx + 1 < len(sys.argv):
                port = int(sys.argv[port_idx + 1])
        except (ValueError, IndexError):
            print("Error: Invalid port number", file=sys.stderr)
            sys.exit(1)

    print(f"Starting FastMCP HTTP server on port {port}", file=sys.stderr)
    print("Allowed path:", os.getenv("MCP_ALLOWED_PATH", "./allowed"), file=sys.stderr)

    if tokens:
        print("Multi-tier authentication enabled", file=sys.stderr)
        print(
            "Configure tokens using: MCP_READ_KEY, MCP_WRITE_KEY, MCP_ADMIN_KEY",
            file=sys.stderr,
        )
    else:
        print(
            "Warning: No authentication configured. Set MCP_ADMIN_KEY for security.",
            file=sys.stderr,
        )

    try:
        mcp.run(transport="http", port=port)
    except KeyboardInterrupt:
        print("\nServer stopped by user", file=sys.stderr)
    except Exception as e:
        print(f"Server error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "http":
        main_http()
    else:
        main()
