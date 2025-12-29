# Logging Architecture & FastMCP Context

This project uses a **layered logging architecture** where FastMCP context logging is used **only in the tools layer**, while lower layers (services, clients, auth) use standard Python logging. This design ensures the SDK can be used as a standalone library without FastMCP dependencies.

## 🎯 Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│  Tools Layer (eka_mcp_sdk/tools/)                       │
│  • FastMCP-aware - ONLY layer with FastMCP imports     │
│  • Uses: await ctx.info(), ctx.debug(), ctx.error()   │
│  • Purpose: MCP client visibility (Claude Desktop)     │
└─────────────────────────────────────────────────────────┘
                      ↓ calls
┌─────────────────────────────────────────────────────────┐
│  Services Layer (eka_mcp_sdk/services/)                 │
│  • Pure Python - NO FastMCP imports                    │
│  • Uses: logger.info(), logger.debug()                 │
│  • Purpose: Business logic, reusable services          │
└─────────────────────────────────────────────────────────┘
                      ↓ calls
┌─────────────────────────────────────────────────────────┐
│  Clients Layer (eka_mcp_sdk/clients/)                   │
│  • Pure Python - NO FastMCP imports                    │
│  • Uses: logger.debug() for API requests/responses     │
│  • Purpose: HTTP API communication                      │
└─────────────────────────────────────────────────────────┘
                      ↓ uses
┌─────────────────────────────────────────────────────────┐
│  Auth Layer (eka_mcp_sdk/auth/)                         │
│  • Pure Python - NO FastMCP imports                    │
│  • Uses: logger.debug() for auth operations            │
│  • Purpose: Authentication management                   │
└─────────────────────────────────────────────────────────┘
```

## 🎯 Why This Architecture?

### 1. **Framework Agnostic Lower Layers**
Lower layers have NO FastMCP dependencies, making them usable as a standard Python library:

```python
# Can be used anywhere - no FastMCP requirement
from eka_mcp_sdk.services import PatientService
from eka_mcp_sdk.clients.eka_emr_client import EkaEMRClient

client = EkaEMRClient(access_token="...")
service = PatientService(client)
result = await service.search_patients("john")  # ✅ Works without FastMCP!
```

### 2. **CrewAI/LangChain Compatible**
Services work in any orchestrator:

```python
from crewai import Tool
from eka_mcp_sdk.services import PatientService

def create_search_tool():
    service = PatientService(client)
    
    def search_wrapper(prefix: str):
        return asyncio.run(service.search_patients(prefix))
    
    return Tool(name="search_patients", func=search_wrapper)
```

### 3. **Dual Logging Visibility**

**When used as MCP Server:**
- **Client sees**: FastMCP context logs from Tools layer (in Claude Desktop, VS Code, etc.)
- **Server logs**: Python logging from all layers (in server console/files)

**When used as direct library:**
- **You see**: Only Python logging (no FastMCP required!)

## Key Benefits of FastMCP Context Logging

When used as an MCP server, FastMCP context provides:

- **Client-Side Visibility**: Logs appear in MCP client log files (VS Code, Claude Desktop, Cursor, etc.)
- **Standardized Levels**: DEBUG, INFO, ERROR for consistent logging
- **Request Context**: Each request gets isolated logging context
- **No Infrastructure**: No need to configure separate logging systems

## Logging Levels

### `ctx.debug(message)`
Detailed diagnostic information for debugging:
- API request parameters
- Response status codes
- Internal flow details
- Configuration values

**Example:**
```python
await ctx.debug(f"API Request: {method} {endpoint}")
await ctx.debug(f"Request params: {params}")
```

### `ctx.info(message)`
High-level operational information:
- Tool entry points
- Major operations
- Success confirmations
- Record counts

**Example:**
```python
await ctx.info(f"Searching patients with prefix: {prefix}")
await ctx.info(f"Found {count} patients matching search criteria")
```

### `ctx.error(message)`
Error conditions and failures:
- API errors with status codes
- Network failures
- Unexpected exceptions
- Validation errors

**Example:**
```python
await ctx.error(f"Patient search failed: {e.message} (status: {e.status_code})")
await ctx.error(f"Network error: {str(e)}")
```

### `ctx.warning(message)` *(optional)*
Non-critical issues:
- Deprecated parameter usage
- Fallback behavior
- Performance concerns

## Implementation Patterns

### 1. Tools Layer (WITH FastMCP Context) ✅ CORRECT

Use `CurrentContext()` dependency injection in tool functions:

```python
from fastmcp.dependencies import CurrentContext
from fastmcp.server.context import Context

@mcp.tool()
async def search_patients(
    prefix: str,
    ctx: Context = CurrentContext()  # Auto-injected, excluded from schema
) -> Dict[str, Any]:
    await ctx.info(f"Searching patients with prefix: {prefix}")
    await ctx.debug(f"Search parameters - limit: {limit}")
    
    try:
        # Call service layer (pure Python, no FastMCP)
        result = await patient_service.search_patients(prefix, limit)
        
        # Log success
        await ctx.info(f"Found {len(result)} patients")
        logger.info(f"Search successful: {len(result)} results")  # Also log to Python
        
        return {"success": True, "data": result}
        
    except EkaAPIError as e:
        # Log errors to both
        await ctx.error(f"Search failed: {e.message}")
        logger.error(f"Patient search error: {e.message}", exc_info=True)
        
        return {"success": False, "error": {...}}
```

**Key Points:**
- `CurrentContext()` is automatically excluded from MCP schema
- Clients never see the `ctx` parameter
- Context is available only during request execution
- **Always log to both** FastMCP context (client) and Python logger (server)

### 2. Services Layer (NO FastMCP) ✅ CORRECT

Use standard Python logging only:

```python
import logging

logger = logging.getLogger(__name__)  # ✅ Standard Python logging only

class PatientService:
    """Pure Python service - NO FastMCP dependencies."""
    
    async def search_patients(
        self,
        prefix: str,
        limit: int = 10
    ) -> Dict[str, Any]:
        """Search patients - callable from MCP, CrewAI, or directly."""
        
        # ✅ Use standard Python logging only
        logger.debug(f"Service: Searching patients with prefix={prefix}")
        
        try:
            # Call client layer
            result = await self.client.search_patients(prefix, limit)
            
            logger.debug(f"Service: Found {len(result)} patients")
            return result
            
        except EkaAPIError as e:
            logger.error(f"Service: Search failed - {e.message}")
            raise
```

### 3. Clients Layer (NO FastMCP) ✅ CORRECT

Use standard Python logging only:

```python
import logging

logger = logging.getLogger(__name__)  # ✅ Standard Python logging only

class BaseEkaClient:
    """Pure Python client - NO FastMCP dependencies."""
    
    async def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Make authenticated API request."""
        
        # ✅ Use standard Python logging only
        logger.debug(f"API Request: {method} {endpoint}")
        logger.debug(f"Curl: {curl_command}")
        
        try:
            response = await self._http_client.request(...)
            
            logger.debug(f"API Response: {response.status_code}")
            return response.json()
            
        except Exception as e:
            logger.error(f"API Error: {method} {endpoint} - {e}")
            raise EkaAPIError(str(e))
```

### 4. Auth Layer (NO FastMCP) ✅ CORRECT

Use standard Python logging only:

```python
import logging

logger = logging.getLogger(__name__)  # ✅ Standard Python logging only

class AuthenticationManager:
    """Pure Python auth manager - NO FastMCP dependencies."""
    
    def __init__(self, access_token: Optional[str] = None):
        # ✅ Use standard Python logging only
        logger.debug(f"AuthenticationManager initialized")
        
    async def get_auth_context(self) -> AuthContext:
        # ✅ Use standard Python logging only
        logger.debug("Obtaining authentication context")
        ...
```
## ❌ Anti-Patterns (What NOT to Do)

### DON'T: Optional FastMCP imports in lower layers

```python
# ❌ BAD - Creates hidden dependency in services/clients/auth
from typing import Optional

try:
    from fastmcp.server.context import Context
    HAS_FASTMCP = True
except ImportError:
    HAS_FASTMCP = False

# Still creates coupling even if "optional"
```

### DON'T: Try-except for context availability in lower layers

```python
# ❌ BAD - Clients/services should not know about FastMCP
try:
    ctx = get_context()
    await ctx.debug("message")
except RuntimeError:
    logger.debug("message")

# ✅ GOOD - Just use Python logging in lower layers
logger.debug("message")
```

### DON'T: Context parameter in service/client methods

```python
# ❌ BAD - Services should not accept Context
async def search_patients(
    self,
    prefix: str,
    ctx: Optional[Context] = None  # ❌ NO!
):
    pass

# ✅ GOOD - Services use standard logging only
async def search_patients(
    self,
    prefix: str
):
    logger.debug(f"Searching patients: {prefix}")
```

## Current Implementation Status

### Files with FastMCP Context Logging ✅

All tools now implement FastMCP context logging:

1. **tools/patient_tools.py**
   - `search_patients`: Search entry, result count, errors
   - `get_comprehensive_patient_profile`: Patient ID, fetch status
   - `add_patient`: Creation entry, patient ID, errors

2. **tools/appointment_tools.py**
   - `get_appointment_slots`: Doctor/clinic/date, slot count
   - `book_appointment`: Booking entry, confirmation, errors
   - `get_appointments_enriched`: Filter params, appointment count
   - All other appointment operations with appropriate logging

3. **tools/prescription_tools.py**
   - `get_prescription_details_basic`: Prescription ID, fetch status
   - `get_comprehensive_prescription_details`: Enrichment options, success/errors

4. **tools/doctor_clinic_tools.py**
   - `get_business_entities`: Clinic and doctor counts
   - `get_doctor_profile_basic`: Doctor ID, fetch status
   - `get_comprehensive_doctor_profile`: Profile fetch with details

5. **tools/assessment_tools.py**
   - `fetch_grouped_assessments`: Filter params, assessment counts, errors

### Files with Pure Python Logging ✅

Lower layers use standard Python logging only:

1. **clients/base_client.py**
   - API request details (debug level)
   - Response status codes (debug level)
   - API errors (error level)
   - Network failures (error level)
   - **NO FastMCP imports** ✅

2. **services/*.py**
   - Business logic operations (debug/info level)
   - Service-level errors (error level)
   - **NO FastMCP imports** ✅

3. **auth/manager.py**
   - Authentication operations (debug level)
   - Token management (debug level)
   - **NO FastMCP imports** ✅

## Logging Strategy

### Minimal Logging Approach

We follow a minimal logging approach:
- **Tool Entry**: Log when a tool is called (INFO level)
- **Success**: Log successful completion with key details (INFO level)
- **Errors**: Always log failures with context (ERROR level)
- **API Details**: Log request/response at DEBUG level for troubleshooting

This provides visibility without overwhelming the logs.

## Testing Logs

### VS Code
1. Open VS Code settings
2. Set `"mcp.logLevel": "debug"` (or "info")
3. Open Output panel → "Model Context Protocol"
4. Invoke MCP tools and watch logs appear

### Claude Desktop
1. Logs appear in:
   - **macOS**: `~/Library/Logs/Claude/mcp*.log`
   - **Windows**: `%APPDATA%\Claude\logs\mcp*.log`
2. Tail the log file:
   ```bash
   tail -f ~/Library/Logs/Claude/mcp-server-eka-care.log
   ```
3. Invoke tools from Claude and watch logs

### Cursor / Other Clients
Refer to client-specific documentation for log file locations.

## Best Practices

### DO:
✅ Use FastMCP context logging ONLY in tools layer  
✅ Use standard Python logging in services/clients/auth layers  
✅ Log at tool entry points (INFO)  
✅ Log key operations and their outcomes (INFO)  
✅ Log all errors with context (ERROR)  
✅ Use DEBUG for detailed diagnostics  
✅ Include relevant IDs and parameters in messages  
✅ Keep messages concise and actionable  
✅ Log to both FastMCP context AND Python logger in tools

### DON'T:
❌ Import FastMCP in services/clients/auth layers  
❌ Use optional FastMCP imports with try/except in lower layers  
❌ Pass Context as parameter to service/client methods  
❌ Log sensitive data (passwords, tokens, PII)  
❌ Log entire API responses at INFO level  
❌ Create excessive DEBUG logs for simple operations  
❌ Use context outside async functions  

## Tool Implementation Template

Use this template for all tools:

```python
from typing import Any, Dict, Annotated
import logging
from fastmcp import FastMCP
from fastmcp.dependencies import CurrentContext
from fastmcp.server.context import Context
from fastmcp.server.dependencies import get_access_token, AccessToken

logger = logging.getLogger(__name__)

def register_xxx_tools(mcp: FastMCP) -> None:
    
    @mcp.tool(description="...")
    async def tool_name(
        param: Annotated[str, "Description"],
        ctx: Context = CurrentContext()  # ✅ Always inject context in tools
    ) -> Dict[str, Any]:
        """Tool description."""
        
        # ✅ FastMCP context logging (for client visibility)
        await ctx.info(f"Operation started: {param}")
        await ctx.debug(f"Parameters: ...")
        
        # ✅ Standard Python logging (for server logs)
        logger.info(f"Tool called: tool_name with {param}")
        
        try:
            # Initialize client and service (pure Python, no FastMCP)
            token: AccessToken | None = get_access_token()
            client = XXXClient(access_token=token.token if token else None)
            service = XXXService(client)
            
            # Call service
            result = await service.do_something(param)
            
            # ✅ Log success to both
            await ctx.info("Operation completed successfully")
            logger.info(f"Operation successful")
            
            return {"success": True, "data": result}
            
        except EkaAPIError as e:
            # ✅ Log errors to both
            await ctx.error(f"Operation failed: {e.message}")
            logger.error(f"Tool error: {e.message}", exc_info=True)
            
            return {
                "success": False,
                "error": {
                    "message": e.message,
                    "status_code": e.status_code,
                    "error_code": e.error_code
                }
            }
```

## Verifying Architecture

### Check 1: No FastMCP in Lower Layers
```bash
# Should return ZERO matches
grep -r "from fastmcp" eka_mcp_sdk/clients/
grep -r "from fastmcp" eka_mcp_sdk/services/
grep -r "from fastmcp" eka_mcp_sdk/auth/

# Should have matches
grep -r "from fastmcp" eka_mcp_sdk/tools/
```

### Check 2: Can Import Without FastMCP
```python
# This should work without FastMCP installed
from eka_mcp_sdk.services import PatientService
from eka_mcp_sdk.clients.eka_emr_client import EkaEMRClient
```

### Check 3: Tools Use Context
```bash
# All tools should use Context = CurrentContext()
grep -r "ctx: Context = CurrentContext()" eka_mcp_sdk/tools/
```

## References

- [FastMCP Context Documentation](https://gofastmcp.com/servers/context)
- [FastMCP Logging Guide](https://gofastmcp.com/servers/logging)
- [MCP Specification](https://modelcontextprotocol.io)
- [CLAUDE.md](.code.guide/CLAUDE.md) - Architecture overview
- [TEST_IMPLEMENTATION_SUMMARY.md](.code.guide/TEST_IMPLEMENTATION_SUMMARY.md) - Testing guide

---

**Last Updated**: December 29, 2025  
**Status**: ✅ Complete - All tools have FastMCP context logging, all lower layers use pure Python logging
