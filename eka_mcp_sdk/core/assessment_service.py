"""Assessment service module for health assessment operations."""
from typing import Any, Dict, Optional, List
import logging

from ..clients.doctor_tools_client import DoctorToolsClient
from ..auth.models import EkaAPIError

logger = logging.getLogger(__name__)


class AssessmentService:
    """Core service for assessment operations."""
    
    def __init__(self, client: DoctorToolsClient):
        """
        Initialize the assessment service.
        
        Args:
            client: DoctorToolsClient instance for API calls
        """
        self.client = client
    
    async def fetch_grouped_assessments(
        self,
        practitioner_uuid: Optional[str] = None,
        patient_uuid: Optional[str] = None,
        unique_identifier: Optional[str] = None,
        transaction_id: Optional[str] = None,
        wfids: Optional[List[str]] = None,
        status: str = "COMPLETED"
    ) -> Dict[str, Any]:
        """
        Fetch grouped assessment conversations.
        
        Args:
            practitioner_uuid: UUID of the practitioner
            patient_uuid: UUID of the patient
            unique_identifier: Unique identifier for filtering / patient oid
            transaction_id: Transaction ID for filtering
            wfids: List of workflow IDs to filter
            status: Status filter (default: COMPLETED)
            
        Returns:
            Grouped assessment data
        """
        return await self.client.fetch_grouped_assessments(
            practitioner_uuid=practitioner_uuid,
            patient_uuid=patient_uuid,
            unique_identifier=unique_identifier,
            transaction_id=transaction_id,
            wfids=wfids,
            status=status
        )
