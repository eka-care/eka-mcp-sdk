"""Unit tests for the RecordsService medical-records flow."""

import asyncio
import os
import tempfile
from unittest.mock import AsyncMock, MagicMock

import httpx
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


def _authorized_upload_client():
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
    return client


# IP-literal hosts keep these tests offline (no real DNS lookup).
PUBLIC_URL = "https://93.184.216.34/report"


def test_upload_patient_record_from_file_url():
    client = _authorized_upload_client()
    content = b"\x89PNG\r\n\x1a\n fake image"
    client.download_file = AsyncMock(return_value=content)

    result = asyncio.run(
        RecordsService(client).upload_patient_record("oid-1", file_url=PUBLIC_URL)
    )

    client.download_file.assert_called_once_with(PUBLIC_URL, 5 * 1024 * 1024)
    args, _ = client.initiate_medical_record_upload.call_args
    assert args[1][0]["files"][0] == {"contentType": "image/png", "file_size": len(content)}
    up_args, _ = client.upload_file_to_presigned_url.call_args
    assert up_args[2] == content
    assert result["content_type"] == "image/png"
    assert result["filename"] == "record.png"


def test_upload_patient_record_rejects_unsupported_file_type():
    client = make_mock_client()
    client.download_file = AsyncMock(return_value=b"just some text")

    with pytest.raises(EkaAPIError, match="Unsupported file type"):
        asyncio.run(RecordsService(client).upload_patient_record("oid-1", file_url=PUBLIC_URL))

    client.initiate_medical_record_upload.assert_not_called()


@pytest.mark.parametrize(
    "file_url",
    [
        "http://93.184.216.34/report.pdf",  # not https
        "https://127.0.0.1/report.pdf",  # loopback
        "https://169.254.169.254/latest/meta-data",  # cloud metadata endpoint
        "https://10.0.0.5/report.pdf",  # private network
        "not a url",
        "https://93.184.216.34:99999/report.pdf",  # invalid port
        "https://[::1/report.pdf",  # malformed IPv6 host
    ],
)
def test_upload_patient_record_rejects_unsafe_file_url(file_url):
    client = make_mock_client()
    client.download_file = AsyncMock()

    with pytest.raises(EkaAPIError):
        asyncio.run(RecordsService(client).upload_patient_record("oid-1", file_url=file_url))

    client.download_file.assert_not_called()


def test_upload_patient_record_requires_file_url_or_file_path():
    client = make_mock_client()

    with pytest.raises(EkaAPIError):
        asyncio.run(RecordsService(client).upload_patient_record("oid-1"))

    client.initiate_medical_record_upload.assert_not_called()


def _client_with_transport(handler):
    client = EkaEMRClient(access_token="token")
    client._http_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return client


def test_download_file_returns_content():
    client = _client_with_transport(lambda request: httpx.Response(200, content=b"%PDF ok"))

    assert asyncio.run(client.download_file("https://files/report", 1024)) == b"%PDF ok"


def test_download_file_rejects_oversized_file():
    client = _client_with_transport(lambda request: httpx.Response(200, content=b"x" * 2048))

    with pytest.raises(EkaAPIError, match="maximum allowed size"):
        asyncio.run(client.download_file("https://files/report", 1024))


def test_download_file_does_not_follow_redirects():
    client = _client_with_transport(
        lambda request: httpx.Response(302, headers={"location": "https://10.0.0.1/"})
    )

    with pytest.raises(EkaAPIError, match="redirects"):
        asyncio.run(client.download_file("https://files/report", 1024))


def test_download_file_times_out():
    async def slow_handler(request):
        await asyncio.sleep(1)
        return httpx.Response(200, content=b"%PDF late")

    client = _client_with_transport(slow_handler)

    with pytest.raises(EkaAPIError, match="timed out"):
        asyncio.run(client.download_file("https://files/report", 1024, timeout_seconds=0.1))


def test_download_file_wraps_network_errors():
    def failing_handler(request):
        raise httpx.ConnectError("connection refused", request=request)

    client = _client_with_transport(failing_handler)

    with pytest.raises(EkaAPIError, match="Network error"):
        asyncio.run(client.download_file("https://files/report", 1024))
