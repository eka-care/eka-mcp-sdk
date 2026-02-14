from typing import Any, Dict, Optional, List, Annotated, Literal
import asyncio
import logging
import json
import random
import hashlib
import hmac
import string
from datetime import datetime, timedelta
from fastmcp import FastMCP
from fastmcp.server.dependencies import get_access_token, AccessToken
from fastmcp.dependencies import CurrentContext
from fastmcp.server.context import Context
from ..utils.fastmcp_helper import readonly_tool_annotations, write_tool_annotations

from ..utils.enrichment_helpers import get_cached_data, extract_patient_summary, extract_doctor_summary

from ..clients.eka_emr_client import EkaEMRClient
from ..auth.models import EkaAPIError
from ..services.doctor_clinic_service import DoctorClinicService
from ..utils.tool_registration import get_extra_headers

logger = logging.getLogger(__name__)

otp_store: Dict[str, Dict] = {}
auth_flow_state: Dict[str, Dict] = {}

# Configuration
OTP_LENGTH = 6
OTP_EXPIRY_MINUTES = 5
MAX_ATTEMPTS = 3
SESSION_EXPIRY_HOURS = 24


def generate_otp(length: int = OTP_LENGTH) -> str:
    """Generate a random numeric OTP"""
    return ''.join(random.choices(string.digits, k=length))


def hash_otp(otp: str, secret: str = "your-secret-key") -> str:
    """Hash OTP for secure storage"""
    return hmac.new(
        secret.encode(),
        otp.encode(),
        hashlib.sha256
    ).hexdigest()


def generate_session_token() -> str:
    """Generate a secure session token"""
    return ''.join(random.choices(string.ascii_letters + string.digits, k=32))


def is_valid_email(identifier: str) -> bool:
    """Basic email validation"""
    return '@' in identifier and '.' in identifier.split('@')[1]


def is_valid_phone(identifier: str) -> bool:
    """Basic phone validation (supports +country_code format)"""
    cleaned = identifier.replace('+', '').replace('-', '').replace(' ', '')
    return cleaned.isdigit() and len(cleaned) >= 10


async def send_sms_otp(phone: str, otp: str) -> bool:
    """Simulate sending OTP via SMS"""
    print(f"[SMS] Sending OTP {otp} to {phone}")
    await asyncio.sleep(0.1)
    return True


def register_user_authentication_tools(mcp: FastMCP) -> None:
    """Register Doctor and Clinic Information MCP tools."""

    @mcp.tool(
        tags={"user", "authentication", "mobile", "verify", "otp"},
        annotations=write_tool_annotations(),
        output_schema={
            "type": "object", 
            "properties": {
                "is_elicitation": {"type": "boolean"},
                "component": {"type": "string"},
                "input": {
                    "type": "object",
                    "properties": {
                        "text": {"type": "string"},
                        "additional_info": {"type": "object"}
                    },
                }
            }
        }
    )
    async def authenticate_user(
        conversation_id: Annotated[Optional[str], "identifier for user across multiple tool calls for different stages"] = None,
        identifier: Annotated[Optional[str], "user identifier such as phone number"] = None,
        otp: Annotated[Optional[str], "OTP for authenticating the user"] = None,
        method: Annotated[Optional[Literal["SMS"]], "Authentication method: SMS (using phone number)"] = None,
        ctx: Context = CurrentContext()
    ) -> Dict[str, Any]:
        """
        Interactive authentication tool that guides users through the complete login flow.
            
        This tool handles the ENTIRE authentication process with smart elicitation:
        1. If no identifier provided → Asks for phone number
        2. Once identifier received → Sends OTP automatically
        3. If OTP not provided → Prompts user to enter the code
        4. Once OTP received → Verifies and creates authenticated session
        
        The tool maintains conversation state and guides users naturally through each step.
        
        AI agents should call this tool repeatedly with user responses and same conversation_id
        with all the information collected till then.
        
        Example Flow:
        1. Agent calls with no params → Tool asks for email/phone
        2. Agent calls with identifier → Tool sends OTP and asks user to enter it
        3. Agent calls with identifier + otp → Tool verifies and returns session

        When to Use This Tool
        Use this tool when the user verification is required to proceed further in the process.

        Trigger Keywords / Phrases
        authenticate user, verify user, mobile number verification, otp

        What to Return
        Returns dict with
        - is_elicitation marked as True if input is required from user
        - component (str) as mobile or otp to mark which component needs to be used to get the info
        - additional_info (dict) containing
            - stage for the user authentication process
                - "awaiting_identifier" stage when more info is required (with prompt for user)
                - "awaiting_otp" stage when OTP has been dispatched
                - "authenticated" stage when authentication is complete
                - "error" stage if something goes wrong
            - conversation_id to be used in subsequent tool calls
            - identifier mobile number or OTP provided
            - method as SMS
        """
        await ctx.info(f"[authenticate_user] Getting user authentication using {method}")

        try:
            # Get the available methods for user authentication from EKA for this business
            # token: AccessToken | None = get_access_token()
            # client = EkaEMRClient(access_token=token.token if token else None, custom_headers=get_extra_headers())
            # appointment_service = AppointmentService(client)
            # result = await appointment_service.get_appointment_slots(doctor_id, clinic_id, start_date, end_date)
            
            # Get or create conversation ID
            if not conversation_id:
                conversation_id = generate_session_token()

            # Get current state for this conversation
            # state = await ctx.get_state("user_auth") or {
            #     "stage": "initial",  # initial -> otp_sent -> verified
            #     "identifier": None,
            #     "request_id": None,
            #     "method": None,
            #     "attempts": 0,
            #     "created_at": datetime.now()
            # }
            state = auth_flow_state.get(conversation_id, {
                "stage": "initial",  # initial -> awaiting_identifier -> otp_sent -> verified
                "identifier": None,
                "request_id": None,
                "method": None,
                "attempts": 0,
                "created_at": datetime.now()
            })

            result = {
                "is_elicitation": True,
                "component": "mobile"
            }

            # STAGE 1: Need identifier
            if not identifier and not state.get("identifier"):
                result["input"] = {
                    "text": "To authenticate you, I need your phone number. Please provide one:",
                    "additional_info": {
                        "stage": "awaiting_identifier",
                        "message": "Please provide your phone number to begin authentication.",
                        "conversation_id": conversation_id,
                    }
                }
                auth_flow_state[conversation_id] = state
                return result

            # Update identifier if provided
            if identifier:
                # Validate format
                if is_valid_phone(identifier):
                    state["identifier"] = identifier
                    state["method"] = method or "SMS"
                else:
                    result["input"] = {
                        "text": "Please provide a valid phone number (with country code):",
                        "additional_info": {
                            "stage": "awaiting_identifier",
                            "error": "Invalid identifier format",
                            "message": "The identifier format is invalid. Please provide a valid email or phone number.",
                            "conversation_id": conversation_id,
                        }
                    }
                    return result

            # STAGE 2: Send OTP (if we have identifier but haven't sent OTP yet)
            if state.get("identifier") and state["stage"] == "initial":
                # Generate and send OTP
                otp_code = generate_otp()
                request_id = ctx.request_id
                
                # Store OTP
                otp_store[request_id] = {
                    "otp_hash": hash_otp(otp_code),
                    "identifier": state["identifier"],
                    "method": state["method"],
                    "created_at": datetime.now(),
                    "expires_at": datetime.now() + timedelta(minutes=OTP_EXPIRY_MINUTES),
                    "attempts": 0,
                    "verified": False
                }
            
                # Send OTP
                success = False
                if state["method"] == "SMS":
                    success = await send_sms_otp(state["identifier"], otp_code)
                
                if not success:
                    result["is_elicitation"] = False
                    result["input"] = {
                        "text": f"Failed to send OTP via {state['method']}. Please try again.",
                        "additional_info": {
                            "stage": "error",
                            "error": "Failed to send OTP",
                            "message": f"Failed to send OTP via {state['method']}. Please try again.",
                            "conversation_id": conversation_id,
                        }
                    }
                    return result

                # Update state
                state["stage"] = "otp_sent"
                state["request_id"] = request_id
                # await ctx.set_state("user_auth", state)
                auth_flow_state[conversation_id] = state

                result["component"] = "otp"
                result["input"] = {
                    "text": f"I've sent a {OTP_LENGTH}-digit code to {state['identifier']} via {state['method']}. Please enter the code:",
                    "additional_info": {
                        "stage": "awaiting_otp",
                        "message": f"OTP sent successfully to {state['identifier']}. The code will expire in {OTP_EXPIRY_MINUTES} minutes.",
                        "conversation_id": conversation_id,
                        "identifier": state["identifier"],
                        "method": state["method"],
                        "expires_in_minutes": OTP_EXPIRY_MINUTES,
                        "otp": otp_code  # REMOVE IN PRODUCTION - only for testing
                    }
                }
                return result

            result["component"] = "otp"
            # STAGE 3: Need OTP code
            if state["stage"] == "otp_sent" and not otp:
                result["input"] = {
                    "text": f"Please enter the {OTP_LENGTH}-digit code sent to {state['identifier']}:",
                    "additional_info": {
                        "stage": "awaiting_otp",
                        "message": "Please provide the OTP code that was sent to you.",
                        "conversation_id": conversation_id,
                        "identifier": state["identifier"],
                        "method": state["method"],
                    }
                }
                return result

            # STAGE 4: Verify OTP
            if state["stage"] == "otp_sent" and otp:
                request_id = state.get("request_id")
                
                if not request_id or request_id not in otp_store:
                    result["is_elicitation"] = False
                    result["input"] = {
                        "text": "Your OTP session has expired. Please start authentication again.",
                        "additional_info": {
                            "stage": "error",
                            "error": "OTP session expired or invalid",
                            "message": "Your OTP session has expired. Please start authentication again.",
                            "conversation_id": conversation_id,
                        }
                    }
                    # Clear state
                    # await ctx.delete_state("user_auth")
                    if conversation_id in auth_flow_state:
                        del auth_flow_state[conversation_id]
                    return result

                otp_data = otp_store[request_id]
            
                # Check if already verified
                if otp_data["verified"]:
                    result["input"] = {
                        "text": "This OTP has already been used. Please request a new one.",
                        "additional_info": {
                            "stage": "error",
                            "error": "OTP already used",
                            "message": "This OTP has already been used. Please request a new one.",
                            "conversation_id": conversation_id,
                        }
                    }
                    return result

                # Check expiration
                if datetime.now() > otp_data["expires_at"]:
                    result["is_elicitation"] = False
                    result["input"] = {
                        "text": "The OTP has expired. Please request a new one.",
                        "additional_info": {
                            "stage": "error",
                            "error": "OTP expired",
                            "message": "The OTP has expired. Please request a new one.",
                            "conversation_id": conversation_id,
                        }
                    }
                    # Clear state
                    # await ctx.delete_state("user_auth")
                    if conversation_id in auth_flow_state:
                        del auth_flow_state[conversation_id]
                    return result
                
                # Check max attempts
                if otp_data["attempts"] >= MAX_ATTEMPTS:
                    result["is_elicitation"] = False
                    result["input"] = {
                        "text": "You have exceeded the maximum number of verification attempts. Please request a new OTP.",
                        "additional_info": {
                            "stage": "error",
                            "error": "Maximum attempts exceeded",
                            "message": "You have exceeded the maximum number of verification attempts. Please request a new OTP.",
                            "conversation_id": conversation_id,
                        }
                    }
                    # Clear state
                    # await ctx.delete_state("user_auth")
                    if conversation_id in auth_flow_state:
                        del auth_flow_state[conversation_id]
                    return result
                
                # Increment attempts
                otp_data["attempts"] += 1

                # Verify OTP
                if hash_otp(otp) == otp_data["otp_hash"]:
                    # Mark as verified
                    otp_data["verified"] = True
                    
                    # Create session

                    # Update state
                    state["stage"] = "verified"
                    # await ctx.set_state("user_auth", state)
                    auth_flow_state[conversation_id] = state

                    result["is_elicitation"] = False
                    result["input"] = {
                        "text": "Authentication successful! You are now logged in.",
                        "additional_info": {
                            "stage": "authenticated",
                            "error": "Maximum attempts exceeded",
                            "message": "Authentication successful! You are now logged in.",
                            "conversation_id": conversation_id,
                            "session_expires_in_hours": SESSION_EXPIRY_HOURS,
                            "user_id": state["identifier"],
                        }
                    }
                    return result
                else:
                    attempts_left = MAX_ATTEMPTS - otp_data["attempts"]
                    result["input"] = {
                        "text": f"That code is incorrect. You have {attempts_left} attempt(s) remaining. Please try again:",
                        "additional_info": {
                            "stage": "awaiting_otp",
                            "message": f"Invalid OTP code. {attempts_left} attempts remaining.",
                            "conversation_id": conversation_id,
                            "identifier": state["identifier"],
                            "method": state["method"],
                            "attempts_remaining": attempts_left
                        }
                    }
                    return result

            # Fallback
            result["is_elicitation"] = False
            result["input"] = {
                "text": "An unexpected error occurred. Please start authentication again.",
                "additional_info": {
                    "stage": "error",
                    "error": "Invalid state",
                    "conversation_id": conversation_id,
                }
            }
            await ctx.info(f"[authenticate_user] Completed successfully\n")
            return result
        except Exception as e:
            await ctx.error(f"[authenticate_user] Failed: {e.message}\n")
            return {
                "success": False,
                "error": {
                    "message": e.message,
                    "status_code": e.status_code,
                    "error_code": e.error_code
                }
            }
