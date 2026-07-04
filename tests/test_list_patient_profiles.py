"""
Unit tests for the list_patients v2 flow:
raw API response -> canonical profile contract -> tool response
(elicitation model or plain list).
"""

from unittest.mock import AsyncMock, MagicMock, patch

from eka_mcp_sdk.services.patient_service import PatientService, map_to_patient_profiles
from eka_mcp_sdk.tools.patient_tools import _list_patient_profiles_v2
from eka_mcp_sdk.utils.patient_profile_utils import build_profile_elicitation_response

RAW_LIST_RESPONSE = {
    "status": "success",
    "data": [
        {"oid": "p1", "fln": "John Doe", "mobile": "+919812345678", "dob": "1990-01-01", "gen": "M"},
        {"oid": "p2", "fln": "Jane Doe"},
    ],
    "currPageMeta": {"pageNo": 0, "pageSize": 2},
}


# ---------- map_to_patient_profiles ----------

def test_map_to_patient_profiles():
    profiles = map_to_patient_profiles(RAW_LIST_RESPONSE)
    assert profiles == [
        {"patient_id": "p1", "name": "John Doe", "mobile": "+919812345678", "dob": "1990-01-01", "gender": "M"},
        {"patient_id": "p2", "name": "Jane Doe", "mobile": None, "dob": None, "gender": None},
    ]


def test_map_to_patient_profiles_empty_and_malformed():
    assert map_to_patient_profiles({}) == []
    assert map_to_patient_profiles({"status": "success", "data": None}) == []
    assert map_to_patient_profiles(None) == []


# ---------- PatientService.list_patient_profiles ----------

async def test_list_patient_profiles_contract():
    client = MagicMock()
    client.list_patients = AsyncMock(return_value=RAW_LIST_RESPONSE)
    service = PatientService(client)

    result = await service.list_patient_profiles(page_no=0, page_size=2)

    client.list_patients.assert_awaited_once_with(0, 2, None, None, False)
    assert [p["patient_id"] for p in result["profiles"]] == ["p1", "p2"]
    assert result["page_meta"] == {"pageNo": 0, "pageSize": 2}


async def test_list_patient_profiles_no_patients():
    client = MagicMock()
    client.list_patients = AsyncMock(return_value={"status": "success", "data": []})
    service = PatientService(client)

    result = await service.list_patient_profiles(page_no=0)

    assert result["profiles"] == []
    assert result["page_meta"] is None


# ---------- build_profile_elicitation_response ----------

def test_build_profile_elicitation_response():
    profiles = map_to_patient_profiles(RAW_LIST_RESPONSE)
    resp = build_profile_elicitation_response(profiles, page_meta={"pageNo": 0})

    assert resp["status"] == "progress"
    assert resp["is_elicitation"] is True
    assert resp["component"] == "patient_card"
    assert resp["input"]["profiles"] == profiles
    assert resp["input"]["page_meta"] == {"pageNo": 0}
    assert resp["_meta"]["schema"]["required"] == ["patient_id"]


def test_build_profile_elicitation_response_without_page_meta():
    resp = build_profile_elicitation_response([{"patient_id": "p1"}])
    assert "page_meta" not in resp["input"]


# ---------- tool layer: _list_patient_profiles_v2 ----------

def _patched_tool_env(client):
    return (
        patch("eka_mcp_sdk.tools.patient_tools.get_access_token", return_value=None),
        patch("eka_mcp_sdk.tools.patient_tools.get_workspace_id", return_value="ekaemr"),
        patch("eka_mcp_sdk.tools.patient_tools.get_extra_headers", return_value={}),
        patch("eka_mcp_sdk.tools.patient_tools.ClientFactory.create_client", return_value=client),
    )


def _mock_ctx():
    ctx = MagicMock()
    ctx.info = AsyncMock()
    ctx.error = AsyncMock()
    return ctx


async def _run_v2(client, supports_elicitation):
    patches = _patched_tool_env(client) + (
        patch(
            "eka_mcp_sdk.tools.patient_tools.get_supports_elicitation",
            return_value=supports_elicitation,
        ),
    )
    for p in patches:
        p.start()
    try:
        return await _list_patient_profiles_v2(0, None, None, None, False, _mock_ctx())
    finally:
        for p in patches:
            p.stop()


async def test_v2_returns_elicitation_model_when_supported():
    client = MagicMock()
    client.list_patients = AsyncMock(return_value=RAW_LIST_RESPONSE)

    resp = await _run_v2(client, supports_elicitation=True)

    assert resp["is_elicitation"] is True
    assert resp["component"] == "patient_card"
    assert [p["patient_id"] for p in resp["input"]["profiles"]] == ["p1", "p2"]


async def test_v2_returns_plain_list_when_elicitation_unsupported():
    client = MagicMock()
    client.list_patients = AsyncMock(return_value=RAW_LIST_RESPONSE)

    resp = await _run_v2(client, supports_elicitation=False)

    assert resp["success"] is True
    assert "is_elicitation" not in resp
    assert [p["patient_id"] for p in resp["data"]["profiles"]] == ["p1", "p2"]


async def test_v2_errors_when_no_profiles():
    client = MagicMock()
    client.list_patients = AsyncMock(return_value={"status": "success", "data": []})

    resp = await _run_v2(client, supports_elicitation=True)

    assert resp["success"] is False
    assert resp["error"]["error_code"] == "NO_PROFILES_FOUND"
