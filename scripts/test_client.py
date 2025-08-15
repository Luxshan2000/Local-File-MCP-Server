#!/usr/bin/env python3
"""
Interactive demo client for FastMCP File Server
Demonstrates how to interact with the server programmatically via stdio
"""

import asyncio
import json
import subprocess
import sys
from pathlib import Path


class FastMCPDemoClient:
    """Demo client for FastMCP server"""
    
    def __init__(self):
        # Find the virtual environment python
        project_root = Path(__file__).parent.parent
        self.venv_python = project_root / "venv" / "bin" / "python"
        self.server_script = project_root / "src" / "fastmcp_server.py"
        self.process = None
        self.request_id = 1
    
    async def start_server(self):
        """Start the FastMCP server process"""
        self.process = await asyncio.create_subprocess_exec(
            str(self.venv_python), str(self.server_script),
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL  # Ignore stderr to avoid parsing issues
        )
    
    async def stop_server(self):
        """Stop the server process"""
        if self.process:
            self.process.terminate()
            await self.process.wait()
    
    async def send_request(self, method, params=None):
        """Send JSON-RPC request"""
        request = {
            "jsonrpc": "2.0",
            "id": self.request_id,
            "method": method
        }
        if params:
            request["params"] = params
        
        self.request_id += 1
        
        # Send request
        request_json = json.dumps(request) + "\n"
        self.process.stdin.write(request_json.encode())
        await self.process.stdin.drain()
        
        # Read response
        response_line = await self.process.stdout.readline()
        return json.loads(response_line.decode().strip())
    
    async def send_notification(self, method, params=None):
        """Send JSON-RPC notification"""
        notification = {
            "jsonrpc": "2.0",
            "method": method
        }
        if params:
            notification["params"] = params
        
        notification_json = json.dumps(notification) + "\n"
        self.process.stdin.write(notification_json.encode())
        await self.process.stdin.drain()


async def demo_operations():
    """Demonstrate various file operations"""
    print("🚀 FastMCP File Server Demo")
    print("=" * 50)
    
    client = FastMCPDemoClient()
    
    try:
        await client.start_server()
        
        # 1. Initialize
        print("1. Initialize MCP Connection")
        init_result = await client.send_request("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "demo-client", "version": "1.0.0"}
        })
        if "result" in init_result:
            print(f"   Protocol Version: {init_result['result']['protocolVersion']}")
            print(f"   Server: {init_result['result']['serverInfo']['name']}")
        else:
            print(f"   Error: {init_result.get('error', 'Unknown error')}")
        print()
        
        # Send initialized notification
        await client.send_notification("notifications/initialized")
        
        # 2. List tools
        print("2. List Available Tools")
        tools = await client.send_request("tools/list", {})
        if "result" in tools:
            for tool in tools["result"]["tools"]:
                print(f"   Tool: {tool['name']}")
                print(f"   Description: {tool['description']}")
        else:
            print(f"   Error: {tools.get('error', 'Unknown error')}")
        print()
        
        # 3. Create file
        print("3. Create Test File")
        create_result = await client.send_request("tools/call", {
            "name": "create_file",
            "arguments": {
                "file_path": "demo.txt",
                "content": "Hello from FastMCP Demo!"
            }
        })
        if "result" in create_result:
            print(f"   Success: {create_result['result']['content'][0]['text']}")
        else:
            print(f"   Error: {create_result.get('error', 'Unknown error')}")
        print()
        
        # 4. Read file
        print("4. Read Test File")
        read_result = await client.send_request("tools/call", {
            "name": "read_file",
            "arguments": {"file_path": "demo.txt"}
        })
        if "result" in read_result:
            content = read_result["result"]["content"][0]["text"]
            print(f"   Content:\n{content}")
        else:
            print(f"   Error: {read_result.get('error', 'Unknown error')}")
        print()
        
        # 5. Update file
        print("5. Update Test File")
        write_result = await client.send_request("tools/call", {
            "name": "write_file",
            "arguments": {
                "file_path": "demo.txt",
                "content": "Updated content via FastMCP!"
            }
        })
        if "result" in write_result:
            print(f"   Success: {write_result['result']['content'][0]['text']}")
        else:
            print(f"   Error: {write_result.get('error', 'Unknown error')}")
        print()
        
        # 6. List files
        print("6. List Files")
        list_result = await client.send_request("tools/call", {
            "name": "list_files",
            "arguments": {}
        })
        if "result" in list_result:
            print(f"   Files:\n{list_result['result']['content'][0]['text']}")
        else:
            print(f"   Error: {list_result.get('error', 'Unknown error')}")
        print()
        
        # 7. Delete file
        print("7. Delete Test File")
        delete_result = await client.send_request("tools/call", {
            "name": "delete_file",
            "arguments": {"file_path": "demo.txt"}
        })
        if "result" in delete_result:
            print(f"   Success: {delete_result['result']['content'][0]['text']}")
        else:
            print(f"   Error: {delete_result.get('error', 'Unknown error')}")
        print()
        
        print("✅ Demo completed successfully!")
        
    except Exception as e:
        print(f"❌ Demo failed: {e}")
        sys.exit(1)
    
    finally:
        await client.stop_server()


def main():
    """Main function"""
    asyncio.run(demo_operations())


if __name__ == "__main__":
    main()
