"""Unit tests for the ExtraService CRM lead flow."""

import asyncio
from unittest.mock import AsyncMock, MagicMock

from eka_mcp_sdk.clients.eka_emr_client import EkaEMRClient
from eka_mcp_sdk.services.extra_service import ExtraService


def make_mock_client():
    client = MagicMock(spec=EkaEMRClient)
    client.create_crm_lead = AsyncMock()
    return client


def test_create_crm_lead_delegates_to_client():
    client = make_mock_client()
    client.create_crm_lead.return_value = {
        "oid": "lead-123",
        "status": "created",
    }

    service = ExtraService(client)
    payload = {
        "name": "John Doe",
        "phone": "9876543210",
        "source": "mcp"
    }

    result = asyncio.run(service.create_crm_lead(payload))

    client.create_crm_lead.assert_called_once_with(payload)
    assert result["oid"] == "lead-123"
    assert result["status"] == "created"