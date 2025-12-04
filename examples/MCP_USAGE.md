# Eka.care MCP SDK - MCP Server Usage

The Eka.care MCP SDK includes a complete MCP server implementation with FastMCP that exposes all healthcare APIs as MCP tools. This allows seamless integration with Claude Desktop and other MCP-compatible clients.

## Quick Start

The SDK includes a built-in MCP server that you can run directly:

```bash
# Start the MCP server
eka-mcp-server

# Or run with Python module
python -m eka_mcp_sdk.server
```

## Claude Desktop Configuration

Add this to your Claude Desktop MCP configuration file:

```json
{
  "mcpServers": {
    "eka-care": {
      "command": "eka-mcp-server",
      "env": {
        "EKA_CLIENT_ID": "your_client_id",
        "EKA_CLIENT_SECRET": "your_client_secret",
        "EKA_API_KEY": "your_api_key"
      }
    }
  }
}
```

### Alternative: Full Python Path

If you prefer to specify the full path:

```json
{
  "mcpServers": {
    "eka-care": {
      "command": "python",
      "args": ["-m", "eka_mcp_sdk.server"],
      "env": {
        "EKA_CLIENT_ID": "your_client_id", 
        "EKA_CLIENT_SECRET": "your_client_secret"
      }
    }
  }
}
```

## Available MCP Tools

The server automatically exposes all healthcare API endpoints as structured MCP tools:

### 👥 Patient Management
- `search_patients` - Search patients by name, mobile, or prefix
- `get_patient_details_basic` - Get basic patient profile information
- `get_comprehensive_patient_profile` - Get complete patient data with history
- `add_patient` - Create new patient profiles
- `update_patient` - Update existing patient information

### 📅 Appointment Management  
- `get_appointment_slots` - Get available slots for doctor/clinic/date
- `book_appointment` - Book new appointments
- `get_appointments_enriched` - Get appointments with full details
- `update_appointment` - Update appointment details
- `cancel_appointment` - Cancel appointments
- `reschedule_appointment` - Reschedule appointments

### 🏥 Doctor & Clinic Management
- `get_business_entities` - Get all doctors and clinics
- `get_doctor_profile_basic` - Get doctor profile information
- `get_comprehensive_doctor_profile` - Get complete doctor data
- `get_clinic_details` - Get clinic information
- `get_doctor_services` - Get doctor's available services

### 💊 Prescription Management
- `get_prescription_details` - Get prescription information
- `create_prescription` - Generate new prescriptions
- `get_prescription_history` - Get patient prescription history

## Configuration

Configure the server using environment variables:

```env
# Required Authentication
EKA_CLIENT_ID=your_client_id
EKA_CLIENT_SECRET=your_client_secret

# Optional Configuration  
EKA_API_KEY=your_api_key
EKA_API_BASE_URL=https://api.eka.care
EKA_TOKEN_STORAGE_DIR=/custom/path/to/tokens
EKA_LOG_LEVEL=INFO
```

## Authentication

The MCP server uses the same authentication system as the direct SDK:

### Client Credentials (Recommended)
- Automatic token management with file storage
- Token refresh handled automatically  
- Suitable for persistent MCP server instances

### External Token (Advanced)
- For integration with external authentication systems
- No automatic refresh - external system manages tokens
- Pass tokens via client initialization in custom implementations

## Transport Options

### stdio (Default)
- Used by Claude Desktop and most MCP clients
- Communicates via standard input/output
- No network configuration required

### HTTP (Development)
- Useful for testing and debugging
- Runs on configurable host/port
- Access via HTTP API endpoints

## Server Features

### Structured Tool Descriptions
All tools use FastMCP's structured description format with:
- Clear tool descriptions in `@mcp.tool()` decorator
- Annotated parameters with detailed descriptions
- Clean docstrings for return value information

### Error Handling
- Standardized error responses with success/error structure
- EkaAPIError integration with status codes
- Detailed logging for troubleshooting

### Resource Access
The server can also expose resources like:
- Server status and configuration
- API documentation
- Health check endpoints

## Development

To extend the MCP server:

1. **Add new tools** in `eka_mcp_sdk/tools/`
2. **Register tools** in server initialization
3. **Use structured descriptions** with `@mcp.tool(description="...")`
4. **Annotate parameters** with `Annotated[Type, "description"]`

## Troubleshooting

### Common Issues

**Authentication Errors**
- Verify `EKA_CLIENT_ID` and `EKA_CLIENT_SECRET` are set
- Check credentials are valid and active
- Review logs for detailed error messages

**Connection Issues**
- Ensure Claude Desktop MCP config is correct
- Verify the command path and environment variables
- Check server logs for startup errors

**Tool Execution Errors**
- Validate API parameters and format
- Check network connectivity to Eka.care APIs
- Review API response details in logs

### Logging

Set `EKA_LOG_LEVEL=DEBUG` for detailed request/response logging:

```env
EKA_LOG_LEVEL=DEBUG
```

This will show:
- Full HTTP requests and responses
- Authentication token operations  
- Detailed error context
- MCP protocol messages

## Example Usage in Claude Desktop

Once configured, you can use natural language with Claude:

> "Search for patients with mobile number starting with +91"

> "Get available appointment slots for Dr. Smith at City Clinic tomorrow"

> "Book an appointment for patient John Doe with Dr. Smith"

> "Show me the prescription history for patient ID 12345"

The MCP tools will be automatically invoked with the appropriate parameters based on your requests.