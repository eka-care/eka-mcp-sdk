"""
Abstract Base EMR Client Interface.

All EMR client implementations (EkaEMR, Moolchand, etc.) must implement this interface.
This enables workspace-agnostic tool implementations via the factory pattern.
"""

from abc import abstractmethod
from typing import Dict, Any
from .base_client import BaseEkaClient


class BasePHRClient(BaseEkaClient):
    """Abstract interface for PHR client implementations.

    All PHR clients must implement these methods to be usable by
    the factory pattern and workspace routing.
    """

    @abstractmethod
    def get_api_module_name(self) -> str:
        pass

    @abstractmethod
    def get_workspace_name(self) -> str:
        """Return the name of the workspace this client handles."""
        pass

    # ==================== Patient Operations ====================

    @abstractmethod
    async def get_patient_vitals(self, patient_id: str) -> Dict[str, Any]:
        """Retrieve patient vitals."""
        pass

    @abstractmethod
    async def add_patient(self, patient_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a patient profile."""
        pass

    @abstractmethod
    async def get_patient_details(self, patient_id: str) -> Dict[str, Any]:
        """Retrieve patient profile."""
        pass

    @abstractmethod
    async def list_all_patient_profiles(
        self,
    ) -> Dict[str, Any]:
        """Retrieve patient profile."""
        pass

    @abstractmethod
    async def update_patient(
        self, patient_id: str, update_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update patient profile details."""
        pass

    @abstractmethod
    async def archive_patient(self, patient_id: str) -> Dict[str, Any]:
        """Archive patient profile."""
        pass

    @abstractmethod
    async def get_patient_by_mobile(
        self, mobile: str, full_profile: bool = False
    ) -> Dict[str, Any]:
        """Retrieve patient profiles by mobile number."""
        pass

    # ==================== Lifecycle ====================

    async def close(self) -> None:
        """Close HTTP client connections."""
        await self._http_client.aclose()