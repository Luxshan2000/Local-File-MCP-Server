#!/usr/bin/env python3
"""
Test scope validation with different access levels
"""

import requests
import json

def test_scope_validation():
    """Test different access levels and scope validation"""
    base_url = "http://127.0.0.1:8086"
    
    # Different access tokens
    tokens = {
        "read": "test-readonly-123",
        "write": "test-readwrite-456", 
        "admin": "test-admin-789"
    }
    
    print("🔐 Testing Scope-Based Access Control")
    print("=" * 45)
    
    for access_level, token in tokens.items():
        print(f"\n🧪 Testing {access_level.upper()} access level")
        print("-" * 30)
        
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json, text/event-stream',
            'Authorization': f'Bearer {token}'
        }
        
        # Test read operation (should work for all)
        test_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "list_files",
                "arguments": {"directory_path": "."}
            }
        }
        
        response = requests.post(f"{base_url}/mcp", 
                               json=test_request, 
                               headers=headers,
                               timeout=10)
        
        if response.status_code == 200:
            print(f"   ✅ list_files: SUCCESS")
        else:
            print(f"   ❌ list_files: FAILED ({response.status_code})")
        
        # Test write operation (should fail for read-only)
        test_request["params"]["name"] = "create_file"
        test_request["params"]["arguments"] = {
            "file_path": f"test_{access_level}.txt",
            "content": f"Test content for {access_level}"
        }
        
        response = requests.post(f"{base_url}/mcp", 
                               json=test_request, 
                               headers=headers,
                               timeout=10)
        
        if response.status_code == 200:
            print(f"   ✅ create_file: SUCCESS")
        else:
            print(f"   ❌ create_file: FAILED ({response.status_code})")
        
        # Test delete operation (should only work for admin)
        test_request["params"]["name"] = "delete_file"
        test_request["params"]["arguments"] = {
            "file_path": f"test_{access_level}.txt"
        }
        
        response = requests.post(f"{base_url}/mcp", 
                               json=test_request, 
                               headers=headers,
                               timeout=10)
        
        if response.status_code == 200:
            print(f"   ✅ delete_file: SUCCESS")
        else:
            print(f"   ❌ delete_file: FAILED ({response.status_code})")

if __name__ == "__main__":
    test_scope_validation()