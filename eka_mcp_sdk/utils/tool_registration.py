"""
Tool registration utilities for prioritizing comprehensive tools.

This module provides utilities to ensure comprehensive tools are registered
before basic tools, guiding LLMs to prefer the comprehensive versions.
"""

from typing import Dict, List, Callable, Any
from fastmcp import FastMCP
import logging

logger = logging.getLogger(__name__)


class ToolRegistrationHelper:
    """Helper class to manage tool registration order and priorities."""
    
    def __init__(self, mcp: FastMCP):
        self.mcp = mcp
        self.comprehensive_tools: List[Callable] = []
        self.basic_tools: List[Callable] = []
        self.utility_tools: List[Callable] = []
    
    def add_comprehensive_tool(self, tool_func: Callable) -> None:
        """Add a comprehensive tool (will be registered first)."""
        self.comprehensive_tools.append(tool_func)
    
    def add_basic_tool(self, tool_func: Callable) -> None:
        """Add a basic tool (will be registered after comprehensive tools)."""
        self.basic_tools.append(tool_func)
    
    def add_utility_tool(self, tool_func: Callable) -> None:
        """Add a utility tool (will be registered last)."""
        self.utility_tools.append(tool_func)
    
    def register_all(self) -> None:
        """Register all tools in priority order: comprehensive -> basic -> utility."""
        logger.info("Registering tools in priority order...")
        
        # Register comprehensive tools first (highest priority)
        logger.info(f"Registering {len(self.comprehensive_tools)} comprehensive tools...")
        for tool in self.comprehensive_tools:
            self.mcp.tool()(tool)
        
        # Register basic tools second
        logger.info(f"Registering {len(self.basic_tools)} basic tools...")
        for tool in self.basic_tools:
            self.mcp.tool()(tool)
        
        # Register utility tools last
        logger.info(f"Registering {len(self.utility_tools)} utility tools...")
        for tool in self.utility_tools:
            self.mcp.tool()(tool)
        
        total_tools = len(self.comprehensive_tools) + len(self.basic_tools) + len(self.utility_tools)
        logger.info(f"Successfully registered {total_tools} tools total")


def create_tool_categories() -> Dict[str, List[str]]:
    """
    Define tool categories for better organization.
    
    Returns:
        Dictionary mapping categories to tool name patterns
    """
    return {
        "comprehensive": [
            "*_enriched",
            "get_comprehensive_*",
            "*_with_details",
            "*_complete"
        ],
        "basic": [
            "*_basic",
            "*_simple",
            "*_minimal",
            "*_ids_only"
        ],
        "utility": [
            "search_*",
            "list_*", 
            "add_*",
            "update_*",
            "delete_*",
            "archive_*",
            "*_slots",
            "book_*",
            "cancel_*",
            "reschedule_*",
            "complete_*"
        ]
    }


def get_tool_priority(tool_name: str) -> int:
    """
    Get priority score for a tool based on its name.
    
    Args:
        tool_name: Name of the tool
    
    Returns:
        Priority score (lower = higher priority)
    """
    categories = create_tool_categories()
    
    # Check comprehensive tools (highest priority)
    for pattern in categories["comprehensive"]:
        if _matches_pattern(tool_name, pattern):
            return 1
    
    # Check utility tools (medium priority)
    for pattern in categories["utility"]:
        if _matches_pattern(tool_name, pattern):
            return 2
    
    # Check basic tools (lowest priority)
    for pattern in categories["basic"]:
        if _matches_pattern(tool_name, pattern):
            return 3
    
    # Default priority for unmatched tools
    return 2


def _matches_pattern(name: str, pattern: str) -> bool:
    """Check if a tool name matches a pattern with wildcards."""
    if pattern.startswith("*") and pattern.endswith("*"):
        return pattern[1:-1] in name
    elif pattern.startswith("*"):
        return name.endswith(pattern[1:])
    elif pattern.endswith("*"):
        return name.startswith(pattern[:-1])
    else:
        return name == pattern


def sort_tools_by_priority(tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Sort tools by priority (comprehensive first, basic last).
    
    Args:
        tools: List of tool dictionaries with 'name' key
    
    Returns:
        Sorted list of tools
    """
    return sorted(tools, key=lambda tool: get_tool_priority(tool.get("name", "")))


# Example usage and patterns for tool descriptions
COMPREHENSIVE_TOOL_DESCRIPTION_TEMPLATE = """
🌟 RECOMMENDED: {description}

This is the preferred tool for {use_case} as it provides complete context
{benefits}. Use this instead of {basic_alternative} unless you
specifically need {basic_use_case}.

{args_section}

Returns:
    {returns_description}
"""

BASIC_TOOL_DESCRIPTION_TEMPLATE = """
{description}

⚠️  Consider using {comprehensive_alternative} instead for complete information.
Only use this if you specifically need {specific_use_case}.

{args_section}

Returns:
    {returns_description}
"""


def register_all_tools(mcp: FastMCP) -> None:
    """
    Register all available tools to the MCP server.
    
    Args:
        mcp: FastMCP instance to register tools on
    """
    from ..tools.doctor_tools import register_doctor_tools
    from ..tools.appointment_tools import register_appointment_tools  
    from ..tools.patient_tools import register_patient_tools
    from ..tools.prescription_tools import register_prescription_tools
    
    logger.info("Registering all available tools...")
    
    try:
        register_doctor_tools(mcp)
        logger.info("Doctor tools registered successfully")
    except Exception as e:
        logger.error(f"Failed to register doctor tools: {e}")
    
    try:
        register_appointment_tools(mcp)
        logger.info("Appointment tools registered successfully")
    except Exception as e:
        logger.error(f"Failed to register appointment tools: {e}")
    
    try:
        register_patient_tools(mcp)
        logger.info("Patient tools registered successfully") 
    except Exception as e:
        logger.error(f"Failed to register patient tools: {e}")
    
    try:
        register_prescription_tools(mcp)
        logger.info("Prescription tools registered successfully")
    except Exception as e:
        logger.error(f"Failed to register prescription tools: {e}")
    
    logger.info("All tools registration completed")