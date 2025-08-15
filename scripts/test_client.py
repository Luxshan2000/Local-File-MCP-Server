#!/usr/bin/env python3
"""
Test client for MCP File Server
Demonstrates how to interact with the server programmatically
"""

import requests
import sys


class MCPClient:
    """Simple MCP client for testing the file server"""

    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.headers = {"Content-Type": "application/json", "X-API-Key": api_key}
        self.request_id = 1

    def _make_request(self, method: str, params: dict = None):
        """Make a JSON-RPC request to the server"""
        data = {"jsonrpc": "2.0", "id": self.request_id, "method": method}
        if params:
            data["params"] = params

        self.request_id += 1

        try:
            response = requests.post(
                f"{self.base_url}/mcp", json=data, headers=self.headers
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"error": f"Request failed: {e}"}

    def health_check(self):
        """Check server health"""
        try:
            response = requests.get(f"{self.base_url}/health")
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"error": f"Health check failed: {e}"}

    def initialize(self):
        """Initialize MCP connection"""
        return self._make_request("initialize")

    def list_tools(self):
        """List available tools"""
        return self._make_request("tools/list")

    def create_file(self, file_path: str, content: str):
        """Create a new file"""
        params = {
            "name": "local_file_mcp_server",
            "arguments": {
                "operation": "create",
                "file_path": file_path,
                "content": content,
            },
        }
        return self._make_request("tools/call", params)

    def read_file(self, file_path: str):
        """Read a file"""
        params = {
            "name": "local_file_mcp_server",
            "arguments": {"operation": "read", "file_path": file_path},
        }
        return self._make_request("tools/call", params)

    def write_file(self, file_path: str, content: str):
        """Write to an existing file"""
        params = {
            "name": "local_file_mcp_server",
            "arguments": {
                "operation": "write",
                "file_path": file_path,
                "content": content,
            },
        }
        return self._make_request("tools/call", params)

    def delete_file(self, file_path: str):
        """Delete a file"""
        params = {
            "name": "local_file_mcp_server",
            "arguments": {"operation": "delete", "file_path": file_path},
        }
        return self._make_request("tools/call", params)

    def list_files(self, directory_path: str = "."):
        """List files in directory"""
        params = {
            "name": "local_file_mcp_server",
            "arguments": {"operation": "list", "file_path": directory_path},
        }
        return self._make_request("tools/call", params)


def demo_operations(client: MCPClient):
    """Demonstrate various file operations"""
    print("🚀 MCP File Server Demo")
    print("=" * 50)

    # Health check
    print("1. Health Check")
    health = client.health_check()
    print(f"   Status: {health.get('status', 'Error')}")
    print()

    # Initialize
    print("2. Initialize MCP Connection")
    init_result = client.initialize()
    if "result" in init_result:
        print(f"   Protocol Version: {init_result['result']['protocolVersion']}")
        print(f"   Server: {init_result['result']['serverInfo']['name']}")
    else:
        print(f"   Error: {init_result.get('error', 'Unknown error')}")
    print()

    # List tools
    print("3. List Available Tools")
    tools = client.list_tools()
    if "result" in tools:
        for tool in tools["result"]["tools"]:
            print(f"   Tool: {tool['name']}")
            print(f"   Description: {tool['description']}")
    else:
        print(f"   Error: {tools.get('error', 'Unknown error')}")
    print()

    # Create file
    print("4. Create Test File")
    create_result = client.create_file("demo.txt", "Hello from MCP Client!")
    if "result" in create_result:
        print(f"   Success: {create_result['result']['content'][0]['text']}")
    else:
        print(f"   Error: {create_result.get('error', 'Unknown error')}")
    print()

    # Read file
    print("5. Read Test File")
    read_result = client.read_file("demo.txt")
    if "result" in read_result:
        content = read_result["result"]["content"][0]["text"]
        print(f"   Content: {content}")
    else:
        print(f"   Error: {read_result.get('error', 'Unknown error')}")
    print()

    # Write to file
    print("6. Update Test File")
    write_result = client.write_file("demo.txt", "Updated content via MCP!")
    if "result" in write_result:
        print(f"   Success: {write_result['result']['content'][0]['text']}")
    else:
        print(f"   Error: {write_result.get('error', 'Unknown error')}")
    print()

    # List files
    print("7. List Files")
    list_result = client.list_files()
    if "result" in list_result:
        print(f"   Files:\n{list_result['result']['content'][0]['text']}")
    else:
        print(f"   Error: {list_result.get('error', 'Unknown error')}")
    print()

    # Delete file
    print("8. Delete Test File")
    delete_result = client.delete_file("demo.txt")
    if "result" in delete_result:
        print(f"   Success: {delete_result['result']['content'][0]['text']}")
    else:
        print(f"   Error: {delete_result.get('error', 'Unknown error')}")
    print()

    print("✅ Demo completed!")


def main():
    """Main function"""
    if len(sys.argv) < 3:
        print("Usage: python3 test_client.py <server_url> <api_key>")
        print("Example: python3 test_client.py http://localhost:8082 your-api-key")
        sys.exit(1)

    server_url = sys.argv[1]
    api_key = sys.argv[2]

    client = MCPClient(server_url, api_key)
    demo_operations(client)


if __name__ == "__main__":
    main()
