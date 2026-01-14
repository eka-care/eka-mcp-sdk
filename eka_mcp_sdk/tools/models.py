"""Pydantic models for tool parameters and validation."""

from datetime import datetime
from typing import Optional, Literal
from pydantic import BaseModel, Field, field_validator, model_validator

class PatientData(BaseModel):
    fln: str = Field(
        ..., 
        description="Full legal name"
    )
    dob: str = Field(
        ..., 
        description="Date of birth (YYYY-MM-DD)"
    )
    gen: str = Field(
        ..., 
        description="Gender"
    )
    mobile: Optional[str] = Field(
        None, 
        description="Mobile number with country code (+91...)"
    )
    email: Optional[str] = Field(
        None, 
        description="Email address"
    )
    address: Optional[str] = Field(
        None, 
        description="Physical address"
    )

class AppointmentBookingRequest(BaseModel):
    """Appointment booking request model matching Eka Care API specification."""
    
    patient_id: str = Field(
        ...,
        description="Patient's unique identifier (oid from patient lookup)",
        pattern=r"^\d+$",
        examples=["176650465340471"]
    )
    doctor_id: str = Field(
        ...,
        description="Doctor's unique identifier from get_business_entities",
        pattern=r"^do\d+$",
        examples=["do1765290197897"]
    )
    clinic_id: str = Field(
        ...,
        description="Clinic's unique identifier from get_business_entities",
        pattern=r"^c-[a-f0-9-]+$",
        examples=["c-b4c014c9c2aa415c88c9aaa7"]
    )
    date: str = Field(
        ...,
        description="Appointment date in YYYY-MM-DD format (today or future)",
        pattern=r"^\d{4}-\d{2}-\d{2}$",
        examples=["2025-12-30"]
    )
    start_time: str = Field(
        ...,
        description="Start time in HH:MM 24-hour format (e.g., 15:00 for 3pm, 12:00 for noon)",
        pattern=r"^\d{2}:\d{2}$",
        examples=["15:00", "12:00"]
    )
    end_time: str = Field(
        None,
        description="End time in HH:MM 24-hour format (default: start_time + 15 minutes)",
        pattern=r"^\d{2}:\d{2}$",
        examples=["15:30", "12:30"]
    )
    mode: Literal["INCLINIC", "VIDEO", "AUDIO"] = Field(
        default="INCLINIC",
        description="Appointment mode: INCLINIC (in-person), VIDEO (telemedicine), or AUDIO (phone call)"
    )
    reason: Optional[str] = Field(
        None,
        description="Reason for appointment or chief complaint",
        max_length=500,
        examples=["Regular checkup", "Follow-up consultation"]
    )
    
    @field_validator('date')
    @classmethod
    def validate_date_not_past(cls, v: str) -> str:
        """Validate that appointment date is not in the past."""
        try:
            appointment_date = datetime.strptime(v, "%Y-%m-%d").date()
            today = datetime.now().date()
            if appointment_date < today:
                raise ValueError(f"Appointment date cannot be in the past. Provided: {v}, Today: {today}")
            return v
        except ValueError as e:
            if "does not match format" in str(e):
                raise ValueError(f"Invalid date format. Use YYYY-MM-DD. Provided: {v}")
            raise
    
    @model_validator(mode='after')
    def set_default_end_time(self) -> 'AppointmentBookingRequest':
        """Set end_time to start_time + 15 minutes if not provided."""
        if self.end_time is None and self.start_time:
            try:
                # Parse start_time
                start_dt = datetime.strptime(self.start_time, "%H:%M")
                # Add 15 minutes
                end_dt = start_dt + timedelta(minutes=15)
                # Format back to HH:MM
                self.end_time = end_dt.strftime("%H:%M")
            except ValueError:
                raise ValueError(f"Invalid start_time format: {self.start_time}")
        
        # Validate end_time is after start_time
        if self.end_time and self.start_time:
            if self.end_time <= self.start_time:
                raise ValueError(f"End time ({self.end_time}) must be after start time ({self.start_time})")
        return self
    
    class Config:
        json_schema_extra = {
            "example": {
                "patient_id": "176650465340471",
                "doctor_id": "do1765290197897",
                "clinic_id": "c-b4c014c9c2aa415c88c9aaa7",
                "date": "2025-12-30",
                "start_time": "15:00",
                "end_time": "15:30",
                "mode": "INCLINIC",
                "reason": "Regular checkup"
            }
        }
