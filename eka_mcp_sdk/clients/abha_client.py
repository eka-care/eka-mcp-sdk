"""ABHA API client for ABDM login and profile operations."""

from typing import Dict, Any
import logging

from .base_client import BaseEkaClient
from ..auth.models import EkaAPIError
from ..config.settings import settings

logger = logging.getLogger(__name__)


class AbhaClient(BaseEkaClient):
    """HTTP client for ABHA/ABDM APIs. Extends BaseEkaClient for shared auth and HTTP handling."""

    def get_api_module_name(self) -> str:
        return "ABHA"

    async def login_init(self, method: str, identifier: str) -> Dict[str, Any]:
        """Initiate ABHA login by sending OTP.

        Args:
            method: Login method — "mobile", "aadhaar_number", "abha_number", or "phr_address"
            identifier: Value matching the method (e.g. 10-digit mobile number)

        Returns:
            {"txn_id": str, "hint": str}
        """
        return await self._make_request(
            method="POST",
            endpoint="/abdm/na/v1/profile/login/init",
            data={"method": method, "identifier": identifier},
        )

    async def login_verify(self, otp: str, txn_id: str) -> Dict[str, Any]:
        """Verify the login OTP.

        Args:
            otp: OTP received on the user's mobile
            txn_id: Transaction ID from login_init response

        Returns:
            {"txn_id": str, "skip_state": str, "profile": dict, "abha_profiles": list, "eka": dict, "hint": str}
        """
        return await self._make_request(
            method="POST",
            endpoint="/abdm/na/v1/profile/login/verify",
            data={"otp": otp, "txn_id": txn_id},
        )

    async def login_phr(self, phr_address: str, txn_id: str) -> Dict[str, Any]:
        """Complete login by selecting an ABHA address (PHR address).

        Args:
            phr_address: The ABHA address selected by the user (e.g. "user@abdm")
            txn_id: Transaction ID from login_verify response

        Returns:
            {"txn_id": str, "skip_state": str, "profile": dict, "eka": dict, "hint": str}
        """
        return await self._make_request(
            method="POST",
            endpoint="/abdm/na/v1/profile/login/phr",
            data={"phr_address": phr_address, "txn_id": txn_id},
        )

    async def get_abha_card(self, oid: str) -> bytes:
        """Download the ABHA card as a PNG image.

        Makes a direct HTTP request (bypassing _make_request) because the
        response is binary PNG, not JSON.

        Args:
            oid: Eka user OID from the login response's eka.oid field

        Returns:
            Raw PNG image bytes
        """
        url = f"{settings.api_base_url}/abdm/v1/profile/asset/card"
        headers = {"X-Pt-Id": oid, "client-id": settings.client_id}

        if self.access_token or settings.client_secret:
            auth_context = await self._auth_manager.get_auth_context()
            headers.update(auth_context.auth_headers)

        response = await self._http_client.request(
            method="GET",
            url=url,
            headers=headers,
            params={"oid": oid},
        )

        if response.status_code >= 400:
            error_detail = await self._parse_error_response(response)
            raise EkaAPIError(
                message=error_detail["message"],
                status_code=response.status_code,
                error_code=error_detail.get("error_code"),
            )

        return response.content
