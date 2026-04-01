"""ABHA login orchestration service.

Manages the multi-step ABHA mobile login flow as separate steps,
each invoked by its own MCP tool call.
"""

from typing import Any, Dict
import logging
import os
import tempfile

from ..clients.abha_client import AbhaClient
from ..auth.models import EkaAPIError

logger = logging.getLogger(__name__)


class AbhaService:
    """Orchestrates the ABHA login flow as discrete steps."""

    def __init__(self, client: AbhaClient):
        self.client = client

    async def send_otp(self, mobile_number: str) -> Dict[str, Any]:
        """Step 1: Send OTP to the mobile number."""
        init_response = await self.client.login_init("mobile", mobile_number)
        return {
            "success": True,
            "step": "otp_sent",
            "txn_id": init_response["txn_id"],
            "message": f"OTP sent to mobile number. {init_response.get('hint', '')}".strip(),
            "next_action": {
                "tool": "abha_verify_otp",
                "instruction": "Ask the user for the 6-digit OTP they received on their mobile. Then call abha_verify_otp with the OTP and the txn_id from this response. Do NOT call any other ABHA tool until you have the OTP.",
            },
        }

    async def verify_otp(self, otp: str, txn_id: str) -> Dict[str, Any]:
        """Step 2: Verify the OTP."""
        verify_response = await self.client.login_verify(otp, txn_id)
        skip_state = verify_response.get("skip_state", "")
        new_txn_id = verify_response.get("txn_id", txn_id)

        if skip_state == "abha_end":
            return await self._complete_login(verify_response)

        if skip_state == "abha_select":
            abha_profiles = verify_response.get("abha_profiles", [])
            return {
                "success": True,
                "step": "select_profile",
                "txn_id": new_txn_id,
                "abha_profiles": abha_profiles,
                "next_action": {
                    "tool": "abha_select_profile",
                    "instruction": "Show the user the list of ABHA profiles above and ask them to pick one. Then call abha_select_profile with the chosen phr_address (abha_address) and the txn_id from this response.",
                },
            }

        if skip_state == "abha_create":
            return {
                "success": False,
                "error": "ABHA creation is not supported yet. Please create an ABHA account first.",
            }

        return {
            "success": False,
            "error": f"Unexpected skip_state: {skip_state}",
        }

    async def select_profile(self, phr_address: str, txn_id: str) -> Dict[str, Any]:
        """Step 3 (optional): Select an ABHA profile when multiple exist."""
        phr_response = await self.client.login_phr(phr_address, txn_id)
        return await self._complete_login(phr_response)

    async def _complete_login(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Extract profile and save ABHA card as a downloadable file."""
        eka = response.get("eka", {})
        oid = eka.get("oid")
        profile = response.get("profile", {})

        if not oid:
            return {
                "success": True,
                "step": "complete",
                "profile": profile,
                "abha_card_file": None,
                "warning": "No OID returned, could not fetch ABHA card",
            }

        card_file_path = None
        try:
            card_bytes = await self.client.get_abha_card(oid)
            if card_bytes:
                downloads_dir = os.path.expanduser("~/Downloads")
                name = profile.get("first_name", "abha").lower()
                card_file_path = os.path.join(downloads_dir, f"abha_card_{name}_{oid}.png")
                with open(card_file_path, "wb") as f:
                    f.write(card_bytes)
        except EkaAPIError as e:
            logger.warning(f"Failed to fetch ABHA card: {e.message}")
        except OSError as e:
            logger.warning(f"Failed to save ABHA card: {e}")

        return {
            "success": True,
            "step": "complete",
            "profile": profile,
            "abha_card_file": card_file_path,
            "oid": oid,
        }
