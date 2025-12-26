import httpx
from typing import Dict, Any, Optional
from abc import ABC, abstractmethod
import logging
from fastmcp.server.dependencies import get_context
from fastmcp.server.context import Context

from ..auth.manager import AuthenticationManager
from ..auth.models import EkaAPIError
from ..config.settings import EkaSettings

logger = logging.getLogger(__name__)


def _build_curl_command(method: str, url: str, headers: Dict[str, str], data: Optional[Dict[str, Any]] = None, params: Optional[Dict[str, Any]] = None) -> str:
    """Build a curl command from request parameters."""
    import urllib.parse
    
    # Start with basic curl command
    curl_parts = ['curl', '-X', method]
    
    # Add headers
    for key, value in headers.items():
        # Mask sensitive headers
        # if key.lower() in ['authorization', 'client-secret']:
        #     value = value[:20] + '...' if len(value) > 20 else '***'
        curl_parts.append(f"-H '{key}: {value}'")
    
    # Add query parameters to URL
    if params:
        query_string = urllib.parse.urlencode(params)
        url = f"{url}?{query_string}"
    
    # Add data if present
    if data:
        import json
        curl_parts.append(f"-d '{json.dumps(data)}'")
    
    # Add URL
    curl_parts.append(f"'{url}'")
    
    return ' '.join(curl_parts)


class BaseEkaClient(ABC):
    """Base client for Eka.care API interactions."""
    
    def __init__(self, access_token: Optional[str] = None, custom_headers: Optional[Dict[str, str]] = None):
        self._http_client = httpx.AsyncClient(timeout=30.0)
        self._auth_manager = AuthenticationManager(access_token)
        self._custom_headers = custom_headers or {}
        self.last_curl_command: Optional[str] = None
    
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
        
        # Try to get FastMCP context for logging (may not be available in all contexts)
        ctx: Optional[Context] = None
        try:
            ctx = get_context()
        except RuntimeError:
            # Context not available (e.g., outside of MCP request)
            pass
        
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
            
            # Generate curl command for debugging
            curl_cmd = _build_curl_command(method, url, headers, data, params)
            self.last_curl_command = curl_cmd  # Store for test access
            
            # Log using context if available, fallback to standard logger
            if ctx:
                await ctx.debug(f"API Request: {method} {endpoint}")
                if params:
                    await ctx.debug(f"Request params: {params}")
                await ctx.debug(f"Curl command: {curl_cmd}")
            else:
                logger.info(f"Making {method} request to: {url}")
                if params:
                    logger.debug(f"Request params: {params}")
                logger.debug(f"Curl command: {curl_cmd}")
            
            # Make request
            response = await self._http_client.request(
                method=method,
                url=url,
                headers=headers,
                json=data,
                params=params
            )

            # Log response status
            if ctx:
                await ctx.debug(f"API Response: {response.status_code}")
            else:
                logger.info(f"API response status: {response.status_code}")
            
            # Handle response
            if response.status_code >= 400:
                error_msg = f"API error: {response.status_code} - {response.text[:100]}"
                if ctx:
                    await ctx.error(error_msg)
                else:
                    logger.error(f"API error response: {response.text}")
                
                error_detail = await self._parse_error_response(response)
                raise EkaAPIError(
                    message=error_detail["message"],
                    status_code=response.status_code,
                    error_code=error_detail.get("error_code")
                )
            
            # Handle 204 No Content or empty responses
            if response.status_code == 204 or not response.text:
                return {"success": True, "status_code": response.status_code}
            
            try:
                response_data = response.json()
            except Exception:
                # If JSON parsing fails but status is successful, return success
                if 200 <= response.status_code < 300:
                    return {"success": True, "status_code": response.status_code, "raw_response": response.text}
                raise
            
            return response_data
            
        except httpx.RequestError as e:
            error_msg = f"Network error for {method} {url}: {str(e)}"
            if ctx:
                await ctx.error(error_msg)
            else:
                logger.error(error_msg)
            raise EkaAPIError(f"Network error: {str(e)}")
        except httpx.HTTPStatusError as e:
            error_msg = f"HTTP error for {method} {url}: {e.response.status_code}"
            if ctx:
                await ctx.error(error_msg)
            else:
                logger.error(f"HTTP error for {method} {url}: {e.response.status_code} - {e.response.text}")
            raise EkaAPIError(f"HTTP error: {e.response.status_code}", e.response.status_code)
        except Exception as e:
            error_msg = f"Unexpected error for {method} {url}: {str(e)}"
            if ctx:
                await ctx.error(error_msg)
            else:
                logger.error(error_msg)
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
