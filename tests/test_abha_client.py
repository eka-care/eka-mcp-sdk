"""Unit tests for AbhaClient ABHA API methods."""

import asyncio
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from eka_mcp_sdk.clients.abha_client import AbhaClient


@pytest.fixture
def client():
    """Create AbhaClient with a dummy token."""
    with patch("eka_mcp_sdk.clients.base_client.settings") as mock_settings:
        mock_settings.client_id = "test-client-id"
        mock_settings.client_secret = None
        mock_settings.api_base_url = "https://api.eka.care"
        c = AbhaClient(access_token="test-token")
    return c


@pytest.fixture
def mock_make_request(client):
    """Patch _make_request on the client instance."""
    client._make_request = AsyncMock()
    return client._make_request


class TestLoginInit:
    def test_calls_correct_endpoint(self, client, mock_make_request):
        mock_make_request.return_value = {"txn_id": "txn-123", "hint": "OTP sent"}
        result = asyncio.run(client.login_init("mobile", "9876543210"))

        mock_make_request.assert_called_once_with(
            method="POST",
            endpoint="/abdm/na/v1/profile/login/init",
            data={"method": "mobile", "identifier": "9876543210"},
        )
        assert result["txn_id"] == "txn-123"


class TestLoginVerify:
    def test_calls_correct_endpoint(self, client, mock_make_request):
        mock_make_request.return_value = {
            "txn_id": "txn-456",
            "skip_state": "abha_end",
            "profile": {"abha_number": "1234"},
            "eka": {"oid": "oid-1", "uuid": "uuid-1", "min_token": "tok"},
        }
        result = asyncio.run(client.login_verify("123456", "txn-123"))

        mock_make_request.assert_called_once_with(
            method="POST",
            endpoint="/abdm/na/v1/profile/login/verify",
            data={"otp": "123456", "txn_id": "txn-123"},
        )
        assert result["skip_state"] == "abha_end"
        assert result["eka"]["oid"] == "oid-1"


class TestLoginPhr:
    def test_calls_correct_endpoint(self, client, mock_make_request):
        mock_make_request.return_value = {
            "txn_id": "txn-789",
            "skip_state": "abha_end",
            "profile": {"abha_address": "user@abdm"},
            "eka": {"oid": "oid-2", "uuid": "uuid-2", "min_token": "tok2"},
        }
        result = asyncio.run(client.login_phr("user@abdm", "txn-456"))

        mock_make_request.assert_called_once_with(
            method="POST",
            endpoint="/abdm/na/v1/profile/login/phr",
            data={"phr_address": "user@abdm", "txn_id": "txn-456"},
        )
        assert result["eka"]["oid"] == "oid-2"


class TestGetAbhaCard:
    def test_calls_correct_endpoint_and_returns_bytes(self, client):
        """get_abha_card should make a GET request with X-Pt-Id header and return raw bytes."""
        fake_png = b"\x89PNG\r\n\x1a\nfakeimage"

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = fake_png

        client._http_client = AsyncMock()
        client._http_client.request = AsyncMock(return_value=mock_response)

        # Patch auth and settings used inside get_abha_card
        with patch("eka_mcp_sdk.clients.abha_client.settings") as mock_settings:
            mock_settings.client_id = "test-client-id"
            mock_settings.api_base_url = "https://api.eka.care"
            client._auth_manager = AsyncMock()
            client._auth_manager.get_auth_context = AsyncMock(
                return_value=MagicMock(auth_headers={"Authorization": "Bearer test-token"})
            )

            result = asyncio.run(client.get_abha_card("oid-1"))

        assert result == fake_png

        call_kwargs = client._http_client.request.call_args
        assert call_kwargs.kwargs["method"] == "GET"
        assert "oid=oid-1" in call_kwargs.kwargs["url"] or "oid-1" in str(call_kwargs.kwargs.get("params", {}))
        assert call_kwargs.kwargs["headers"]["X-Pt-Id"] == "oid-1"
