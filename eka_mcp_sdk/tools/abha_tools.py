"""ABHA MCP tool registration."""

from typing import Any, Dict, Annotated
import logging

from fastmcp import FastMCP
from fastmcp.server.dependencies import get_access_token, AccessToken
from fastmcp.dependencies import CurrentContext
from fastmcp.server.context import Context

from ..clients.abha_client import AbhaClient
from ..services.abha_service import AbhaService
from ..auth.models import EkaAPIError

logger = logging.getLogger(__name__)


def _make_service() -> AbhaService:
    token: AccessToken | None = get_access_token()
    access_token = token.token if token else None
    return AbhaService(AbhaClient(access_token=access_token))


def register_abha_tools(mcp: FastMCP) -> None:
    """Register ABHA/ABDM MCP tools."""

    @mcp.tool(tags={"abha", "login", "abdm"})
    async def abha_send_otp(
        mobile_number: Annotated[str, "10-digit mobile number registered with ABHA"],
        ctx: Context = CurrentContext(),
    ) -> Dict[str, Any]:
        """
        Step 1 of ABHA login: Send OTP to the user's mobile number.

        Returns a txn_id that must be passed to abha_verify_otp.
        After calling this tool, ask the user for the OTP they received.

        Trigger Keywords / Phrases
        abha login, abdm login, health id login, abha mobile login,
        link abha, connect abdm, ayushman bharat login,
        create abha, abha create, create health id, health id create,
        register abha, abha registration, new abha, get abha,
        abha card, download abha card, fetch abha card
        """
        await ctx.info(f"[abha_send_otp] Sending OTP to {mobile_number}")
        try:
            service = _make_service()
            return await service.send_otp(mobile_number)
        except EkaAPIError as e:
            await ctx.error(f"[abha_send_otp] Failed: {e.message}")
            return {"success": False, "error": e.message, "status_code": e.status_code}

    @mcp.tool(tags={"abha", "login", "abdm"})
    async def abha_verify_otp(
        otp: Annotated[str, "OTP received by the user on their mobile"],
        txn_id: Annotated[str, "Transaction ID returned by abha_send_otp"],
        ctx: Context = CurrentContext(),
    ) -> Dict[str, Any]:
        """
        Step 2 of ABHA login: Verify the OTP entered by the user.

        Pass the txn_id from abha_send_otp and the OTP the user provided.

        If the response step is "select_profile", present the abha_profiles
        list to the user as a table showing Name, ABHA Address, and KYC Status
        for each profile. Then call abha_select_profile with their chosen
        abha_address.

        If the response step is "complete", the login is done. The profile
        and ABHA card (base64 PNG in abha_card field) are already included
        in the response. Show the profile and inform the user their ABHA
        card is available. Do NOT make additional tool calls to fetch the card.
        """
        await ctx.info(f"[abha_verify_otp] Verifying OTP for txn: {txn_id}")
        try:
            service = _make_service()
            return await service.verify_otp(otp, txn_id)
        except EkaAPIError as e:
            await ctx.error(f"[abha_verify_otp] Failed: {e.message}")
            return {"success": False, "error": e.message, "status_code": e.status_code}

    @mcp.tool(tags={"abha", "login", "abdm"})
    async def abha_select_profile(
        phr_address: Annotated[str, "The ABHA address selected by the user (e.g. user@abdm)"],
        txn_id: Annotated[str, "Transaction ID returned by abha_verify_otp"],
        ctx: Context = CurrentContext(),
    ) -> Dict[str, Any]:
        """
        Step 3 of ABHA login (only if needed): Select an ABHA profile.

        Call this only when abha_verify_otp returned status "select_profile".
        Pass the phr_address the user selected from the abha_profiles list
        and the txn_id from that response.

        Returns the completed profile and ABHA card (base64 PNG in abha_card
        field). Show the profile and inform the user their ABHA card is
        available. Do NOT make additional tool calls to fetch the card.
        """
        await ctx.info(f"[abha_select_profile] Selecting profile: {phr_address}")
        try:
            service = _make_service()
            return await service.select_profile(phr_address, txn_id)
        except EkaAPIError as e:
            await ctx.error(f"[abha_select_profile] Failed: {e.message}")
            return {"success": False, "error": e.message, "status_code": e.status_code}
