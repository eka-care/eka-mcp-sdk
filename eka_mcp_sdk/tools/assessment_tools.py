from typing import Any, Dict, Optional, List, Annotated
import logging
from fastmcp import FastMCP
from fastmcp.server.dependencies import get_access_token, AccessToken
from fastmcp.dependencies import CurrentContext
from fastmcp.server.context import Context

from ..clients.eka_emr_client import EkaEMRClient
from ..auth.models import EkaAPIError
from ..services.assessment_service import AssessmentService

logger = logging.getLogger(__name__)

def register_assessment_tools(mcp: FastMCP) -> None:
    """Register Assessment MCP tools."""
    
    @mcp.tool(
        description="Fetch and group assessments by patient and/or practitioner"
    )
    async def fetch_grouped_assessments(
        practitioner_uuid: Annotated[Optional[str], "UUID of the practitioner"] = None,
        patient_uuid: Annotated[Optional[str], "UUID of the patient"] = None,
        unique_identifier: Annotated[Optional[str], "Unique identifier for filtering/ patient oid"] = None,
        transaction_id: Annotated[Optional[str], "Transaction ID for filtering"] = None,
        wfids: Annotated[Optional[List[str]], "List of workflow IDs to filter"] = None,
        status: Annotated[str, "Status filter (e.g., COMPLETED, IN_PROGRESS)"] = "COMPLETED",
        ctx: Context = CurrentContext()
    ) -> Dict[str, Any]:
        """Returns grouped assessment data with patient and practitioner details."""
        filters = [f for f in [f"practitioner={practitioner_uuid}" if practitioner_uuid else None,
                              f"patient={patient_uuid}" if patient_uuid else None,
                              f"status={status}"] if f]
        filter_str = ", ".join(filters) if filters else "no filters"
        await ctx.info(f"Fetching grouped assessments with {filter_str}")
        
        try:
            token: AccessToken | None = get_access_token()
            client = EkaEMRClient(access_token=token.token if token else None)
            
            assessment_service = AssessmentService(client)
            
            result = await assessment_service.fetch_grouped_assessments(
                practitioner_uuid=practitioner_uuid,
                patient_uuid=patient_uuid,
                unique_identifier=unique_identifier,
                transaction_id=transaction_id,
                wfids=wfids,
                status=status
            )
            
            assessment_count = len(result.get('assessments', [])) if isinstance(result, dict) else 0
            await ctx.info(f"Retrieved {assessment_count} grouped assessments")
            
            return {"success": True, "data": result}
        except EkaAPIError as e:
            await ctx.error(f"Failed to fetch assessments: {e.message}")
            return {
                "success": False,
                "error": {
                    "message": e.message,
                    "status_code": e.status_code,
                    "error_code": e.error_code
                }
            }


