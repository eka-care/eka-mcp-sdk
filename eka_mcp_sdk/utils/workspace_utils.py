"""
Workspace utilities for detecting and routing requests to correct EMR clients.
"""

import json
import logging

from fastmcp.server.dependencies import get_http_headers
from ..config.settings import settings

logger = logging.getLogger(__name__)


def get_workspace_id() -> str:
    """
    Extract workspace ID from x-eka-jwt-payload header.
    
    The header contains a JSON payload with a 'w-id' field that identifies
    the workspace (e.g., 'moolchand', 'ekaemr').
    
    Returns:
        Workspace ID string, defaults to 'ekaemr' if not found or on error.
    """
    try:
        headers = get_http_headers()
        jwt_payload_str = headers.get("x-eka-jwt-payload", "{}")
        
        if not jwt_payload_str or jwt_payload_str == "{}":
            logger.debug("No x-eka-jwt-payload header found, using default workspace")
            return "ekaemr"
        
        jwt_payload = json.loads(jwt_payload_str)
        workspace_id = jwt_payload.get("w-id", "ekaemr")

        WORKSPACE_ID_TO_WORKSPACE_NAME_DICT = settings.workspace_id_to_workspace_name_dict
        if WORKSPACE_ID_TO_WORKSPACE_NAME_DICT is str:
            WORKSPACE_ID_TO_WORKSPACE_NAME_DICT = json.loads(WORKSPACE_ID_TO_WORKSPACE_NAME_DICT) 
        
        logger.debug(f"Detected workspace: {workspace_id}")
        return WORKSPACE_ID_TO_WORKSPACE_NAME_DICT.get(workspace_id, "ekaemr")
        
    except json.JSONDecodeError as e:
        logger.warning(f"Failed to parse x-eka-jwt-payload header: {e}")
        return "ekaemr"
    except Exception as e:
        logger.warning(f"Error getting workspace ID: {e}")
        return "ekaemr"


def get_workspace_info() -> dict:
    """
    Get full workspace information from JWT payload.
    
    Returns:
        Dictionary with workspace info, or empty dict on error.
    """
    try:
        headers = get_http_headers()
        jwt_payload_str = headers.get("x-eka-jwt-payload", "{}")
        return json.loads(jwt_payload_str) if jwt_payload_str else {}
    except Exception:
        return {}
