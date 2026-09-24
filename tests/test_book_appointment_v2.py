"""
Unit tests for the book_appointment v2 flow:
tool validation (auth + required fields) -> service orchestration
(doctor-in-clinic check, slot availability, booking) -> client API call.
"""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from eka_mcp_sdk.auth.models import EkaAPIError
from eka_mcp_sdk.services.appointment_service import AppointmentService
from eka_mcp_sdk.tools.appointment_tools import _book_appointment_v2
from eka_mcp_sdk.tools.models import AppointmentBookingRequest

BOOKING_DATE = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")

ENTITIES = {"clinics": [{"clinic_id": "c1", "doctors": ["d1"]}]}


def _schedule(available: bool):
    return {
        "data": {
            "schedule": {
                "c1": [
                    {
                        "slots": [
                            {
                                "s": f"{BOOKING_DATE}T10:00:00",
                                "e": f"{BOOKING_DATE}T10:15:00",
                                "available": available,
                            },
                            {
                                "s": f"{BOOKING_DATE}T10:15:00",
                                "e": f"{BOOKING_DATE}T10:30:00",
                                "available": True,
                            },
                        ]
                    }
                ]
            }
        }
    }


def _service_client(available: bool = True):
    client = MagicMock()
    client.get_business_entities = AsyncMock(return_value=ENTITIES)
    client.get_appointment_slots_raw = AsyncMock(return_value=_schedule(available))
    client.book_appointment = AsyncMock(return_value={"appointment_id": "a1"})
    return client


async def _book(service):
    return await service.book_appointment_v2(
        patient_id="p1",
        doctor_id="d1",
        clinic_id="c1",
        date=BOOKING_DATE,
        start_time="10:00",
        end_time="10:30",
        reason="checkup",
    )


# ---------- AppointmentService.book_appointment_v2 ----------

async def test_service_books_available_slot():
    client = _service_client(available=True)
    result = await _book(AppointmentService(client))

    assert result["booked"] is True
    assert result["appointment"] == {"appointment_id": "a1"}
    # end time comes from the actual slot in the schedule, not the request
    assert result["booked_slot"] == {"date": BOOKING_DATE, "start_time": "10:00", "end_time": "10:15"}

    payload = client.book_appointment.await_args.args[0]
    assert payload["patient_id"] == "p1"
    assert payload["doctor_id"] == "d1"
    assert payload["clinic_id"] == "c1"
    assert payload["appointment_details"]["mode"] == "INCLINIC"
    assert payload["appointment_details"]["reason"] == "checkup"


async def test_service_returns_alternates_for_unavailable_slot():
    client = _service_client(available=False)
    result = await _book(AppointmentService(client))

    assert result["booked"] is False
    assert result["appointment"] is None
    assert result["alternate_slots"], "expected alternate slots for the unavailable request"
    client.book_appointment.assert_not_awaited()


async def test_service_rejects_doctor_not_in_clinic():
    client = _service_client()
    service = AppointmentService(client)
    with pytest.raises(EkaAPIError) as exc:
        await service.book_appointment_v2(
            patient_id="p1", doctor_id="d1", clinic_id="other-clinic",
            date=BOOKING_DATE, start_time="10:00", end_time="10:30",
        )
    assert exc.value.error_code == "DOCTOR_NOT_IN_CLINIC"
    client.get_appointment_slots_raw.assert_not_awaited()


async def test_service_rejects_missing_schedule():
    client = _service_client()
    client.get_appointment_slots_raw = AsyncMock(return_value={"data": {"schedule": {}}})
    with pytest.raises(EkaAPIError) as exc:
        await _book(AppointmentService(client))
    assert exc.value.error_code == "NO_SCHEDULE"


async def test_service_rejects_slot_not_in_schedule():
    client = _service_client()
    service = AppointmentService(client)
    with pytest.raises(EkaAPIError) as exc:
        await service.book_appointment_v2(
            patient_id="p1", doctor_id="d1", clinic_id="c1",
            date=BOOKING_DATE, start_time="23:45", end_time="23:59",
        )
    assert exc.value.error_code == "SLOT_NOT_FOUND"


# ---------- tool layer: _book_appointment_v2 ----------

def _booking(**overrides):
    fields = {
        "patient_id": "p1",
        "doctor_id": "d1",
        "clinic_id": "c1",
        "date": BOOKING_DATE,
        "start_time": "10:00",
        "end_time": "10:30",
    }
    fields.update(overrides)
    return AppointmentBookingRequest(**fields)


def _mock_ctx():
    ctx = MagicMock()
    ctx.info = AsyncMock()
    ctx.error = AsyncMock()
    return ctx


def _mock_token(token="tok"):
    access_token = MagicMock()
    access_token.token = token
    return access_token


async def _run_v2(booking, client, token="tok"):
    with patch("eka_mcp_sdk.tools.appointment_tools.get_access_token",
               return_value=_mock_token(token) if token else None), \
         patch("eka_mcp_sdk.tools.appointment_tools.get_workspace_id", return_value="ekaemr"), \
         patch("eka_mcp_sdk.tools.appointment_tools.get_extra_headers", return_value={}), \
         patch("eka_mcp_sdk.tools.appointment_tools.ClientFactory.create_client", return_value=client):
        return await _book_appointment_v2(booking, _mock_ctx())


async def test_v2_requires_authorization():
    from eka_mcp_sdk.tools.appointment_tools import settings
    with patch.object(settings, "client_secret", None):
        resp = await _run_v2(_booking(), _service_client(), token=None)
    assert resp["success"] is False
    assert resp["error"]["error_code"] == "UNAUTHORIZED"


async def test_v2_reports_missing_required_fields():
    resp = await _run_v2(_booking(patient_id=None), _service_client())
    assert resp["success"] is False
    assert resp["error"]["error_code"] == "MISSING_REQUIRED_FIELDS"
    assert "patient_id" in resp["error"]["message"]


async def test_v2_books_successfully():
    resp = await _run_v2(_booking(), _service_client(available=True))
    assert resp["success"] is True
    assert resp["data"] == {"appointment_id": "a1"}
    assert resp["booked_slot"]["end_time"] == "10:15"


async def test_v2_returns_unavailable_response_with_alternates():
    resp = await _run_v2(_booking(), _service_client(available=False))
    assert resp["success"] is False
    assert resp["slot_unavailable"] is True
    assert resp["alternate_slots"]
    assert resp["error"]["error_code"] == "SLOT_UNAVAILABLE"


async def test_v2_maps_service_error_to_envelope():
    resp = await _run_v2(_booking(clinic_id="other-clinic"), _service_client())
    assert resp["success"] is False
    assert resp["error"]["error_code"] == "DOCTOR_NOT_IN_CLINIC"
