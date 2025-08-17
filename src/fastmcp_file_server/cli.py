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
    ignore_keys = False

    # Parse command line arguments
    args = sys.argv[1:]
    i = 0
    while i < len(args):
        if args[i] == "--port":
            try:
                if i + 1 < len(args):
                    port = int(args[i + 1])
                    i += 2
                else:
                    print("Error: --port requires a value", file=sys.stderr)
                    sys.exit(1)
            except ValueError:
                print("Error: Invalid port number", file=sys.stderr)
                sys.exit(1)
        elif args[i] == "--ignore-keys":
            ignore_keys = True
            i += 1
        elif args[i] == "--help" or args[i] == "-h":
            print("FastMCP File Server - HTTP Mode", file=sys.stderr)
            print("", file=sys.stderr)
            print("Usage: fastmcp-file-server-http [OPTIONS]", file=sys.stderr)
            print("", file=sys.stderr)
            print("Options:", file=sys.stderr)
            print("  --port PORT      HTTP server port (default: 8082)", file=sys.stderr)
            print("  --ignore-keys    Skip authentication warning (not recommended)", file=sys.stderr)
            print("  --help, -h       Show this help message", file=sys.stderr)
            print("", file=sys.stderr)
            print("Environment Variables:", file=sys.stderr)
            print("  MCP_ALLOWED_PATH     Safe directory for file operations", file=sys.stderr)
            print("  MCP_HTTP_PORT        HTTP server port", file=sys.stderr)
            print("  MCP_READ_KEY         Read-only access token", file=sys.stderr)
            print("  MCP_WRITE_KEY        Read/write access token", file=sys.stderr)
            print("  MCP_ADMIN_KEY        Admin access token", file=sys.stderr)
            sys.exit(0)
        else:
            print(f"Error: Unknown argument '{args[i]}'", file=sys.stderr)
            print("Use --help for usage information", file=sys.stderr)
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
        print("\n" + "="*60, file=sys.stderr)
        print("⚠️  SECURITY WARNING: NO AUTHENTICATION CONFIGURED", file=sys.stderr)
        print("="*60, file=sys.stderr)
        print("", file=sys.stderr)
        print("The HTTP server will run WITHOUT authentication!", file=sys.stderr)
        print("This means ANYONE on the network can access your files.", file=sys.stderr)
        print("", file=sys.stderr)
        print("For security, please set at least one of:", file=sys.stderr)
        print("  export MCP_READ_KEY='your-read-token'", file=sys.stderr)
        print("  export MCP_WRITE_KEY='your-write-token'", file=sys.stderr)
        print("  export MCP_ADMIN_KEY='your-admin-token'", file=sys.stderr)
        print("", file=sys.stderr)
        print("Generate secure tokens with: openssl rand -hex 32", file=sys.stderr)
        print("", file=sys.stderr)
        if not ignore_keys:
            print("To bypass this warning (NOT RECOMMENDED), use: --ignore-keys", file=sys.stderr)
            print("="*60, file=sys.stderr)
            print("", file=sys.stderr)
            
            try:
                response = input("Continue without authentication? [y/N]: ").strip().lower()
                if response not in ['y', 'yes']:
                    print("Aborting for security. Please configure authentication.", file=sys.stderr)
                    sys.exit(1)
            except (KeyboardInterrupt, EOFError):
                print("\nAborting for security.", file=sys.stderr)
                sys.exit(1)
        else:
            print("WARNING BYPASSED: Running without authentication (--ignore-keys)", file=sys.stderr)
        print("="*60, file=sys.stderr)

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
