#!/usr/bin/env python3
"""
Simple HTTP client test for FastMCP File Server
Tests the HTTP transport (streamable HTTP with SSE)
"""

import requests
import json

def test_fastmcp_http():
    """Test FastMCP HTTP server"""
    import os
    
    base_url = "http://127.0.0.1:8082"
    api_key = os.getenv("MCP_API_KEY", "")
    
    print("🌐 Testing FastMCP HTTP Server")
    print("=" * 40)
    
    # Headers required for FastMCP streamable HTTP
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json, text/event-stream'
    }
    
    # Add Bearer token if API key is provided
    if api_key:
        headers['Authorization'] = f'Bearer {api_key}'
        print(f"🔐 Using API key authentication")
    
    try:
        # Test 1: Initialize
        print("1️⃣ Initialize connection...")
        init_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "http-test", "version": "1.0"}
            }
        }
        
        response = requests.post(f"{base_url}/mcp", 
                               json=init_request, 
                               headers=headers,
                               timeout=10)
        
        if response.status_code == 200:
            # FastMCP returns SSE format: "event: message\ndata: {json}\n"
            lines = [line.strip() for line in response.text.split('\n') if line.strip()]
            if len(lines) >= 2 and lines[0] == "event: message":
                data_line = lines[1]
                if data_line.startswith("data: "):
                    json_data = data_line[6:]  # Remove "data: " prefix
                    data = json.loads(json_data)
                    print(f"   ✅ Connected to: {data['result']['serverInfo']['name']}")
                    print(f"   ✅ Protocol: {data['result']['protocolVersion']}")
                else:
                    print(f"   ❌ Invalid data line: {data_line[:50]}")
                    return False
            else:
                print(f"   📝 Lines: {lines}")
                print(f"   ❌ Unexpected format - {len(lines)} lines")
                return False
        else:
            print(f"   ❌ Failed: {response.status_code} - {response.text}")
            return False
        
        # Note: FastMCP's streamable HTTP requires session management
        # For full functionality, you'd need to handle session IDs
        # This is a basic connectivity test
        
        print("   ℹ️  Note: Full HTTP testing requires session management")
        print("   ℹ️  Use stdio transport for simple integration")
        print("✅ HTTP server is accessible!")
        return True
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Connection failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

if __name__ == "__main__":
    success = test_fastmcp_http()
    if success:
        print("\n🎉 HTTP server test passed!")
        print("💡 For full MCP functionality, use stdio transport or MCP client libraries")
    else:
        print("\n❌ HTTP server test failed!")
        print("💡 Make sure to run 'make run-http' first")