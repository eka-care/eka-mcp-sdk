import asyncio
import logging
from fastmcp import FastMCP

from .config.settings import settings
from .auth.manager import auth_manager
from .tools.doctor_tools import register_doctor_tools

logging.basicConfig(level=getattr(logging, settings.log_level.upper()))
logger = logging.getLogger(__name__)


def create_mcp_server() -> FastMCP:
    """Create and configure the MCP server."""
    mcp = FastMCP(
        name="Eka.care EMR API Server",
        instructions="""
            This is the Eka.care EMR API Server. It is used to manage the Eka.care EMR system.
            Provides capabilities to manage appointments, prescriptions, and patient records.
            Give abilities to quickly ask questions about the patient's health and medical history.
            Answer practice related questions such as patient demographics, appointment history, prescription history, etc.
        """)
    
    @mcp.tool()
    async def get_server_info() -> dict:
        """
        Get server information and configuration.
        
        Returns:
            Server configuration and status information
        """
        return {
            "server_name": "Eka.care Healthcare API Server",
            "version": "0.1.0",
            "api_base_url": settings.eka_api_base_url,
            "available_modules": ["Doctor Tools"],
            "status": "running"
        }
    
    # Register all tool modules
    register_doctor_tools(mcp)
    
    return mcp


def main():
    """Main entry point for the MCP server."""
    logger.info("Starting Eka.care MCP Server...")
    logger.info(f"API base URL: {settings.eka_api_base_url}")
    
    mcp = create_mcp_server()
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()