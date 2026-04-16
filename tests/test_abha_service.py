"""Unit tests for AbhaService login flow orchestration."""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock
from eka_mcp_sdk.services.abha_service import AbhaService
from eka_mcp_sdk.clients.abha_client import AbhaClient


def make_mock_client():
    client = MagicMock(spec=AbhaClient)
    client.login_init = AsyncMock()
    client.login_verify = AsyncMock()
    client.login_phr = AsyncMock()
    client.get_abha_card = AsyncMock()
    return client


VERIFY_RESPONSE_ABHA_END = {
    "txn_id": "txn-456",
    "skip_state": "abha_end",
    "profile": {"abha_number": "1234", "abha_address": "user@abdm", "first_name": "Test"},
    "abha_profiles": [],
    "eka": {"oid": "oid-1", "uuid": "uuid-1", "min_token": "tok"},
    "hint": "",
}

VERIFY_RESPONSE_ABHA_SELECT = {
    "txn_id": "txn-456",
    "skip_state": "abha_select",
    "profile": {},
    "abha_profiles": [
        {"abha_address": "alice@abdm", "name": "Alice", "kyc_verified": "verified"},
        {"abha_address": "bob@abdm", "name": "Bob", "kyc_verified": "pending"},
    ],
    "eka": {},
    "hint": "",
}

LOGIN_PHR_RESPONSE = {
    "txn_id": "txn-789",
    "skip_state": "abha_end",
    "profile": {"abha_address": "alice@abdm", "first_name": "Alice"},
    "abha_profiles": [],
    "eka": {"oid": "oid-2", "uuid": "uuid-2", "min_token": "tok2"},
    "hint": "",
}

FAKE_CARD = b"\x89PNG\r\n\x1a\nfakecard"


class TestSendOtp:
    def test_sends_otp_and_returns_txn_id(self):
        client = make_mock_client()
        client.login_init.return_value = {"txn_id": "txn-123", "hint": "OTP sent"}

        service = AbhaService(client)
        result = asyncio.run(service.send_otp("9876543210"))

        client.login_init.assert_called_once_with("mobile", "9876543210")
        assert result["success"] is True
        assert result["txn_id"] == "txn-123"
        assert result["step"] == "otp_sent"
        assert result["next_action"]["tool"] == "abha_verify_otp"


class TestVerifyOtpAbhaEnd:
    def test_single_profile_returns_complete(self):
        client = make_mock_client()
        client.login_verify.return_value = VERIFY_RESPONSE_ABHA_END
        client.get_abha_card.return_value = FAKE_CARD

        service = AbhaService(client)
        result = asyncio.run(service.verify_otp("123456", "txn-123"))

        client.login_verify.assert_called_once_with("123456", "txn-123")
        client.get_abha_card.assert_called_once_with("oid-1")
        assert result["success"] is True
        assert result["step"] == "complete"
        assert result["profile"]["abha_number"] == "1234"
        assert result["abha_card"]["content_type"] == "image/png"
        assert result["abha_card"]["data"] is not None


class TestVerifyOtpAbhaSelect:
    def test_multiple_profiles_returns_select(self):
        client = make_mock_client()
        client.login_verify.return_value = VERIFY_RESPONSE_ABHA_SELECT

        service = AbhaService(client)
        result = asyncio.run(service.verify_otp("123456", "txn-123"))

        assert result["success"] is True
        assert result["step"] == "select_profile"
        assert result["txn_id"] == "txn-456"
        assert len(result["abha_profiles"]) == 2
        assert result["abha_profiles"][0]["kyc_verified"] == "verified"
        assert result["abha_profiles"][1]["kyc_verified"] == "pending"
        assert result["next_action"]["tool"] == "abha_select_profile"
        client.get_abha_card.assert_not_called()


class TestVerifyOtpAbhaCreate:
    def test_returns_unsupported(self):
        client = make_mock_client()
        client.login_verify.return_value = {
            **VERIFY_RESPONSE_ABHA_END,
            "skip_state": "abha_create",
        }

        service = AbhaService(client)
        result = asyncio.run(service.verify_otp("123456", "txn-123"))

        assert result["success"] is False
        assert "not supported" in result["error"].lower()
        client.get_abha_card.assert_not_called()


class TestSelectProfile:
    def test_selects_profile_and_returns_complete(self):
        client = make_mock_client()
        client.login_phr.return_value = LOGIN_PHR_RESPONSE
        client.get_abha_card.return_value = FAKE_CARD

        service = AbhaService(client)
        result = asyncio.run(service.select_profile("alice@abdm", "txn-456"))

        client.login_phr.assert_called_once_with("alice@abdm", "txn-456")
        client.get_abha_card.assert_called_once_with("oid-2")
        assert result["success"] is True
        assert result["step"] == "complete"
        assert result["profile"]["abha_address"] == "alice@abdm"
        assert result["abha_card"]["content_type"] == "image/png"
