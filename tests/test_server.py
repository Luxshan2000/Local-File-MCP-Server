#!/usr/bin/env python3
"""
Test suite for MCP File Server
"""

import unittest
import tempfile
import shutil
import sys
from pathlib import Path
from unittest.mock import patch
import threading
import time
import requests
from http.server import HTTPServer

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from server import load_env_config, MCPFileServer  # noqa: E402


class TestMCPFileServer(unittest.TestCase):
    """Test MCP File Server functionality"""

    def setUp(self):
        """Set up test environment"""
        # Create temporary directory for tests
        self.test_dir = tempfile.mkdtemp()
        self.allowed_dir = Path(self.test_dir) / "allowed"
        self.allowed_dir.mkdir(exist_ok=True)

        # Mock config for testing
        self.test_config = {
            "API_KEY": "test-api-key-123",
            "PORT": 8083,
            "HOST": "localhost",
            "ALLOWED_PATH": str(self.allowed_dir),
            "CREATE_ALLOWED_DIR": True,
            "MAX_FILE_SIZE": 1024 * 1024,  # 1MB for tests
            "ALLOWED_EXTENSIONS": [".txt", ".json", ".md"],
            "ENABLE_SUBDIRECTORIES": True,
            "LOG_LEVEL": "ERROR",  # Reduce noise in tests
            "LOG_REQUESTS": False,
        }

        # Start patching CONFIG and keep it active
        self.config_patcher = patch("server.CONFIG", self.test_config)
        self.config_patcher.start()

        # Start test server
        self.server = HTTPServer(("localhost", 8083), MCPFileServer)
        self.server_thread = threading.Thread(target=self.server.serve_forever)
        self.server_thread.daemon = True
        self.server_thread.start()
        time.sleep(0.1)  # Give server time to start

    def tearDown(self):
        """Clean up test environment"""
        self.server.shutdown()
        self.server.server_close()
        self.config_patcher.stop()
        # shutil.rmtree(self.test_dir, ignore_errors=True)

    def make_request(self, data, api_key="test-api-key-123"):
        """Helper to make MCP requests"""
        headers = {"Content-Type": "application/json", "X-API-Key": api_key}
        response = requests.post(
            "http://localhost:8083/mcp", json=data, headers=headers
        )
        return response.json()

    def test_health_check(self):
        """Test health check endpoint"""
        response = requests.get("http://localhost:8083/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "healthy")
        self.assertEqual(data["server"], "local-file-mcp-server")

    def test_initialize(self):
        """Test MCP initialize method"""
        data = {"jsonrpc": "2.0", "id": 1, "method": "initialize"}
        response = self.make_request(data)

        self.assertEqual(response["jsonrpc"], "2.0")
        self.assertEqual(response["id"], 1)
        self.assertIn("result", response)
        self.assertEqual(response["result"]["protocolVersion"], "2024-11-05")
        self.assertIn("serverInfo", response["result"])

    def test_tools_list(self):
        """Test tools/list method"""
        data = {"jsonrpc": "2.0", "id": 2, "method": "tools/list"}
        response = self.make_request(data)

        self.assertEqual(response["jsonrpc"], "2.0")
        self.assertEqual(response["id"], 2)
        self.assertIn("result", response)
        self.assertIn("tools", response["result"])
        self.assertEqual(len(response["result"]["tools"]), 1)
        self.assertEqual(
            response["result"]["tools"][0]["name"], "local_file_mcp_server"
        )

    def test_invalid_api_key(self):
        """Test request with invalid API key"""
        data = {"jsonrpc": "2.0", "id": 3, "method": "tools/list"}
        response = self.make_request(data, api_key="invalid-key")

        self.assertEqual(response["jsonrpc"], "2.0")
        self.assertEqual(response["id"], 3)
        self.assertIn("error", response)
        self.assertEqual(response["error"]["code"], -32001)
        self.assertIn("Invalid API key", response["error"]["message"])

    def test_create_file(self):
        """Test creating a new file"""
        data = {
            "jsonrpc": "2.0",
            "id": 4,
            "method": "tools/call",
            "params": {
                "name": "local_file_mcp_server",
                "arguments": {
                    "operation": "create",
                    "file_path": "test.txt",
                    "content": "Hello, World!",
                },
            },
        }
        response = self.make_request(data)

        self.assertEqual(response["jsonrpc"], "2.0")
        self.assertEqual(response["id"], 4)
        self.assertIn("result", response)

        # Check file was created
        test_file = self.allowed_dir / "test.txt"
        self.assertTrue(test_file.exists())
        self.assertEqual(test_file.read_text(), "Hello, World!")

    def test_read_file(self):
        """Test reading an existing file"""
        # Create test file
        test_file = self.allowed_dir / "read_test.txt"
        test_file.write_text("Test content")

        data = {
            "jsonrpc": "2.0",
            "id": 5,
            "method": "tools/call",
            "params": {
                "name": "local_file_mcp_server",
                "arguments": {"operation": "read", "file_path": "read_test.txt"},
            },
        }
        response = self.make_request(data)

        self.assertEqual(response["jsonrpc"], "2.0")
        self.assertEqual(response["id"], 5)
        self.assertIn("result", response)
        self.assertIn("Test content", response["result"]["content"][0]["text"])

    def test_write_file(self):
        """Test writing to an existing file"""
        # Create test file
        test_file = self.allowed_dir / "write_test.txt"
        test_file.write_text("Original content")

        data = {
            "jsonrpc": "2.0",
            "id": 6,
            "method": "tools/call",
            "params": {
                "name": "local_file_mcp_server",
                "arguments": {
                    "operation": "write",
                    "file_path": "write_test.txt",
                    "content": "Updated content",
                },
            },
        }
        response = self.make_request(data)

        self.assertEqual(response["jsonrpc"], "2.0")
        self.assertEqual(response["id"], 6)
        self.assertIn("result", response)

        # Check file was updated
        self.assertEqual(test_file.read_text(), "Updated content")

    def test_delete_file(self):
        """Test deleting a file"""
        # Create test file
        test_file = self.allowed_dir / "delete_test.txt"
        test_file.write_text("To be deleted")

        data = {
            "jsonrpc": "2.0",
            "id": 7,
            "method": "tools/call",
            "params": {
                "name": "local_file_mcp_server",
                "arguments": {"operation": "delete", "file_path": "delete_test.txt"},
            },
        }
        response = self.make_request(data)

        self.assertEqual(response["jsonrpc"], "2.0")
        self.assertEqual(response["id"], 7)
        self.assertIn("result", response)

        # Check file was deleted
        self.assertFalse(test_file.exists())

    def test_list_directory(self):
        """Test listing directory contents"""
        # Create test files
        (self.allowed_dir / "file1.txt").write_text("content1")
        (self.allowed_dir / "file2.json").write_text('{"key": "value"}')
        (self.allowed_dir / "subdir").mkdir()

        data = {
            "jsonrpc": "2.0",
            "id": 8,
            "method": "tools/call",
            "params": {
                "name": "local_file_mcp_server",
                "arguments": {"operation": "list", "file_path": "."},
            },
        }
        response = self.make_request(data)

        self.assertEqual(response["jsonrpc"], "2.0")
        self.assertEqual(response["id"], 8)
        self.assertIn("result", response)

        content = response["result"]["content"][0]["text"]
        self.assertIn("file1.txt", content)
        self.assertIn("file2.json", content)
        self.assertIn("subdir", content)

    def test_invalid_file_extension(self):
        """Test creating file with invalid extension"""
        data = {
            "jsonrpc": "2.0",
            "id": 9,
            "method": "tools/call",
            "params": {
                "name": "local_file_mcp_server",
                "arguments": {
                    "operation": "create",
                    "file_path": "test.exe",
                    "content": "not allowed",
                },
            },
        }
        response = self.make_request(data)

        self.assertEqual(response["jsonrpc"], "2.0")
        self.assertEqual(response["id"], 9)
        self.assertIn("error", response)
        self.assertEqual(response["error"]["code"], -32602)
        self.assertIn("File extension not allowed", response["error"]["message"])

    def test_file_too_large(self):
        """Test creating file that's too large"""
        large_content = "x" * (2 * 1024 * 1024)  # 2MB, larger than 1MB limit

        data = {
            "jsonrpc": "2.0",
            "id": 10,
            "method": "tools/call",
            "params": {
                "name": "local_file_mcp_server",
                "arguments": {
                    "operation": "create",
                    "file_path": "large.txt",
                    "content": large_content,
                },
            },
        }
        response = self.make_request(data)

        self.assertEqual(response["jsonrpc"], "2.0")
        self.assertEqual(response["id"], 10)
        self.assertIn("error", response)
        self.assertEqual(response["error"]["code"], -32602)
        self.assertIn("File size exceeds limit", response["error"]["message"])

    def test_path_traversal_protection(self):
        """Test protection against path traversal attacks"""
        data = {
            "jsonrpc": "2.0",
            "id": 11,
            "method": "tools/call",
            "params": {
                "name": "local_file_mcp_server",
                "arguments": {"operation": "read", "file_path": "../../../etc/passwd"},
            },
        }
        response = self.make_request(data)

        self.assertEqual(response["jsonrpc"], "2.0")
        self.assertEqual(response["id"], 11)
        self.assertIn("error", response)
        self.assertEqual(response["error"]["code"], -32602)
        self.assertIn("outside allowed directory", response["error"]["message"])


class TestConfigLoad(unittest.TestCase):
    """Test configuration loading"""

    def test_default_config(self):
        """Test default configuration when no .env file exists"""
        config = load_env_config()

        self.assertEqual(config["API_KEY"], "secure-mcp-key-123")
        self.assertEqual(config["PORT"], 8082)
        self.assertEqual(config["HOST"], "localhost")
        self.assertEqual(config["ALLOWED_PATH"], "./allowed")
        self.assertTrue(config["CREATE_ALLOWED_DIR"])
        self.assertEqual(config["MAX_FILE_SIZE"], 10485760)
        self.assertEqual(config["LOG_LEVEL"], "INFO")
        self.assertTrue(config["LOG_REQUESTS"])


if __name__ == "__main__":
    # Run the tests
    unittest.main(verbosity=2)
