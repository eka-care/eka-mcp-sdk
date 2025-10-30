import asyncio
from fastmcp import Client
from eka_mcp_sdk.server import create_mcp_server

config = {
    "mcpServers": {
        "eka_mcp_sdk": {
            # Local stdio server using installed command
            "transport": "stdio",
            "command": "eka-mcp-server",
            "env": {
                "EKA_CLIENT_ID": "EC_174022407354131",
                "EKA_CLIENT_SECRET": "32d471f4-f0b9-4a6e-a4ba-1f22ad1a94c9",
                "EKA_API_KEY": "bf47bf1b-b1e6-4af7-b00d-fe48b9cd56e3",
                "EKA_API_BASE_URL": "https://api.eka.care",
                "LOG_LEVEL": "DEBUG"
            }
        }
    }
}

# In-memory server (ideal for testing)
client = Client(config)

async def main():
    async with client:
        print("🏓 Testing MCP Server Connection...")
        
        # Basic server interaction
        await client.ping()
        print("✅ Server ping successful")
        
        # List available operations
        tools = await client.list_tools()
        resources = await client.list_resources()
        prompts = await client.list_prompts()
        
        print(f"\n📊 Available Tools: {len(tools)}")
        for tool in tools:
            print(f"  - {tool.name}: {tool.description}")
        
        print(f"\n📚 Available Resources: {len(resources)}")
        print(f"🎯 Available Prompts: {len(prompts)}")
        
        # Test server info tool (no parameters needed)
        print("\n🔍 Testing get_server_info tool...")
        result = await client.call_tool("get_server_info", {})
        print(f"✅ Server Info: {result}")
        
        # Test business entities (should work)
        print("\n🏥 Testing get_business_entities tool...")
        try:
            business_result = await client.call_tool("get_business_entities", {})
            print(f"✅ Business Entities: {business_result}")
        except Exception as e:
            print(f"⚠️  Error: {e}")
        
        # Test appointments with proper endpoint
        print("\n📅 Testing get_appointments tool (new endpoint)...")
        try:
            appointments_result = await client.call_tool("get_appointments", {})
            print(f"✅ Appointments: {appointments_result}")
        except Exception as e:
            print(f"⚠️  Error: {e}")
            
        print("\n🎉 MCP Client test completed!")

asyncio.run(main())
