from typing import Any, Dict, Optional, List, Union, Annotated
import logging
from datetime import datetime
from fastmcp import FastMCP
from fastmcp.server.dependencies import get_access_token, AccessToken
from fastmcp.dependencies import CurrentContext
from fastmcp.server.context import Context
from ..utils.fastmcp_helper import readonly_tool_annotations, write_tool_annotations
from ..utils.deduplicator import get_deduplicator

from ..clients.eka_emr_client import EkaEMRClient
from ..auth.models import EkaAPIError
from ..services.appointment_service import AppointmentService
from .models import AppointmentBookingRequest
from ..utils.tool_registration import get_extra_headers
from ..utils.enrichment_helpers import (
    get_cached_data,
    extract_patient_summary,
    extract_doctor_summary,
    extract_clinic_summary
)

logger = logging.getLogger(__name__)


def register_appointment_tools(mcp: FastMCP) -> None:
    """Register Enhanced Appointment Management MCP tools."""
    
    @mcp.tool(
        description="Get available appointment slots for a doctor at a specific clinic on a given date. Check available slots before booking.",
        tags={"appointment", "read", "slots", "availability"},
        annotations=readonly_tool_annotations()
    )
    async def get_appointment_slots(
        doctor_id: Annotated[str, "Doctor ID (from get_business_entities)"],
        clinic_id: Annotated[str, "Clinic ID (from get_business_entities)"],
        start_date: Annotated[str, "Start date YYYY-MM-DD"],
        end_date: Annotated[str, "End date YYYY-MM-DD (max: start_date + 1)"],
        ctx: Context = CurrentContext()
    ) -> Dict[str, Any]:
        """
        Retrieve available appointment time slots for a specific doctor at a given clinic within a limited date range (same day or next day).

        When to Use This Tool
        Use this tool when the user wants to check availability before booking an appointment, rescheduling, or exploring alternative times. 
        This tool must be called before attempting to book an appointment. 
        Only valid for short-range availability checks (today or tomorrow).

        Constraints:
        - Date range must be D to D+1 only.
        - Requires valid doctor_id and clinic_id from get_business_entities.

        Trigger Keywords / Phrases
        available slots, check availability, when can I book, is the doctor free, 
        appointments today / tomorrow, book at noon / morning / afternoon, what times are open
 
        What to Return
        Returns a list of appointment slots with start_time, end_time, and available (boolean).

        If no slots are available, returns an empty slots array. Do not attempt booking within this tool.

        """
        await ctx.info(f"[get_appointment_slots] Getting slots for doctor {doctor_id} at clinic {clinic_id} from {start_date} to {end_date}")
        
        try:
            token: AccessToken | None = get_access_token()
            client = EkaEMRClient(access_token=token.token if token else None, custom_headers=get_extra_headers())
            appointment_service = AppointmentService(client)
            result = await appointment_service.get_appointment_slots(doctor_id, clinic_id, start_date, end_date)
            
            slot_count = len(result.get('slots', [])) if isinstance(result, dict) else 0
            await ctx.info(f"[get_appointment_slots] Completed successfully - {slot_count} slots available\n")
            
            return {"success": True, "data": result}
        except EkaAPIError as e:
            await ctx.error(f"[get_appointment_slots] Failed: {e.message}\n")
            return {
                "success": False,
                "error": {
                    "message": e.message,
                    "status_code": e.status_code,
                    "error_code": e.error_code
                }
            }
    
    @mcp.tool(
        description="Book appointment for a patient. Need: patient_id, doctor_id, clinic_id, date, time. Check slots first recommended.",
        tags={"appointment", "write", "book", "create"},
        annotations=write_tool_annotations()
    )
    async def book_appointment(
        booking: Annotated[
            AppointmentBookingRequest,
            """Appointment booking details with all required fields.
            
            Required fields:
            - patient_id: From list_patients or get_patient_by_mobile (e.g., "176650465340471")
            - doctor_id: From get_business_entities (e.g., "do1765290197897")
            - clinic_id: From get_business_entities (e.g., "c-b4c014c9c2aa415c88c9aaa7")
            - date: YYYY-MM-DD format (e.g., "2025-12-30")
            - start_time: HH:MM 24hr format (e.g., "15:00" for 3pm, "12:00" for noon)
            - end_time: HH:MM 24hr format (e.g., "15:30", "12:30")
            
            Optional fields:
            - mode: "INCLINIC" (default), "VIDEO", or "AUDIO"
            - reason: Visit reason (e.g., "Regular checkup")
            
            Time conversions:
            - "noon" → 12:00, "3pm" → 15:00, "3:30pm" → 15:30
            - Default duration: 30 minutes
            """
        ],
        ctx: Context = CurrentContext()
    ) -> Dict[str, Any]:
        """
        Book an appointment for a patient with a specific doctor at a clinic on a given date and time.

        When to Use This Tool
        Use this tool when the user wants to confirm and create a new appointment after selecting a specific time slot.
        This tool should be used only after patient, doctor, and clinic information is available.
        It is strongly recommended to verify slot availability using get_appointment_slots before booking.

        Trigger Keywords / Phrases
        book appointment, schedule visit, confirm booking, book with doctor, 
        schedule at noon / morning / afternoon, fix appointment, make an appointment

        What to Return
        Returns booking confirmation details including the appointment_id and associated metadata.

        If booking fails, returns an error response. This tool performs a write action and should not be retried without user confirmation.

        """
        
        # Check for duplicate request (ChatGPT multiple clients issue)
        dedup = get_deduplicator()
        dedup_params = {
            "patient_id": booking.patient_id,
            "doctor_id": booking.doctor_id,
            "clinic_id": booking.clinic_id,
            "date": booking.date,
            "start_time": booking.start_time,
            "end_time": booking.end_time
        }
        is_duplicate, cached_response = dedup.check_and_get_cached("book_appointment", **dedup_params)
        
        if is_duplicate and cached_response:
            await ctx.info("⚡ DUPLICATE REQUEST - Returning cached appointment response")
            return cached_response
        
        await ctx.info(f"[book_appointment] Booking for patient {booking.patient_id}")
        await ctx.debug(f"Details: date={booking.date}, time={booking.start_time}-{booking.end_time}, mode={booking.mode}")
        
        try:
            # Convert date and time to Unix timestamps
            date_time_start = datetime.strptime(f"{booking.date} {booking.start_time}", "%Y-%m-%d %H:%M")
            date_time_end = datetime.strptime(f"{booking.date} {booking.end_time}", "%Y-%m-%d %H:%M")
            start_timestamp = int(date_time_start.timestamp())
            end_timestamp = int(date_time_end.timestamp())
            
            # Build request body matching Eka Care API format (EkaIds tab)
            # Top-level: clinic_id, doctor_id, patient_id (snake_case)
            # Nested: appointment_details with Unix timestamps
            appointment_data = {
                "clinic_id": booking.clinic_id,
                "doctor_id": booking.doctor_id,
                "patient_id": booking.patient_id,
                "appointment_details": {
                    "start_time": start_timestamp,
                    "end_time": end_timestamp,
                    "mode": booking.mode
                }
            }
            if booking.reason:
                appointment_data["appointment_details"]["reason"] = booking.reason
            
            await ctx.debug(f"Constructed appointment data: {appointment_data}")
            token: AccessToken | None = get_access_token()
            client = EkaEMRClient(access_token=token.token if token else None, custom_headers=get_extra_headers())
            appointment_service = AppointmentService(client)
            result = await appointment_service.book_appointment(appointment_data)
            
            appointment_id = result.get('appointment_id') or result.get('appointmentId') or result.get('id')
            await ctx.info(f"[book_appointment] Success - ID: {appointment_id}\n")
            
            response = {"success": True, "data": result}
            # Cache the successful response
            dedup.cache_response("book_appointment", response, **dedup_params)
            return response
        except EkaAPIError as e:
            await ctx.error(f"[book_appointment] Failed: {e.message}\n")
            return {
                "success": False,
                "error": {
                    "message": e.message,
                    "status_code": e.status_code,
                    "error_code": e.error_code
                }
            }
    
    @mcp.tool(
        enabled=False,
        description="Get appointments with filters. Use patient_id alone OR use dates (cannot combine both).",
        tags={"appointment", "read", "list", "enriched"},
        annotations=readonly_tool_annotations() 
    )
    async def get_appointments_enriched(
        patient_id: Annotated[Optional[str], "Filter by patient (cannot use with dates)"] = None,
        doctor_id: Annotated[Optional[str], "Filter by doctor"] = None,
        clinic_id: Annotated[Optional[str], "Filter by clinic"] = None,
        start_date: Annotated[Optional[str], "From date YYYY-MM-DD (cannot use with patient_id)"] = None,
        end_date: Annotated[Optional[str], "To date YYYY-MM-DD (cannot use with patient_id)"] = None,
        page_no: int = 0,
        ctx: Context = CurrentContext()
    ) -> Dict[str, Any]:
        """
        Retrieve appointments with enriched details including patient information, doctor profiles, clinic details, and appointment status.

        When to Use This Tool
        Use this tool when the user wants to view appointment information with full context.
        This is the preferred tool for listing appointments and should be used instead of basic appointment listing tools unless minimal data is required.
        Suitable for patient views, doctor schedules, and date-based appointment reviews.

        Filter rules:
        - patient_id alone: All patient appointments
        - dates: Appointments in range (no patient_id)
        - doctor_id/clinic_id: Combine with dates.

        Trigger Keywords / Phrases
        show my appointments, list appointments, upcoming appointments, today’s appointments,
        doctor schedule, clinic appointments, appointment history, appointments this week

        Returns
        Appointments with doctor names, clinic addresses, status
        If no appointments match the filters, returns an empty appointments array.
        """
        filters = [f for f in [f"doctor={doctor_id}" if doctor_id else None, 
                              f"clinic={clinic_id}" if clinic_id else None,
                              f"patient={patient_id}" if patient_id else None,
                              f"dates={start_date} to {end_date}" if start_date or end_date else None] if f]
        filter_str = ", ".join(filters) if filters else "no filters"
        await ctx.info(f"[get_appointments_enriched] Getting enriched appointments with {filter_str}")
        
        try:
            token: AccessToken | None = get_access_token()
            client = EkaEMRClient(access_token=token.token if token else None, custom_headers=get_extra_headers())
            appointment_service = AppointmentService(client)
            result = await appointment_service.get_appointments_enriched(
                doctor_id=doctor_id,
                clinic_id=clinic_id,
                patient_id=patient_id,
                start_date=start_date,
                end_date=end_date,
                page_no=page_no
            )
            
            appointment_count = len(result.get('appointments', [])) if isinstance(result, dict) else 0
            await ctx.info(f"[get_appointments_enriched] Completed successfully - {appointment_count} appointments\n")
            
            return {"success": True, "data": result}
        except EkaAPIError as e:
            await ctx.error(f"[get_appointments_enriched] Failed: {e.message}\n")
            return {
                "success": False,
                "error": {
                    "message": e.message,
                    "status_code": e.status_code,
                    "error_code": e.error_code
                }
            }
    
    @mcp.tool(
        description = "List appointments with minimal data (IDs only) for internal or lightweight use.",
        tags={"appointment", "read", "list", "basic"},
        annotations=readonly_tool_annotations()
    )
    async def get_appointments_basic(
        doctor_id: Annotated[Optional[str], "Doctor ID"] = None,
        clinic_id: Annotated[Optional[str], "Clinic ID"] = None,
        patient_id: Annotated[Optional[str], "Patient ID"] = None,
        start_date: Annotated[Optional[str], "Start date YYYY-MM-DD"] = None,
        end_date: Annotated[Optional[str], "End date YYYY-MM-DD"] = None,
        page_no: Annotated[int, "Pagination page number"] = 0,
        ctx: Context = CurrentContext()
    ) -> Dict[str, Any]:
        """
        Retrieve a list of appointments with basic data containing entity IDs only, without patient, doctor, or clinic details.

        When to Use This Tool
        Use this tool only when raw appointment records are required. Use get_appointments_enriched otherwise.
        This tool is intended for internal workflows, debugging, or follow-up calls where entity details will be resolved separately.

        Trigger Keywords / Phrases
        raw appointments, appointment ids, basic appointment list, internal lookup,
        debug appointments, lightweight appointment data
        
        Returns:
        Basic appointments with entity IDs only
        If no appointments match the filters, returns an empty appointments array.

        """
        await ctx.info(f"[get_appointments_basic] Getting basic appointments - page {page_no}")
        
        try:
            token: AccessToken | None = get_access_token()
            client = EkaEMRClient(access_token=token.token if token else None, custom_headers=get_extra_headers())
            appointment_service = AppointmentService(client)
            result = await appointment_service.get_appointments_basic(
                doctor_id=doctor_id,
                clinic_id=clinic_id,
                patient_id=patient_id,
                start_date=start_date,
                end_date=end_date,
                page_no=page_no
            )
            
            appointment_count = len(result.get('appointments', [])) if isinstance(result, dict) else 0
            await ctx.info(f"[get_appointments_basic] Completed successfully - {appointment_count} appointments\n")
            
            return {"success": True, "data": result}
        except EkaAPIError as e:
            await ctx.error(f"[get_appointments_basic] Failed: {e.message}\n")
            return {
                "success": False,
                "error": {
                    "message": e.message,
                    "status_code": e.status_code,
                    "error_code": e.error_code
                }
            }
    
    @mcp.tool(
        description = "Get complete details for a single appointment including patient, doctor, and clinic information.",
        enabled=False,   
        tags={"appointment", "read", "details", "enriched"},
        annotations=readonly_tool_annotations()
    )
    async def get_appointment_details_enriched(
        appointment_id: Annotated[str, "Appointment ID"],
        partner_id: Annotated[Optional[str], "Use partner appointment ID if set"] = None,
        ctx: Context = CurrentContext()
    ) -> Dict[str, Any]:
        """
        Get comprehensive appointment details with complete patient, doctor, and clinic information.
        
        When to Use This Tool
        Use this tool when the user wants to view complete information for a specific appointment.
        This is the preferred tool for fetching single appointment details and should be used instead of basic appointment detail tools whenever available.
        It eliminates the need for additional API calls to resolve related entities.
        
        Trigger Keywords / Phrases
        appointment details, view appointment, show appointment information, appointment summary,
        doctor and clinic details, patient appointment record, appointment status

        What to Return
        Complete appointment details with enriched patient, doctor, and clinic information
        If the appointment is not found, returns an appropriate error response.

        """
        await ctx.info(f"[get_appointment_details_enriched] Getting enriched details for appointment: {appointment_id}")
        
        try:
            token: AccessToken | None = get_access_token()
            client = EkaEMRClient(access_token=token.token if token else None, custom_headers=get_extra_headers())
            appointment_service = AppointmentService(client)
            result = await appointment_service.get_appointment_details_enriched(appointment_id, partner_id)
            
            await ctx.info(f"[get_appointment_details_enriched] Completed successfully\n")
            
            return {"success": True, "data": result}
        except EkaAPIError as e:
            await ctx.error(f"[get_appointment_details_enriched] Failed: {e.message}\n")
            return {
                "success": False,
                "error": {
                    "message": e.message,
                    "status_code": e.status_code,
                    "error_code": e.error_code
                }
            }

    @mcp.tool(
        description = "Get basic details for a single appointment with entity IDs only.",
        enabled=False,
        tags={"appointment", "read", "details", "basic"},
        annotations=readonly_tool_annotations()
    )
    async def get_appointment_details_basic(
        appointment_id: Annotated[str, "Appointment ID"],
        partner_id: Annotated[Optional[str], "Use partner appointment ID if set"] = None,
        ctx: Context = CurrentContext()
    ) -> Dict[str, Any]:
        """
        Get basic appointment details (IDs only).
        
        Consider using get_appointment_details_enriched instead for complete information.
        Only use this if you specifically need raw appointment data without patient/doctor/clinic details.
        
        Trigger Keywords / Phrases
        basic appointment details, appointment ids, raw appointment record,
        internal lookup, debug appointment, minimal appointment data

        Returns:
        Basic appointment details with entity IDs only
        If the appointment is not found, returns an appropriate error response.
        """
        await ctx.info(f"[get_appointment_details_basic] Getting basic details for appointment: {appointment_id}")
        
        try:
            token: AccessToken | None = get_access_token()
            client = EkaEMRClient(access_token=token.token if token else None, custom_headers=get_extra_headers())
            appointment_service = AppointmentService(client)
            result = await appointment_service.get_appointment_details_basic(appointment_id, partner_id)
            
            await ctx.info(f"[get_appointment_details_basic] Completed successfully\n")
            
            return {"success": True, "data": result}
        except EkaAPIError as e:
            await ctx.error(f"[get_appointment_details_basic] Failed: {e.message}\n")
            return {
                "success": False,
                "error": {
                    "message": e.message,
                    "status_code": e.status_code,
                    "error_code": e.error_code
                }
            }
    
    @mcp.tool(
        description = "List all appointments for a patient with enriched doctor and clinic details.",
        enabled=False,
        tags={"appointment", "read", "patient", "list", "enriched"},
        annotations=readonly_tool_annotations()
    )
    async def get_patient_appointments_enriched(
        patient_id: Annotated[str, "Patient ID"],
        limit: Annotated[Optional[int], "Max records to return"] = None,
        ctx: Context = CurrentContext()
    ) -> Dict[str, Any]:
        """
        Retrieve all appointments for a specific patient with enriched doctor and clinic details.

        When to Use This Tool
        Use this tool when the user wants to view a patient’s appointment history or upcoming appointments with full contextual information.
        This is the preferred tool for listing appointments for a single patient and should be used instead of basic patient appointment listing tools.
        It provides complete doctor and clinic details without requiring additional follow-up calls.
        
        Trigger Keywords / Phrases
        patient appointments, my appointments, appointment history,
        upcoming appointments for patient, past visits, patient visit records

        What to Return        
        List of enriched appointments for the patient with doctor and clinic information
        If the patient has no appointments, returns an empty appointments array.
        """
        await ctx.info(f"[get_patient_appointments_enriched] Getting enriched appointments for patient: {patient_id}")
        
        try:
            token: AccessToken | None = get_access_token()
            client = EkaEMRClient(access_token=token.token if token else None, custom_headers=get_extra_headers())
            appointment_service = AppointmentService(client)
            result = await appointment_service.get_patient_appointments_enriched(patient_id, limit)
            
            appointment_count = len(result) if isinstance(result, list) else 0
            await ctx.info(f"[get_patient_appointments_enriched] Completed successfully - {appointment_count} appointments\n")
            
            return {"success": True, "data": result}
        except EkaAPIError as e:
            await ctx.error(f"[get_patient_appointments_enriched] Failed: {e.message}\n")
            client = EkaEMRClient(access_token=token.token if token else None, custom_headers=get_extra_headers())
            appointment_service = AppointmentService(client)
            result = await appointment_service.get_patient_appointments_enriched(patient_id, limit)
            return {"success": True, "data": result}
        except EkaAPIError as e:
            return {
                "success": False,
                "error": {
                    "message": e.message,
                    "status_code": e.status_code,
                    "error_code": e.error_code
                }
            }
    
    @mcp.tool(
        description= "List basic appointment records for a patient without doctor or clinic details.",
        enabled=False,
        tags={"appointment", "read", "patient", "list", "basic"},
        annotations=readonly_tool_annotations()
    )
    async def get_patient_appointments_basic(
        patient_id: Annotated[str, "Patient ID"],
        limit: Annotated[Optional[int], "Max records to return"] = None,
        ctx: Context = CurrentContext()
    ) -> Dict[str, Any]:
        """
        Get basic appointments for a specific patient (IDs only).
        
        When to use this tool
        Only use this if you specifically need raw appointment data without doctor/clinic details.
        Otherwise consider using get_patient_appointments_enriched instead for complete information.
        
        Trigger Keywords / Phrases
        basic patient appointments, patient appointment ids, raw patient visits,
        internal lookup, debug patient appointments, minimal appointment data
        
        Returns:
            Basic appointments with entity IDs only
            If the patient has no appointments, returns an empty appointments array.

        """
        await ctx.info(f"[get_patient_appointments_basic] Getting basic appointments for patient: {patient_id}")
        
        try:
            token: AccessToken | None = get_access_token()
            client = EkaEMRClient(access_token=token.token if token else None, custom_headers=get_extra_headers())
            appointment_service = AppointmentService(client)
            result = await appointment_service.get_patient_appointments_basic(patient_id, limit)
            
            appointment_count = len(result) if isinstance(result, list) else 0
            await ctx.info(f"[get_patient_appointments_basic] Completed successfully - {appointment_count} appointments\n")
            
            return {"success": True, "data": result}
        except EkaAPIError as e:
            await ctx.error(f"[get_patient_appointments_basic] Failed: {e.message}\n")
            return {
                "success": False,
                "error": {
                    "message": e.message,
                    "status_code": e.status_code,
                    "error_code": e.error_code
                }
            }
    
    @mcp.tool(
        description = "Update an existing appointment’s status, timing, or other supported attributes.",
        enabled=False,
        tags={"appointment", "write", "update"},
        annotations=write_tool_annotations()
    )
    async def update_appointment(
        appointment_id: Annotated[str, "Appointment ID"],
        update_data: Annotated[Dict[str, Any], "Fields to update"],
        partner_id: Annotated[Optional[str], "Use partner appointment ID if set"] = None,
        ctx: Context = CurrentContext()
    ) -> Dict[str, Any]:
        """
        Update an existing appointment.

        When to Use This Tool
        Use this tool when the user wants to change an existing appointment, such as rescheduling, cancelling, or updating appointment-related details.
        This tool should be used only after a valid appointment has been identified.
        User intent should be explicit before performing any update, as this is a write operation.
        
        Trigger Keywords / Phrases
        reschedule appointment, update appointment, cancel appointment, change appointment time,
        modify booking, update status, mark appointment, edit appointment

        Returns:
            Updated appointment details
            If the update fails, returns an error response. This action should not be retried automatically without user confirmation.

        """
        await ctx.info(f"[update_appointment] Updating appointment {appointment_id} - fields: {list(update_data.keys())}")
        
        try:
            token: AccessToken | None = get_access_token()
            client = EkaEMRClient(access_token=token.token if token else None, custom_headers=get_extra_headers())
            appointment_service = AppointmentService(client)
            result = await appointment_service.update_appointment(appointment_id, update_data, partner_id)
            
            await ctx.info(f"[update_appointment] Completed successfully\n")
            
            return {"success": True, "data": result}
        except EkaAPIError as e:
            await ctx.error(f"[update_appointment] Failed: {e.message}\n")
            return {
                "success": False,
                "error": {
                    "message": e.message,
                    "status_code": e.status_code,
                    "error_code": e.error_code
                }
            }
    
    @mcp.tool(
        description = "Mark an appointment as completed with final status and notes.",
        tags={"appointment", "write", "complete", "status"},
        annotations=write_tool_annotations()
    )
    async def complete_appointment(
        appointment_id: Annotated[str, "Appointment ID"],
        completion_data: Annotated[Dict[str, Any], "Completion status and notes"],
        ctx: Context = CurrentContext()
    ) -> Dict[str, Any]:
        """
        Mark an appointment as completed.

        When to Use This Tool
        Use this tool when the appointment has concluded and needs to be marked as completed in the system.
        This tool should be called only after the appointment has taken place.
        User intent should be explicit, as this action updates the appointment’s final state.

        Trigger Keywords / Phrases
        complete appointment, mark as completed, finish appointment,
        close visit, appointment done, visit completed
        
        Returns:
            Completion confirmation with updated appointment status.
            If completion fails, returns an error response. This action should not be retried automatically without user confirmation.

        """
        await ctx.info(f"[complete_appointment] Completing appointment: {appointment_id}")
        
        try:
            token: AccessToken | None = get_access_token()
            client = EkaEMRClient(access_token=token.token if token else None, custom_headers=get_extra_headers())
            appointment_service = AppointmentService(client)
            result = await appointment_service.complete_appointment(appointment_id, completion_data)
            
            await ctx.info(f"[complete_appointment] Completed successfully\n")
            
            return {"success": True, "data": result}
        except EkaAPIError as e:
            await ctx.error(f"[complete_appointment] Failed: {e.message}\n")
            return {
                "success": False,
                "error": {
                    "message": e.message,
                    "status_code": e.status_code,
                    "error_code": e.error_code
                }
            }
    
    @mcp.tool(
        description = "Cancel an existing appointment and record cancellation details.",
        tags={"appointment", "write", "cancel", "destructive"},
        annotations=write_tool_annotations(destructive=True)
    )
    async def cancel_appointment(
        appointment_id: Annotated[str, "Appointment ID"],
        cancel_data: Annotated[Dict[str, Any], "Cancellation reason and notes"],
        ctx: Context = CurrentContext()
    ) -> Dict[str, Any]:
        """
        Cancel an appointment.

        When to Use This Tool
        Use this tool when the user explicitly wants to cancel an appointment.
        This action should be performed only after confirming the correct appointment with the user.
        Because this is a destructive write operation, intent must be clear and unambiguous.
        
        Args:
            appointment_id: Appointment's unique identifier
            cancel_data: Cancellation details including reason and notes
        
        Returns:
            Cancellation confirmation with updated appointment status
        """
        await ctx.info(f"[cancel_appointment] Cancelling appointment: {appointment_id}")
        
        try:
            token: AccessToken | None = get_access_token()
            client = EkaEMRClient(access_token=token.token if token else None, custom_headers=get_extra_headers())
            appointment_service = AppointmentService(client)
            result = await appointment_service.cancel_appointment(appointment_id, cancel_data)
            
            await ctx.info(f"[cancel_appointment] Completed successfully\n")
            
            return {"success": True, "data": result}
        except EkaAPIError as e:
            await ctx.error(f"[cancel_appointment] Failed: {e.message}\n")
            return {
                "success": False,
                "error": {
                    "message": e.message,
                    "status_code": e.status_code,
                    "error_code": e.error_code
                }
            }
    
    @mcp.tool(
        description = "Change an existing appointment to a new date or time.",
        enabled=False,
        tags={"appointment", "write", "reschedule"},
        annotations=write_tool_annotations()
    )
    async def reschedule_appointment(
        appointment_id: Annotated[str, "Appointment ID"],
        reschedule_data: Annotated[Dict[str, Any], "New date and time"],
        ctx: Context = CurrentContext()
    ) -> Dict[str, Any]:
        """
        Reschedule an appointment to a new date/time.

        When to Use This Tool
        Use this tool when the user explicitly wants to move an existing appointment to a different date or time.
        This tool should be used only after confirming the target appointment and the new timing.
        It is recommended to verify availability for the new time slot before rescheduling.

        Trigger Keywords / Phrases
        reschedule appointment, move appointment, change appointment time,
        shift booking, postpone appointment, appointment moved
        
        Returns:
            Rescheduled appointment details with new timing
            If rescheduling fails, returns an error response. This action should not be retried automatically without user confirmation.

        """
        await ctx.info(f"[reschedule_appointment] Rescheduling appointment: {appointment_id}")
        
        try:
            token: AccessToken | None = get_access_token()
            client = EkaEMRClient(access_token=token.token if token else None, custom_headers=get_extra_headers())
            appointment_service = AppointmentService(client)
            result = await appointment_service.reschedule_appointment(appointment_id, reschedule_data)
            
            await ctx.info(f"[reschedule_appointment] Completed successfully\n")
            
            return {"success": True, "data": result}
        except EkaAPIError as e:
            await ctx.error(f"[reschedule_appointment] Failed: {e.message}\n")
            return {
                "success": False,
                "error": {
                    "message": e.message,
                    "status_code": e.status_code,
                    "error_code": e.error_code
                }
            }
    


# This function is now handled by the AppointmentService class
# Keeping for backward compatibility if needed
async def _enrich_appointments_data(client: EkaEMRClient, appointments_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Unified function to enrich appointment data with patient, doctor, and clinic details.
    Works with both single appointments and lists of appointments.
    """
    try:
        # Handle different input structures
        appointments_list = []
        if "appointments" in appointments_data:
            appointments_list = appointments_data.get("appointments", [])
        elif isinstance(appointments_data, list):
            appointments_list = appointments_data
        elif isinstance(appointments_data, dict) and appointments_data.get("appointment_id"):
            # Single appointment
            appointments_list = [appointments_data]
        else:
            # Unknown structure, return as is
            return appointments_data
        
        if not appointments_list:
            return appointments_data
        
        enriched_appointments = []
        
        # Cache for avoiding duplicate API calls
        patients_cache = {}
        doctors_cache = {}
        clinics_cache = {}
        
        for appointment in appointments_list:
            enriched_appointment = appointment.copy()
            
            # Enrich with patient details
            patient_id = appointment.get("patient_id")
            if patient_id:
                patient_info = await get_cached_data(
                    client.get_patient_details, patient_id, patients_cache
                )
                if patient_info:
                    enriched_appointment["patient_details"] = extract_patient_summary(patient_info)
            
            # Enrich with doctor details
            doctor_id = appointment.get("doctor_id")
            if doctor_id:
                doctor_info = await get_cached_data(
                    client.get_doctor_profile, doctor_id, doctors_cache
                )
                if doctor_info:
                    enriched_appointment["doctor_details"] = extract_doctor_summary(doctor_info)
            
            # Enrich with clinic details
            clinic_id = appointment.get("clinic_id")
            if clinic_id:
                clinic_info = await get_cached_data(
                    client.get_clinic_details, clinic_id, clinics_cache
                )
                if clinic_info:
                    enriched_appointment["clinic_details"] = extract_clinic_summary(clinic_info)
            
            enriched_appointments.append(enriched_appointment)
        
        # Return enriched data with original structure preserved
        if "appointments" in appointments_data:
            result = appointments_data.copy()
            result["appointments"] = enriched_appointments
            return result
        elif isinstance(appointments_data, list):
            return enriched_appointments
        else:
            # Single appointment case
            return enriched_appointments[0] if enriched_appointments else appointments_data
        
    except Exception as e:
        logger.warning(f"Failed to enrich appointments data: {str(e)}")
        return appointments_data



#Appointment ID: api-6ae89715-bda5-4bf0-9aa1-69265dce9a4b


