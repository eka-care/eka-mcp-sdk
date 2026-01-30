import asyncio
import json
from fastmcp import Client

config = {
    "mcpServers": {
        "eka_mcp_sdk": {
            # Local stdio server using installed command
            "transport": "stdio",
            "command": "eka-mcp-server",
            "env": {
                "EKA_CLIENT_ID": "",
                "EKA_CLIENT_SECRET": "",
                "EKA_API_KEY": "",
                "EKA_API_BASE_URL": "https://api.eka.care",
                "LOG_LEVEL": "DEBUG"
            }
        }
    }
}

# In-memory server (ideal for testing)
client = Client(config)

def print_tool_response(response):
    if response.structured_content.get("is_elicitation", False):
        print(f"Elicitation Component: {response.structured_content.get('component')}")
        tool_response = response.structured_content.get("input")
        print(f"Tool Prompt: {tool_response.get('text', '')}")
        print(f"Additional Info: {tool_response.get('additional_info', {})}")


async def main():
    async with client:
        print("🏓 Testing MCP Server Connection...")
        
        # Basic server interaction
        await client.ping()
        print("✅ Server ping successful")
        
        # Test user authentication at different stages
        print("\n📅 Testing authenticate_user tool with no info...")
        try:
            result = await client.call_tool("authenticate_user", {})
            print(f"✅ Tool:")
            print_tool_response(result)
            

        except Exception as e:
            print(f"⚠️  Error: {e}")
        
        # Test user authentication at different stages
        print("\n📅 Testing authenticate_user tool with mobile number...")
        try:
            result = await client.call_tool("authenticate_user", { "identifier": "9876543219" })
            print(f"✅ Tool:")
            print_tool_response(result)
        except Exception as e:
            print(f"⚠️  Error: {e}")
            
        print("\n🎉 MCP Client test completed!")

asyncio.run(main())
