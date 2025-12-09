import httpx
from typing import Dict, Any, Optional
from abc import ABC, abstractmethod
import logging

from ..auth.manager import AuthenticationManager
from ..auth.models import EkaAPIError
from ..config.settings import EkaSettings

logger = logging.getLogger(__name__)


class BaseEkaClient(ABC):
    """Base client for Eka.care API interactions."""
    
    def __init__(self, access_token: Optional[str] = None, custom_headers: Optional[Dict[str, str]] = None):
        self._http_client = httpx.AsyncClient(timeout=30.0)
        self._auth_manager = AuthenticationManager(access_token)
        self._custom_headers = custom_headers or {}
    
    async def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Make authenticated request to Eka.care API."""
        # Get current settings and initialize url for exception handling
        settings = EkaSettings()
        url = f"{settings.api_base_url}{endpoint}"
        
        try:
            # Get authentication context
            auth_context = await self._auth_manager.get_auth_context()
            
            # Prepare request
            headers = auth_context.auth_headers
            
            # Add client-id header for all API calls
            if not settings.client_id:
                raise EkaAPIError("EKA_CLIENT_ID environment variable is required but not set")
            headers["client-id"] = settings.client_id
            
            # Add instance custom headers
            if self._custom_headers:
                headers.update(self._custom_headers)
            
            logger.info(f"Making {method} request to: {url}")
            if params:
                logger.debug(f"Request params: {params}")
            if data:
                logger.debug(f"Request data: {data}")
            logger.debug(f"Request headers: {headers}")
            
            # Make request
            response = await self._http_client.request(
                method=method,
                url=url,
                headers=headers,
                json=data,
                params=params
            )
            
            logger.info(f"API response status: {response.status_code}")
            logger.debug(f"API response headers: {dict(response.headers)}")
            
            # Handle response
            if response.status_code >= 400:
                logger.error(f"API error response: {response.text}")
                error_detail = await self._parse_error_response(response)
                raise EkaAPIError(
                    message=error_detail["message"],
                    status_code=response.status_code,
                    error_code=error_detail.get("error_code")
                )
            
            response_data = response.json()
            logger.debug(f"API response data: {response_data}")
            
            return response_data
            
        except httpx.RequestError as e:
            logger.error(f"Request error for {method} {url}: {str(e)}")
            raise EkaAPIError(f"Network error: {str(e)}")
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error for {method} {url}: {e.response.status_code} - {e.response.text}")
            raise EkaAPIError(f"HTTP error: {e.response.status_code}", e.response.status_code)
        except Exception as e:
            logger.error(f"Unexpected error for {method} {url}: {str(e)}")
            raise EkaAPIError(f"Unexpected error: {str(e)}")
    
    async def _parse_error_response(self, response: httpx.Response) -> Dict[str, Any]:
        """Parse error response from Eka.care API."""
        try:
            error_data = response.json()
            return {
                "message": error_data.get("message", f"API error: {response.status_code}"),
                "error_code": error_data.get("error", error_data.get("code")),
                "details": error_data
            }
        except Exception:
            return {
                "message": f"API error: {response.status_code} - {response.text}",
                "error_code": None,
                "details": {"status_code": response.status_code, "response": response.text}
            }
    
    async def close(self) -> None:
        """Close HTTP client connections."""
        await self._http_client.aclose()
    
    @abstractmethod
    def get_api_module_name(self) -> str:
        """Return the name of the API module this client handles."""
        pass
