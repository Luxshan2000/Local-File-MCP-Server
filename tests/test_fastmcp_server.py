import asyncio
import json
import sys
from pathlib import Path


class FastMCPTestClient:
    """Test client for FastMCP server"""
    
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
        """Send JSON-RPC notification (no response expected)"""
        notification = {
            "jsonrpc": "2.0",
            "method": method
        }
        if params:
            notification["params"] = params
        
        # Send notification
        notification_json = json.dumps(notification) + "\n"
        self.process.stdin.write(notification_json.encode())
        await self.process.stdin.drain()


async def test_server_initialization():
    """Test server initialization"""
    client = FastMCPTestClient()
    
    try:
        await client.start_server()
        
        # Test initialization
        init_response = await client.send_request("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {
                "name": "test-client",
                "version": "1.0.0"
            }
        })
        
        assert "result" in init_response
        assert init_response["result"]["serverInfo"]["name"] == "Local File Server"
        
        # Send initialized notification
        await client.send_notification("notifications/initialized")
        
        print("Server initialization test passed")
        return True
        
    except Exception as e:
        print(f"Server initialization test failed: {e}")
        return False
    
    finally:
        await client.stop_server()


async def test_tools_list():
    """Test tools listing"""
    client = FastMCPTestClient()
    
    try:
        await client.start_server()
        
        # Initialize
        await client.send_request("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "test-client", "version": "1.0.0"}
        })
        await client.send_notification("notifications/initialized")
        
        # Test tools/list
        tools_response = await client.send_request("tools/list", {})
        
        assert "result" in tools_response
        tools = tools_response["result"]["tools"]
        tool_names = [tool["name"] for tool in tools]
        
        expected_tools = ["create_file", "read_file", "write_file", "delete_file", "list_files"]
        for expected_tool in expected_tools:
            assert expected_tool in tool_names, f"Missing tool: {expected_tool}"
        
        print("Tools list test passed")
        return True
        
    except Exception as e:
        print(f"Tools list test failed: {e}")
        return False
    
    finally:
        await client.stop_server()


async def test_file_operations():
    """Test complete file operations workflow"""
    client = FastMCPTestClient()
    
    try:
        await client.start_server()
        
        # Initialize
        await client.send_request("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "test-client", "version": "1.0.0"}
        })
        await client.send_notification("notifications/initialized")
        
        test_file = "test_operations.txt"
        test_content = "Hello FastMCP Test!"
        updated_content = "Updated FastMCP Test!"
        
        # 1. Create file
        create_response = await client.send_request("tools/call", {
            "name": "create_file",
            "arguments": {
                "file_path": test_file,
                "content": test_content
            }
        })
        assert "result" in create_response
        assert "Successfully created" in create_response["result"]["content"][0]["text"]
        
        # 2. Read file
        read_response = await client.send_request("tools/call", {
            "name": "read_file",
            "arguments": {
                "file_path": test_file
            }
        })
        assert "result" in read_response
        assert test_content in read_response["result"]["content"][0]["text"]
        
        # 3. Write file (update)
        write_response = await client.send_request("tools/call", {
            "name": "write_file",
            "arguments": {
                "file_path": test_file,
                "content": updated_content
            }
        })
        assert "result" in write_response
        assert "Successfully wrote" in write_response["result"]["content"][0]["text"]
        
        # 4. Read updated file
        read_updated_response = await client.send_request("tools/call", {
            "name": "read_file",
            "arguments": {
                "file_path": test_file
            }
        })
        assert "result" in read_updated_response
        assert updated_content in read_updated_response["result"]["content"][0]["text"]
        
        # 5. List files
        list_response = await client.send_request("tools/call", {
            "name": "list_files",
            "arguments": {}
        })
        assert "result" in list_response
        assert test_file in list_response["result"]["content"][0]["text"]
        
        # 6. Delete file
        delete_response = await client.send_request("tools/call", {
            "name": "delete_file",
            "arguments": {
                "file_path": test_file
            }
        })
        assert "result" in delete_response
        assert "Successfully deleted" in delete_response["result"]["content"][0]["text"]
        
        print("File operations test passed")
        return True
        
    except Exception as e:
        print(f"File operations test failed: {e}")
        return False
    
    finally:
        await client.stop_server()


async def test_error_handling():
    """Test error handling"""
    client = FastMCPTestClient()
    
    try:
        await client.start_server()
        
        # Initialize
        await client.send_request("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "test-client", "version": "1.0.0"}
        })
        await client.send_notification("notifications/initialized")
        
        # Test reading non-existent file
        read_response = await client.send_request("tools/call", {
            "name": "read_file",
            "arguments": {
                "file_path": "nonexistent.txt"
            }
        })
        assert "error" in read_response or "does not exist" in str(read_response)
        
        # Test path traversal protection
        traversal_response = await client.send_request("tools/call", {
            "name": "read_file",
            "arguments": {
                "file_path": "../../../etc/passwd"
            }
        })
        assert "error" in traversal_response or "outside allowed directory" in str(traversal_response)
        
        print("Error handling test passed")
        return True
        
    except Exception as e:
        print(f"Error handling test failed: {e}")
        return False
    
    finally:
        await client.stop_server()


async def run_all_tests():
    """Run all tests"""
    print("Running FastMCP Server Test Suite")
    print("=" * 40)
    
    tests = [
        test_server_initialization,
        test_tools_list,
        test_file_operations,
        test_error_handling
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if await test():
            passed += 1
        print()  # Add spacing between tests
    
    print(f"Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("All tests passed!")
        return True
    else:
        print("Some tests failed!")
        return False


def main():
    """Main test function"""
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()