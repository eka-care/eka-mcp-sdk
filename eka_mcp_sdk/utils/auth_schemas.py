"""
Reusable authentication elicitation schemas and session enums.

This module is intended to be imported by external repos (e.g. eka-remote-mcp)
to avoid duplicating JSON schemas and session key conventions.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

try:
    from enum import StrEnum
except ImportError:  # Python < 3.11
    from enum import Enum

    class StrEnum(str, Enum):  # type: ignore[no-redef]
        pass


class MobileAuthStage(StrEnum):
    MOBILE_OTP_SENT = "MOBILE_OTP_SENT"
    MOBILE_OTP_VERIFIED = "MOBILE_OTP_VERIFIED"
    MOBILE_UHIDS_LISTED = "MOBILE_UHIDS_LISTED"
    MOBILE_UHID_SELECTED = "MOBILE_UHID_SELECTED"
    MOBILE_OTP_SENT_RETRY = "MOBILE_OTP_SENT_RETRY"


class AuthStatus(StrEnum):
    AUTHENTICATED = "AUTHENTICATED"
    UNAUTHENTICATED = "UNAUTHENTICATED"


class SessionKey(StrEnum):
    MOBILE_AUTH_STAGE = "MOBILE_AUTH_STAGE"
    MOBILE_NUMBER = "MOBILE_NUMBER"
    COUNTRY_CODE = "COUNTRY_CODE"
    MOBILE_AUTH_OTP_VALUE = "MOBILE_AUTH_OTP_VALUE"
    MOBILE_AUTH_AUTHENTICATION = "MOBILE_AUTH_AUTHENTICATION"
    MOBILE_AUTH_OTP_RETRIES = "MOBILE_AUTH_OTP_RETRIES"
    MOBILE_AUTH_UHIDS_LIST = "MOBILE_AUTH_UHIDS_LIST"
    MOBILE_AUTH_SELECTED_UHID = "MOBILE_AUTH_SELECTED_UHID"

    EMAIL_AUTH_STAGE = "EMAIL_AUTH_STAGE"
    EMAIL_ADDRESS = "EMAIL_ADDRESS"
    EMAIL_AUTH_OTP_VALUE = "EMAIL_AUTH_OTP_VALUE"
    EMAIL_AUTH_AUTHENTICATION = "EMAIL_AUTH_AUTHENTICATION"
    EMAIL_AUTH_OTP_RETRIES = "EMAIL_AUTH_OTP_RETRIES"
    EMAIL_AUTH_OTP_RESENT_COUNT = "EMAIL_AUTH_OTP_RESENT_COUNT"


ASK_MOBILE_SCHEMA: Dict[str, Any] = {
    "status": "progress",
    "is_elicitation": True,
    "component": "mobile_number",
    "input": {"method": "mobile"},
    "_meta": {
        "schema": {
            "type": "object",
            "properties": {
                "mobile_number": {
                    "type": "string",
                    "pattern": "^[6-9][0-9]{9}$",
                    "minLength": 10,
                    "maxLength": 10,
                    "description": "Enter your mobile number",
                }
            },
            "required": ["method", "mobile_number"],
        }
    },
}


ASK_OTP_SCHEMA: Dict[str, Any] = {
    "status": "progress",
    "is_elicitation": True,
    "component": "otp",
    "input": {"method": "mobile"},
    "_meta": {
        "disp_toast_msg": "OTP sent successfully.",
        "schema": {
            "type": "object",
            "properties": {
                "otp": {
                    "type": "string",
                    "pattern": "^[0-9]{6}$",
                    "minLength": 6,
                    "maxLength": 6,
                    "description": "Enter the OTP you received.",
                }
            },
            "required": ["method", "otp"],
        },
        "mcp_meta_fields": ["otp"],
    },
}


LIST_UHIDS_SCHEMA: Dict[str, Any] = {
    "status": "progress",
    "is_elicitation": True,
    "component": "pills",
    "input": {"text": "Please select the profile you want to use", "options": []},
    "tool_type": "elicitation",
    "_meta": {
        "schema": {
            "type": "object",
            "properties": {"value": {"type": "string"}},
            "required": ["value"],
        },
        "mcp_meta_fields": ["value"],
    },
}


UHID_SELECTED_SCHEMA: Dict[str, Any] = {
    "status": "success",
    "is_elicitation": True,
    "component": "success",
    "input": {},
    "_meta": {
        "disp_message": "Authenticated and profile selected successfully.",
    },
    "session_context": {},
}


ERROR_ELICITATION_SCHEMA: Dict[str, Any] = {
    "status": "failure",
    "is_elicitation": True,
    "component": "error",
    "input": {},
    "_meta": {
        "disp_message": "Something went wrong while authenticating.",
        "disp_toast_msg": "Something went wrong. Please Try Again.",
    },
    "session_context": {},
}


class UnauthenticatedError(Exception):
    def __init__(self, message: Optional[str] = None):
        self.message = message or (
            "User is not authenticated. "
            "Please authenticate first using the authentication_elicitation tool."
        )
        self.error = "unauthenticated"
        self.success = False

    def __str__(self) -> str:
        return self.message

    def to_dict(self) -> Dict[str, Any]:
        return {"error": self.error, "message": self.message, "success": False}

