from typing import Any, Dict, Optional, List, Annotated
import logging
from fastmcp import FastMCP
from fastmcp.server.dependencies import get_access_token, AccessToken
from fastmcp.dependencies import CurrentContext
from fastmcp.server.context import Context

from ..clients.eka_emr_client import EkaEMRClient
from ..auth.models import EkaAPIError
from ..services.records_service import RecordsService
from ..utils.tool_registration import get_extra_headers
from ..utils.fastmcp_helper import readonly_tool_annotations, write_tool_annotations

logger = logging.getLogger(__name__)


def register_records_tools(mcp: FastMCP) -> None:
    """Register Medical Records (vault) MCP tools."""

    @mcp.tool(
        title="List Patient Records",
        tags={"records", "read", "list"},
        annotations=readonly_tool_annotations()
    )
    async def list_patient_records(
        patient_id: Annotated[str, "Patient ID (oid from list/mobile lookup)"],
        updated_after: Annotated[Optional[int], "Only return records updated after this epoch (seconds)"] = None,
        offset: Annotated[Optional[str], "Pagination token (next_token from a previous response)"] = None,
        ctx: Context = CurrentContext()
    ) -> Dict[str, Any]:
        """
        List a patient's medical records (lab reports, prescriptions, scans, etc.).

        When to use this tool
        Use this to browse or page through the documents stored in a patient's
        medical record vault. Returns lightweight metadata per record, not the
        file contents. To get a downloadable file, follow up with get_patient_record.

        Trigger Keywords / Phrases
        list patient records, medical records, documents, lab reports, vault,
        uploaded reports, patient files, show records

        Args:
            patient_id: Patient's unique identifier (oid)
            updated_after: Only return records updated after this epoch (seconds)
            offset: Pagination token from a previous response's next_token

        Returns:
            Records with items (document_id, type, upload_date, title, tags, thumbnail)
            and a next_token for pagination. Empty items array if the patient has no records.
        """
        await ctx.info(f"[list_patient_records] Listing records for patient: {patient_id}")

        try:
            token: AccessToken | None = get_access_token()
            client = EkaEMRClient(access_token=token.token if token else None, custom_headers=get_extra_headers())
            records_service = RecordsService(client)
            result = await records_service.list_patient_records(patient_id, updated_after, offset)

            await ctx.info("Retrieved patient records successfully")

            return {"success": True, "data": result}
        except EkaAPIError as e:
            await ctx.error(f"Failed to list patient records: {e.message}")
            return {
                "success": False,
                "error": {
                    "message": e.message,
                    "status_code": e.status_code,
                    "error_code": e.error_code
                }
            }

    @mcp.tool(
        title="Get Patient Record",
        tags={"records", "read", "details"},
        annotations=readonly_tool_annotations()
    )
    async def get_patient_record(
        patient_id: Annotated[str, "Patient ID (oid from list/mobile lookup)"],
        document_id: Annotated[str, "Record/document unique identifier (from list_patient_records)"],
        ctx: Context = CurrentContext()
    ) -> Dict[str, Any]:
        """
        Get a single medical record's metadata and a signed download URL for the file.

        When to use this tool
        Use this after list_patient_records when you need the full details of one
        record, including a time-limited download URL to retrieve the actual file.

        Trigger Keywords / Phrases
        get record, fetch record, download record, open document, record details,
        view lab report, get file

        Args:
            patient_id: Patient's unique identifier (oid)
            document_id: The record's unique identifier

        Returns:
            Record metadata plus a signed download URL for the underlying file.
        """
        await ctx.info(f"[get_patient_record] Getting record {document_id} for patient: {patient_id}")

        try:
            token: AccessToken | None = get_access_token()
            client = EkaEMRClient(access_token=token.token if token else None, custom_headers=get_extra_headers())
            records_service = RecordsService(client)
            result = await records_service.get_patient_record(patient_id, document_id)

            await ctx.info("Retrieved patient record successfully")

            return {"success": True, "data": result}
        except EkaAPIError as e:
            await ctx.error(f"Failed to get patient record: {e.message}")
            return {
                "success": False,
                "error": {
                    "message": e.message,
                    "status_code": e.status_code,
                    "error_code": e.error_code
                }
            }

    @mcp.tool(
        title="Delete Patient Record",
        tags={"records", "write", "delete"},
        annotations=write_tool_annotations(destructive=True)
    )
    async def delete_patient_record(
        patient_id: Annotated[str, "Patient ID (oid from list/mobile lookup)"],
        document_id: Annotated[str, "Record/document unique identifier to delete (from list_patient_records)"],
        ctx: Context = CurrentContext()
    ) -> Dict[str, Any]:
        """
        Permanently delete a medical record from a patient's vault. This is irreversible.

        When to use this tool
        Use this to remove a document from a patient's medical record vault. Because
        deletion cannot be undone, confirm the document_id first via list_patient_records
        or get_patient_record, and confirm intent with the user before calling.

        Trigger Keywords / Phrases
        delete record, remove document, delete file, discard record, remove from vault

        Args:
            patient_id: Patient's unique identifier (oid)
            document_id: The record's unique identifier to delete

        Returns:
            Confirmation of the deletion.
        """
        await ctx.info(f"[delete_patient_record] Deleting record {document_id} for patient: {patient_id}")

        try:
            token: AccessToken | None = get_access_token()
            client = EkaEMRClient(access_token=token.token if token else None, custom_headers=get_extra_headers())
            records_service = RecordsService(client)
            result = await records_service.delete_patient_record(patient_id, document_id)

            await ctx.info("Deleted patient record successfully")

            return {"success": True, "data": result}
        except EkaAPIError as e:
            await ctx.error(f"Failed to delete patient record: {e.message}")
            return {
                "success": False,
                "error": {
                    "message": e.message,
                    "status_code": e.status_code,
                    "error_code": e.error_code
                }
            }

    @mcp.tool(
        title="Upload Patient Record",
        tags={"records", "write", "upload"},
        annotations=write_tool_annotations()
    )
    async def upload_patient_record(
        patient_id: Annotated[str, "Patient ID (oid from list/mobile lookup)"],
        file_path: Annotated[str, "Absolute path to a local file to upload (PDF, image, etc.)"],
        title: Annotated[Optional[str], "Human-readable title (max 256 chars)"] = None,
        tags: Annotated[Optional[List[str]], "Tags for the record (max 10, each 2-20 chars)"] = None,
        document_type: Annotated[Optional[str], "Document type code, e.g. 'lr' for lab report"] = None,
        document_date: Annotated[Optional[int], "Document reference date as epoch seconds"] = None,
        ctx: Context = CurrentContext()
    ) -> Dict[str, Any]:
        """
        Upload a local file as a medical record for a patient.

        When to use this tool
        Use this to add a document (lab report, prescription scan, imaging, etc.)
        to a patient's medical record vault from a file on the local filesystem.
        The tool handles the full two-step eka upload flow (authorize + upload).

        Trigger Keywords / Phrases
        upload record, add document, attach lab report, upload file, add to vault,
        store medical record, upload prescription

        Args:
            patient_id: Patient's unique identifier (oid)
            file_path: Absolute path to the local file to upload
            title: Optional human-readable title
            tags: Optional list of tags
            document_type: Optional document type code (e.g. "lr")
            document_date: Optional document reference date as epoch seconds

        Returns:
            Summary of the uploaded record including its new document_id and status.
        """
        await ctx.info(f"[upload_patient_record] Uploading '{file_path}' for patient: {patient_id}")

        try:
            token: AccessToken | None = get_access_token()
            client = EkaEMRClient(access_token=token.token if token else None, custom_headers=get_extra_headers())
            records_service = RecordsService(client)
            result = await records_service.upload_patient_record(
                patient_id=patient_id,
                file_path=file_path,
                title=title,
                tags=tags,
                document_type=document_type,
                document_date=document_date,
            )

            await ctx.info(f"Uploaded patient record successfully: {result.get('document_id')}")

            return {"success": True, "data": result}
        except EkaAPIError as e:
            await ctx.error(f"Failed to upload patient record: {e.message}")
            return {
                "success": False,
                "error": {
                    "message": e.message,
                    "status_code": e.status_code,
                    "error_code": e.error_code
                }
            }
