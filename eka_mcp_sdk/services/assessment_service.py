"""Assessment service module for health assessment operations."""
from typing import Any, Dict, Optional, List
import logging

from ..clients.eka_emr_client import EkaEMRClient
from ..auth.models import EkaAPIError

logger = logging.getLogger(__name__)


class AssessmentService:
    """Core service for assessment operations."""
    
    def __init__(self, client: EkaEMRClient):
        """
        Initialize the assessment service.
        
        Args:
            client: EkaEMRClient instance for API calls
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
    
    async def init_assessment(
        self,
        user_info: Dict[str, Any],
        workflow_id: str,
        patient_uuid: str,
        practitioner_uuid: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Initialize a new assessment.
        
        Args:
            user_info: Dictionary containing user information (e.g., dob, gender)
            workflow_id: Workflow ID for the assessment
            patient_uuid: UUID of the patient
            practitioner_uuid: UUID of the practitioner
            context: Optional context for the assessment
            
        Returns:
            Dictionary containing the initialized assessment data
        """
        return await self.client.init_assessment(
            user_info=user_info,
            workflow_id=workflow_id,
            patient_uuid=patient_uuid,
            practitioner_uuid=practitioner_uuid,
            context=context
        )