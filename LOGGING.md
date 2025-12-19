# FastMCP Context Logging

This project uses FastMCP's context-based logging to provide better visibility for integrators debugging their MCP client implementations.

## Key Benefits

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

### 1. Tool Functions
Use `CurrentContext()` dependency injection:

```python
from fastmcp.dependencies import CurrentContext
from fastmcp.server.context import Context

@mcp.tool()
async def search_patients(
    prefix: str,
    ctx: Context = CurrentContext()  # Auto-injected, excluded from schema
) -> Dict[str, Any]:
    await ctx.info(f"Searching patients with prefix: {prefix}")
    
    try:
        result = await patient_service.search_patients(prefix)
        await ctx.info(f"Found {len(result)} patients")
        return {"success": True, "data": result}
    except Exception as e:
        await ctx.error(f"Search failed: {str(e)}")
        raise
```

**Key Points:**
- `CurrentContext()` is automatically excluded from MCP schema
- Clients never see the `ctx` parameter
- Context is available only during request execution

### 2. Nested Functions (Service Layer)
Use `get_context()` for functions called from tools:

```python
from fastmcp.server.dependencies import get_context

async def make_api_request(url: str) -> dict:
    """Helper function that needs logging."""
    try:
        ctx = get_context()  # Get active context
        await ctx.debug(f"Making request to: {url}")
        
        response = await client.get(url)
        await ctx.debug(f"Response status: {response.status_code}")
        return response.json()
    except RuntimeError:
        # Context not available (outside MCP request)
        # Fall back to standard logging
        logger.debug(f"Making request to: {url}")
        response = await client.get(url)
        return response.json()
```

**Important:**
- `get_context()` raises `RuntimeError` if called outside a request
- Always handle this case for code used outside MCP context
- Use try/except to gracefully fall back to standard logging

### 3. Base Client Pattern
Optional context with fallback:

```python
async def _make_request(self, method: str, endpoint: str) -> dict:
    """Make API request with optional context logging."""
    
    # Try to get context (may not be available)
    ctx: Optional[Context] = None
    try:
        ctx = get_context()
    except RuntimeError:
        pass  # Context not available
    
    # Log using context if available, otherwise use standard logger
    if ctx:
        await ctx.debug(f"API Request: {method} {endpoint}")
    else:
        logger.debug(f"API Request: {method} {endpoint}")
    
    try:
        response = await self._http_client.request(method, url)
        
        if ctx:
            await ctx.debug(f"Response: {response.status_code}")
        
        if response.status_code >= 400:
            if ctx:
                await ctx.error(f"API error: {response.status_code}")
            raise APIError(response.status_code)
        
        return response.json()
    except Exception as e:
        if ctx:
            await ctx.error(f"Request failed: {str(e)}")
        raise
```

## Current Implementation

### Files with Context Logging

1. **server.py**
   - Server startup information
   - Configuration details (debug level)

2. **tools/patient_tools.py**
   - `search_patients`: Search entry, result count, errors
   - `get_comprehensive_patient_profile`: Patient ID, fetch status
   - `add_patient`: Creation entry, patient ID, errors

3. **clients/base.py**
   - API request details (debug level)
   - Response status codes (debug level)
   - API errors (error level)
   - Network failures (error level)

### Minimal Logging Strategy

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
✅ Log at tool entry points (INFO)  
✅ Log key operations and their outcomes (INFO)  
✅ Log all errors with context (ERROR)  
✅ Use DEBUG for detailed diagnostics  
✅ Include relevant IDs and parameters in messages  
✅ Keep messages concise and actionable  

### DON'T:
❌ Log sensitive data (passwords, tokens, PII)  
❌ Log entire API responses at INFO level  
❌ Create excessive DEBUG logs for simple operations  
❌ Use context outside async functions  
❌ Forget to handle `RuntimeError` with `get_context()`  

## Expanding Logging

To add logging to more tools:

1. **Import dependencies:**
   ```python
   from fastmcp.dependencies import CurrentContext
   from fastmcp.server.context import Context
   ```

2. **Add context parameter:**
   ```python
   @mcp.tool()
   async def my_tool(param: str, ctx: Context = CurrentContext()):
       await ctx.info(f"Tool called with: {param}")
       ...
   ```

3. **Log key operations:**
   ```python
   try:
       result = await service.do_something()
       await ctx.info("Operation successful")
       return result
   except Exception as e:
       await ctx.error(f"Operation failed: {str(e)}")
       raise
   ```

## References

- [FastMCP Context Documentation](https://gofastmcp.com/servers/context)
- [FastMCP Logging Guide](https://gofastmcp.com/servers/logging)
- [MCP Specification](https://modelcontextprotocol.io)

## Future Enhancements

Potential improvements:
- [ ] Add structured logging with request IDs
- [ ] Add logging to remaining tool files (appointments, prescriptions, etc.)
- [ ] Add performance metrics logging
- [ ] Add OAuth flow logging
- [ ] Create log aggregation utilities for debugging
