"""Unit tests for the RecordsService medical-records flow."""

import asyncio
import os
import tempfile
from unittest.mock import AsyncMock, MagicMock

import pytest

from eka_mcp_sdk.auth.models import EkaAPIError
from eka_mcp_sdk.clients.eka_emr_client import EkaEMRClient
from eka_mcp_sdk.services.records_service import RecordsService


def make_mock_client():
    client = MagicMock(spec=EkaEMRClient)
    client.list_medical_records = AsyncMock()
    client.get_medical_record = AsyncMock()
    client.delete_medical_record = AsyncMock()
    client.initiate_medical_record_upload = AsyncMock()
    client.upload_file_to_presigned_url = AsyncMock()
    return client


def _make_temp_file(content: bytes = b"%PDF-1.4 fake report", suffix: str = ".pdf") -> str:
    fd, path = tempfile.mkstemp(suffix=suffix)
    with os.fdopen(fd, "wb") as f:
        f.write(content)
    return path


def test_list_patient_records_delegates_to_client():
    client = make_mock_client()
    client.list_medical_records.return_value = {"items": [], "next_token": None}

    service = RecordsService(client)
    result = asyncio.run(service.list_patient_records("oid-1", updated_after=123, offset="tok"))

    client.list_medical_records.assert_called_once_with("oid-1", 123, "tok")
    assert result == {"items": [], "next_token": None}


def test_get_patient_record_delegates_to_client():
    client = make_mock_client()
    client.get_medical_record.return_value = {"document_id": "doc-1", "download_url": "https://x"}

    service = RecordsService(client)
    result = asyncio.run(service.get_patient_record("oid-1", "doc-1"))

    client.get_medical_record.assert_called_once_with("oid-1", "doc-1")
    assert result["document_id"] == "doc-1"


def test_delete_patient_record_delegates_to_client():
    client = make_mock_client()
    client.delete_medical_record.return_value = {"success": True, "status_code": 204}

    service = RecordsService(client)
    result = asyncio.run(service.delete_patient_record("oid-1", "doc-1"))

    client.delete_medical_record.assert_called_once_with("oid-1", "doc-1")
    assert result["success"] is True


def test_upload_patient_record_orchestrates_two_step_flow():
    client = make_mock_client()
    client.initiate_medical_record_upload.return_value = {
        "error": False,
        "batch_response": [
            {
                "document_id": "doc-new",
                "forms": [{"url": "https://s3/upload", "fields": {"key": "abc"}}],
            }
        ],
    }
    client.upload_file_to_presigned_url.return_value = 204

    path = _make_temp_file()
    try:
        service = RecordsService(client)
        result = asyncio.run(
            service.upload_patient_record(
                "oid-1", path, title="Blood test", tags=["lab"], document_type="lr"
            )
        )
    finally:
        os.remove(path)

    # Step 1: metadata registered with file size + content type + optional fields
    args, _ = client.initiate_medical_record_upload.call_args
    assert args[0] == "oid-1"
    batch = args[1]
    assert batch[0]["files"][0]["contentType"] == "application/pdf"
    assert batch[0]["files"][0]["file_size"] > 0
    assert batch[0]["title"] == "Blood test"
    assert batch[0]["tg"] == ["lab"]
    assert batch[0]["dt"] == "lr"

    # Step 2: bytes pushed to the presigned URL with its form fields
    up_args, _ = client.upload_file_to_presigned_url.call_args
    assert up_args[0] == "https://s3/upload"
    assert up_args[1] == {"key": "abc"}
    assert isinstance(up_args[2], bytes)

    assert result["document_id"] == "doc-new"
    assert result["status"] == "uploaded"
    assert result["storage_status_code"] == 204


def test_upload_patient_record_missing_file_raises():
    client = make_mock_client()
    service = RecordsService(client)

    with pytest.raises(EkaAPIError):
        asyncio.run(service.upload_patient_record("oid-1", "/no/such/file.pdf"))

    client.initiate_medical_record_upload.assert_not_called()


def test_upload_patient_record_authorization_error_raises():
    client = make_mock_client()
    client.initiate_medical_record_upload.return_value = {
        "error": True,
        "message": "quota exceeded",
        "batch_response": [],
    }

    path = _make_temp_file()
    try:
        service = RecordsService(client)
        with pytest.raises(EkaAPIError):
            asyncio.run(service.upload_patient_record("oid-1", path))
    finally:
        os.remove(path)

    client.upload_file_to_presigned_url.assert_not_called()
