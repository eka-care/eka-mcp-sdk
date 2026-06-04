from typing import Any, Dict
import logging

from fastmcp import FastMCP
from fastmcp.server.dependencies import get_access_token, AccessToken
from fastmcp.dependencies import CurrentContext
from fastmcp.server.context import Context

from ..auth.models import EkaAPIError
from ..clients.client_factory import ClientFactory
from ..services.extra_service import ExtraService
from ..utils.fastmcp_helper import write_tool_annotations
from ..utils.tool_registration import get_extra_headers
from ..utils.workspace_utils import get_workspace_id
from .models import GeneratePatientLead

logger = logging.getLogger(__name__)


def register_extra_tools(mcp: FastMCP) -> None:
    """Register extra MCP tools such as CRM lead creation."""

    @mcp.tool(
        tags={"crm", "lead", "write", "create", "patient"},
        annotations=write_tool_annotations()
    )
    async def create_crm_lead_tool(
        lead_data: GeneratePatientLead,
        ctx: Context = CurrentContext()
    ) -> Dict[str, Any]:
        """Create a CRM lead in the current workspace."""
        await ctx.info("[create_crm_lead_tool] Creating CRM lead")

        try:
            token: AccessToken | None = get_access_token()
            access_token = token.token if token else None
            workspace_id = get_workspace_id()
            custom_headers = get_extra_headers()
            client = ClientFactory.create_client(
                workspace_id, access_token, custom_headers
            )
            extra_service = ExtraService(client)
            lead_data_dict = lead_data.model_dump(exclude_none=True)
            name_parts = (lead_data_dict.get("patient_name") or "").strip().split(None, 1)
            lead_data_dict["patient_first_name"] = name_parts[0] if name_parts else ""
            lead_data_dict["patient_last_name"] = name_parts[1] if len(name_parts) > 1 else ""
            result = await extra_service.create_crm_lead(
                lead_data_dict
            )

            await ctx.info("[create_crm_lead_tool] Completed successfully\n")
            return {"success": True, "data": result}
        except EkaAPIError as e:
            await ctx.error(f"[create_crm_lead_tool] Failed: {e.message}\n")
            return {
                "success": False,
                "error": {
                    "message": e.message,
                    "status_code": e.status_code,
                    "error_code": e.error_code
                }
            }