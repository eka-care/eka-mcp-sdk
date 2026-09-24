"""
Patient Profile Utilities

Helper functions for building UI responses for patient profile selection
in the patient_card component format.
"""

from typing import Any, Dict, List, Optional


def build_profile_elicitation_response(
    profiles: List[Dict[str, Any]],
    page_meta: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Build the UI contract response for patient profile selection.

    Renders the profiles as selectable pills; the user's chosen
    patient_id comes back in a subsequent tool call.
    """
    resp: Dict[str, Any] = {
        "status": "progress",
        "is_elicitation": True,
        "component": "patient_card",
        "input": {
            "profiles": profiles,
        },
        "_meta": {
            "schema": {
                "type": "object",
                "properties": {
                    "patient_id": {
                        "type": "string",
                        "description": "Selected patient's identifier",
                    }
                },
                "required": ["patient_id"],
            }
        },
    }
    if page_meta:
        resp["input"]["page_meta"] = page_meta
    return resp
