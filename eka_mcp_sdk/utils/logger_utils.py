from typing import Dict, Any, Optional

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
