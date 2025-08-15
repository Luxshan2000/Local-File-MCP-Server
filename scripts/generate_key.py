#!/usr/bin/env python3
"""
MCP Server API Key Generator
Generates a secure 64-character random API key for the MCP file server.
"""

import secrets
import string
import os


def generate_secure_key(length=64):
    """Generate a cryptographically secure random API key."""
    # Use alphanumeric characters (both cases) and some safe symbols
    alphabet = string.ascii_letters + string.digits + "-_"
    return "".join(secrets.choice(alphabet) for _ in range(length))


def create_env_file():
    """Create or update .env file with a new API key."""
    env_path = ".env"
    env_example_path = ".env.example"

    # Generate new secure key
    api_key = generate_secure_key(64)

    print(f"🔑 Generated secure API key: {api_key}")

    # Read template from .env.example if it exists
    if os.path.exists(env_example_path):
        with open(env_example_path, "r") as f:
            content = f.read()

        # Replace the default key with the new secure key
        content = content.replace("secure-mcp-key-123", api_key)
    else:
        # Create basic .env content
        content = f"""# MCP File Server Configuration
# Generated secure API key

MCP_PORT=8082
MCP_HOST=localhost
MCP_API_KEY={api_key}
MCP_ALLOWED_PATH=./allowed
MCP_CREATE_ALLOWED_DIR=true
MCP_MAX_FILE_SIZE=10485760
MCP_LOG_LEVEL=INFO
MCP_LOG_REQUESTS=true
"""

    # Write to .env file
    with open(env_path, "w") as f:
        f.write(content)

    print(f"✅ Created {env_path} with secure configuration")
    print(f"🔒 Your API key is: {api_key}")
    print("📝 Save this key securely - you'll need it to access your MCP server!")

    return api_key


if __name__ == "__main__":
    print("🚀 MCP Server API Key Generator")
    print("=" * 50)

    # Check if .env already exists
    if os.path.exists(".env"):
        response = input("⚠️  .env file already exists. Overwrite? (y/N): ").lower()
        if response != "y":
            print("❌ Cancelled. Existing .env file preserved.")
            exit(0)

    try:
        api_key = create_env_file()

        print("\n🎯 Next steps:")
        print("1. Start your MCP server: python3 server.py")
        print(f"2. Use this API key in your requests: {api_key}")
        print("3. Keep your .env file secure and never commit it to version control!")

    except Exception as e:
        print(f"❌ Error creating .env file: {e}")
        exit(1)
