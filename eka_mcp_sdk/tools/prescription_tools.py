from typing import Any, Dict, Optional
import logging
from fastmcp import FastMCP
from fastmcp.server.dependencies import get_access_token, AccessToken
from fastmcp.dependencies import CurrentContext
from fastmcp.server.context import Context

from ..clients.doctor_tools_client import DoctorToolsClient
from ..auth.models import EkaAPIError
from ..services.prescription_service import PrescriptionService

logger = logging.getLogger(__name__)


def register_prescription_tools(mcp: FastMCP) -> None:
    """Register Prescription Management MCP tools."""
    
    @mcp.tool()
    async def get_prescription_details_basic(
        prescription_id: str,
        ctx: Context = CurrentContext()
    ) -> Dict[str, Any]:
        """
        Get basic prescription details (prescription data only).
        
        ⚠️  Consider using get_comprehensive_prescription_details instead for complete information.
        Only use this if you specifically need basic prescription data without patient/doctor/clinic details.
        
        Args:
            prescription_id: Prescription's unique identifier
        
        Returns:
            Basic prescription details including medications and diagnosis only
        """
        await ctx.info(f"Getting basic prescription details for: {prescription_id}")
        
        try:
            token: AccessToken | None = get_access_token()
            client = DoctorToolsClient(access_token=token.token if token else None)
            prescription_service = PrescriptionService(client)
            result = await prescription_service.get_prescription_details_basic(prescription_id)
            
            await ctx.info("Retrieved basic prescription details successfully")
            
            return {"success": True, "data": result}
        except EkaAPIError as e:
            await ctx.error(f"Failed to get prescription details: {e.message}")
            return {
                "success": False,
                "error": {
                    "message": e.message,
                    "status_code": e.status_code,
                    "error_code": e.error_code
                }
            }
    
    @mcp.tool()
    async def get_comprehensive_prescription_details(
        prescription_id: str,
        include_patient_details: bool = True,
        include_doctor_details: bool = True,
        include_clinic_details: bool = True,
        ctx: Context = CurrentContext()
    ) -> Dict[str, Any]:
        """
        🌟 RECOMMENDED: Get comprehensive prescription details with enriched patient, doctor, and clinic information.
        
        This is the preferred tool for getting prescription information as it provides complete context
        including patient demographics, prescribing doctor details, and clinic information.
        Use this instead of get_prescription_details_basic unless you specifically need only prescription data.
        
        Args:
            prescription_id: Prescription's unique identifier
            include_patient_details: Whether to include patient details (default: True)
            include_doctor_details: Whether to include doctor details (default: True)
            include_clinic_details: Whether to include clinic details (default: True)
        
        Returns:
            Complete prescription details with enriched patient, doctor, and clinic information
        """
        await ctx.info(f"Getting comprehensive prescription details for: {prescription_id}")
        await ctx.debug(f"Include patient: {include_patient_details}, doctor: {include_doctor_details}, clinic: {include_clinic_details}")
        
        try:
            token: AccessToken | None = get_access_token()
            client = DoctorToolsClient(access_token=token.token if token else None)
            prescription_service = PrescriptionService(client)
            result = await prescription_service.get_comprehensive_prescription_details(
                prescription_id, include_patient_details, include_doctor_details, include_clinic_details
            )
            
            await ctx.info("Retrieved comprehensive prescription details successfully")
            
            return {"success": True, "data": result}
        except EkaAPIError as e:
            await ctx.error(f"Failed to get comprehensive prescription: {e.message}")
            return {
                "success": False,
                "error": {
                    "message": e.message,
                    "status_code": e.status_code,
                    "error_code": e.error_code
                }
            }


