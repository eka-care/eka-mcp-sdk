"""Helper functions for MCP tool annotations.

These helpers provide consistent annotation patterns across all tools.
According to FastMCP documentation, when readOnlyHint=True, destructiveHint 
is automatically False and doesn't need explicit setting.
"""

from mcp.types import ToolAnnotations


def readonly_tool_annotations(*, open_world: bool = False) -> ToolAnnotations:
    """Create annotations for read-only tools.
    
    Read-only tools don't modify data and are safe to call repeatedly.
    When readOnlyHint=True, destructiveHint is automatically False.
    
    Args:
        open_world: Whether tool interacts with external systems (default: False for Eka Care internal tools)
    
    Returns:
        ToolAnnotations configured for read-only operations
    """
    return ToolAnnotations(
        readOnlyHint=True,
        openWorldHint=open_world,
        destructiveHint=False
    )


def write_tool_annotations(*, destructive: bool = False, open_world: bool = False) -> ToolAnnotations:
    """Create annotations for write tools that modify data.
    
    Write tools create or update data but typically don't delete or cause data loss.
    
    Args:
        destructive: Whether operation causes data loss or irreversible changes (default: False)
        open_world: Whether tool interacts with external systems (default: False for Eka Care internal tools)
    
    Returns:
        ToolAnnotations configured for write operations
    """
    return ToolAnnotations(
        destructiveHint=destructive,
        openWorldHint=open_world
    )