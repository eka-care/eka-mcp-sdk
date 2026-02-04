from pydantic import Field, ValidationError
from fastmcp.settings import ENV_FILE
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

DEFAULT_EKAEMR_TOOLS = ["search_patients","get_patient_details_basic","get_comprehensive_patient_profile","add_patient","list_patients","update_patient","archive_patient","get_patient_by_mobile","get_business_entities","get_doctor_profile_basic","get_clinic_details_basic","get_doctor_services","get_comprehensive_doctor_profile","get_comprehensive_clinic_profile","get_available_dates","get_appointment_slots","doctor_availability_elicitation","book_appointment","get_appointments_enriched","get_appointments_basic","get_appointment_details_enriched","get_appointment_details_basic","get_patient_appointments_enriched","get_patient_appointments_basic","update_appointment","complete_appointment","cancel_appointment","reschedule_appointment","get_prescription_details_basic","get_comprehensive_prescription_details"]


class EkaSettings(BaseSettings):
    """Base configuration settings for Eka.care SDK."""
    
    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_prefix="EKA_",
        extra="ignore"
    )
    
    # API Configuration
    api_base_url: str = Field(
        default="https://api.eka.care",
        description="Base URL for Eka.care APIs"
    )
    
    # Authentication
    client_id: str = Field(
        default=None,
        description="Eka.care client ID - required for all API calls"
    )
    client_secret: Optional[str] = Field(
        default=None,
        description="Eka.care client secret - required only if not using external access token"
    )
    api_key: Optional[str] = Field(
        default=None,
        description="Optional API key for additional authentication"
    )
    
    # Token Storage Configuration
    token_storage_dir: Optional[str] = Field(
        default=None,
        description="Directory for storing authentication tokens (default: ~/.eka_mcp)"
    )
    
    # Logging
    log_level: str = Field(default="INFO", description="Logging level")
    
    # Workspace Configuration
    workspace_client_type: str = Field(
        default="ekaemr",
        description="Workspace client type"
    )

    workspace_client_dict: dict = Field(
        default={"ekaemr": "eka_mcp_sdk.clients.eka_emr_client.EkaEMRClient"},
        description="Workspace ID to Workspace Client mapping"
    )

    workspace_id_to_workspace_name_dict: dict = Field(
        default={},
        description="Workspace ID to Workspace Name mapping"
    )

    workspace_tools_dict: dict = Field(
        default={"ekaemr": DEFAULT_EKAEMR_TOOLS},
        description="Workspace ID to Workspace Tools mapping"
    )
    
    # Cache for loaded client classes
    _client_class_cache: dict = {}
    
    def get_client_class(self, workspace_id: str):
        """
        Get client class for workspace, dynamically loading from module path.
        
        Args:
            workspace_id: The workspace identifier
            
        Returns:
            The client class (not instance)
        """
        import importlib
        
        if workspace_id in self._client_class_cache:
            return self._client_class_cache[workspace_id]
        
        class_path = self.workspace_client_dict.get(workspace_id)
        if class_path and isinstance(class_path, str):
            module_path, class_name = class_path.rsplit('.', 1)
            module = importlib.import_module(module_path)
            client_class = getattr(module, class_name)
            self._client_class_cache[workspace_id] = client_class
            return client_class
        
        # Return class directly if already a class (for backwards compat)
        if class_path and not isinstance(class_path, str):
            return class_path
        
        return None


# Singleton instance
settings = EkaSettings()
