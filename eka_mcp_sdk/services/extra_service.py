"""Extra service module for CRM and other additional EMR operations."""

from typing import Any, Dict

from ..clients.eka_emr_client import EkaEMRClient


class ExtraService:
    """Core service for additional EMR operations."""

    def __init__(self, client: EkaEMRClient):
        self.client = client

    async def create_crm_lead(self, lead_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a CRM lead through the EMR client."""
        return await self.client.create_crm_lead(lead_data)