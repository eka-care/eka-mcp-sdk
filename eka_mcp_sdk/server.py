import os
import json
import argparse
import logging
import sys
from fastmcp import FastMCP
from fastmcp.dependencies import CurrentContext
from fastmcp.server.context import Context

from eka_mcp_sdk.config.settings import settings
from eka_mcp_sdk.tools.doctor_tools import register_doctor_tools

# Configure logging to stderr (which MCP captures)
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger(__name__)

# Enable SDK client logging
logging.getLogger("eka_mcp_sdk.clients").setLevel(logging.DEBUG)


def create_mcp_server() -> FastMCP:
    """Create and configure the MCP server."""
    
    mcp = FastMCP(
        name="Eka.care EMR API Server",
        stateless_http=True,
        instructions="""
            This is the Eka.care EMR API Server. It is used to manage the Eka.care EMR system.
            Provides capabilities to manage appointments, prescriptions, and patient records.
            Give abilities to quickly ask questions about the patient's health and medical history.
            Answer practice related questions such as patient demographics, appointment history, prescription history, etc.
        """)
    
    
    @mcp.tool()
    async def get_server_info(ctx: Context = CurrentContext()) -> dict:
        """
        Get server information and configuration.
        
        Returns:
            Server configuration and status information
        """
        await ctx.info("Fetching server information")
        await ctx.debug(f"API Base URL: {settings.api_base_url}")
        
        return {
            "server_name": "Eka.care Healthcare API Server",
            "version": "0.1.0",
            "api_base_url": settings.api_base_url,
            "client_id": settings.client_id,
            "available_modules": ["Doctor Tools", "Patient Tools", "Appointment Tools", "Assessment Tools"],
            "status": "running"
        }
    
    # Register all tool modules
    register_doctor_tools(mcp)

    # Properly wrap _list_tools to add workspace filtering
    # We need to preserve the original method's signature and self binding
    from eka_mcp_sdk.utils.workspace_utils import get_workspace_id
    import functools
    
    # Get the original unbound method
    original_list_tools = FastMCP._list_tools
    
    @functools.wraps(original_list_tools)
    async def workspace_filtered_list_tools(*args, **kwargs):
        """Wrapper that filters tools based on workspace from headers."""
        # Call the original method to get all tools
        all_tools = await original_list_tools(*args, **kwargs)
        
        # Apply workspace filtering
        try:
            workspace_id = get_workspace_id() or "ekaemr"
            WORKSPACE_TOOLS_DICT = settings.workspace_tools_dict
            if WORKSPACE_TOOLS_DICT is str:
                WORKSPACE_TOOLS_DICT = json.loads(WORKSPACE_TOOLS_DICT)

            allowed_tool_names = set(WORKSPACE_TOOLS_DICT.get(workspace_id))

            # Filter tools to only those allowed for this workspace
            filtered_tools = [
                tool for tool in all_tools 
                if tool.name in allowed_tool_names
            ]
            
            logger.info(f"Workspace '{workspace_id}': Listed {len(filtered_tools)}/{len(all_tools)} tools")
            return filtered_tools
        except Exception as e:
            logger.warning(f"Error filtering tools by workspace: {e}, returning all tools")
            return all_tools
    
    # Bind the wrapper as a method on the mcp instance
    import types
    mcp._list_tools = types.MethodType(workspace_filtered_list_tools, mcp)
    
    return mcp


def main():
    """Main entry point for the MCP server."""
    parser = argparse.ArgumentParser(description="Eka.care MCP Server")
    parser.add_argument(
        "--transport", 
        choices=["stdio", "http"], 
        default="stdio",
        help="Transport type: stdio (default) or http"
    )
    parser.add_argument(
        "--host",
        default="localhost",
        help="Host for HTTP transport (default: localhost)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8888,
        help="Port for HTTP transport (default: 8888)"
    )
    
    args = parser.parse_args()
    
    logger.info(f"Starting Eka.care MCP Server with {args.transport} transport...")
    
    mcp = create_mcp_server()
    
    if args.transport == "http":
        logger.info(f"Running HTTP server on {args.host}:{args.port}")
        mcp.run(transport="http", host=args.host, port=args.port)
    else:
        logger.info("Running with stdio transport")
        mcp.run()


if __name__ == "__main__":
    main()
