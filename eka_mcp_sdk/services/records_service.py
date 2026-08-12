"""
Medical records service module containing core business logic for patient
medical records (the eka "vault").

This module provides reusable service classes that can be used both by MCP tools
and directly by other applications like CrewAI agents.
"""
from typing import Any, Dict, List, Optional
import logging
import mimetypes
import os

from ..clients.eka_emr_client import EkaEMRClient
from ..auth.models import EkaAPIError

logger = logging.getLogger(__name__)


class RecordsService:
    """Core service for patient medical records operations."""

    def __init__(self, client: EkaEMRClient):
        """
        Initialize the records service.

        Args:
            client: EkaEMRClient instance for API calls
        """
        self.client = client

    async def list_patient_records(
        self,
        patient_id: str,
        updated_after: Optional[int] = None,
        offset: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        List a patient's medical records.

        Args:
            patient_id: Patient's unique identifier (oid)
            updated_after: Only return records updated after this epoch (seconds)
            offset: Pagination token (next_token from a previous response)

        Returns:
            Records list with items and the next pagination token

        Raises:
            EkaAPIError: If the API call fails
        """
        return await self.client.list_medical_records(patient_id, updated_after, offset)

    async def get_patient_record(
        self,
        patient_id: str,
        document_id: str,
    ) -> Dict[str, Any]:
        """
        Get a single medical record's metadata and signed download URL.

        Args:
            patient_id: Patient's unique identifier (oid)
            document_id: Unique identifier of the record/document

        Returns:
            Record metadata including a signed download URL for the file

        Raises:
            EkaAPIError: If the API call fails
        """
        return await self.client.get_medical_record(patient_id, document_id)

    async def delete_patient_record(
        self,
        patient_id: str,
        document_id: str,
    ) -> Dict[str, Any]:
        """
        Delete a patient's medical record. This is irreversible.

        Args:
            patient_id: Patient's unique identifier (oid)
            document_id: Unique identifier of the record/document to delete

        Returns:
            Confirmation of the deletion

        Raises:
            EkaAPIError: If the API call fails
        """
        return await self.client.delete_medical_record(patient_id, document_id)

    async def upload_patient_record(
        self,
        patient_id: str,
        file_path: str,
        title: Optional[str] = None,
        tags: Optional[List[str]] = None,
        document_type: Optional[str] = None,
        document_date: Optional[int] = None,
        cases: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Upload a local file as a medical record for a patient.

        This orchestrates the two-step eka upload flow:
        1. Register the document metadata and obtain a presigned storage URL.
        2. Upload the file bytes directly to that presigned URL.

        Args:
            patient_id: Patient's unique identifier (oid)
            file_path: Absolute path to a local file to upload
            title: Optional human-readable title (max 256 chars)
            tags: Optional list of tags (max 10, each 2-20 chars)
            document_type: Optional document type code (e.g. "lr" for lab report)
            document_date: Optional document reference date as epoch seconds
            cases: Optional list of case identifiers to link the record to

        Returns:
            Summary of the uploaded record including its document_id

        Raises:
            EkaAPIError: If the file is missing or any step of the upload fails
        """
        if not os.path.isfile(file_path):
            raise EkaAPIError(f"File not found or not a regular file: {file_path}")

        file_size = os.path.getsize(file_path)
        filename = os.path.basename(file_path)
        content_type = mimetypes.guess_type(file_path)[0] or "application/octet-stream"

        with open(file_path, "rb") as f:
            file_bytes = f.read()

        doc_request: Dict[str, Any] = {
            "files": [{"contentType": content_type, "file_size": file_size}]
        }
        if document_type:
            doc_request["dt"] = document_type
        if title:
            doc_request["title"] = title
        if tags:
            doc_request["tg"] = tags
        if document_date is not None:
            doc_request["dd_e"] = document_date
        if cases:
            doc_request["cases"] = cases

        # Step 1: obtain authorization (presigned URL)
        auth_response = await self.client.initiate_medical_record_upload(
            patient_id, [doc_request]
        )

        if auth_response.get("error"):
            raise EkaAPIError(
                auth_response.get("message") or "Failed to authorize record upload"
            )

        batch = auth_response.get("batch_response") or []
        if not batch:
            raise EkaAPIError("Upload authorization returned no batch response")

        entry = batch[0]
        error_details = entry.get("error_details")
        if error_details:
            raise EkaAPIError(
                error_details.get("message") or "Failed to authorize record upload",
                error_code=error_details.get("code"),
            )

        document_id = entry.get("document_id")
        forms = entry.get("forms") or []
        if not forms:
            raise EkaAPIError("Upload authorization returned no presigned form")

        form = forms[0]
        presigned_url = form.get("url")
        fields = form.get("fields") or {}
        if not presigned_url:
            raise EkaAPIError("Upload authorization returned no presigned URL")

        # Step 2: upload the file bytes to storage
        status_code = await self.client.upload_file_to_presigned_url(
            presigned_url, fields, file_bytes, filename, content_type
        )

        return {
            "document_id": document_id,
            "filename": filename,
            "title": title,
            "content_type": content_type,
            "file_size": file_size,
            "status": "uploaded",
            "storage_status_code": status_code,
        }
