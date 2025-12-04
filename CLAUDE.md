# Claude.ai Project Context

## Instructions
Always use context7 when I need code generation, setup or configuration steps, or library/API documentation. This means you should automatically use the Context7 MCP tools to resolve library id and get library docs without me having to explicitly ask.

## Project Overview
This is the Eka.care MCP SDK - a self-hosted Model Context Protocol (MCP) server that exposes Eka.care's healthcare APIs to LLM applications like Claude Desktop. The project enables seamless integration of healthcare data and services into AI-powered workflows.

## Key Features
- **Self-Hosted Deployment**: Clean, simple deployment for healthcare organizations
- **Modular Architecture**: Easy to extend with additional API modules
- **Simple Authentication**: Client ID/Secret + optional API key authentication
- **Comprehensive Error Handling**: Direct forwarding of Eka.care API errors
- **LLM-Optimized Responses**: Structured data formats optimized for LLM consumption
- **Reusable Core**: Core components can be imported for building hosted MCP solutions

## Architecture

### Directory Structure
```
eka_mcp_sdk/
├── __init__.py              # Package initialization
├── auth/                    # Authentication module
│   ├── __init__.py
│   ├── manager.py          # Authentication manager with OAuth/token handling
│   └── models.py           # Pydantic models for auth (TokenResponse, AuthContext, EkaAPIError)
├── clients/                 # API client modules
│   ├── __init__.py
│   ├── base.py             # Base client class with common HTTP functionality
│   └── doctor_tools_client.py  # Doctor Tools API client
├── config/                  # Configuration management
│   ├── __init__.py
│   └── settings.py         # Pydantic settings with environment variable loading
├── core/                    # Reusable core components for hosted solutions
│   └── __init__.py         # Exports for external use
├── tools/                   # MCP tool implementations
│   ├── __init__.py
│   └── doctor_tools.py     # FastMCP tools for Doctor Tools API
├── utils/                   # Utility functions
│   └── __init__.py
└── server.py               # Main MCP server entry point
```

### Key Components

#### Authentication (`auth/`)
- **AuthenticationManager**: Handles token lifecycle, refresh, and API authentication
- **AuthContext**: Contains access token, expiration, and auth headers
- **TokenResponse**: Pydantic model for API token responses
- **EkaAPIError**: Custom exception for API errors

#### API Clients (`clients/`)
- **BaseEkaClient**: Abstract base class with common HTTP request functionality
- **DoctorToolsClient**: Specific implementation for Doctor Tools API endpoints

#### Configuration (`config/`)
- **EkaSettings**: Pydantic settings class that loads from environment variables
- Supports `.env` file loading with `EKA_` prefix

#### MCP Tools (`tools/`)
- **register_doctor_tools()**: Registers Doctor Tools API endpoints as MCP tools
- Each tool wraps API client methods with proper error handling

## Current API Modules

### Doctor Tools
- **create_appointment**: Create new appointments
- **get_appointments**: Retrieve appointments with filters
- **update_appointment_status**: Update appointment status
- **generate_prescription**: Generate digital prescriptions
- **get_patient_records**: Access patient medical records
- **add_patient_record**: Add new patient records
- **get_prescription_history**: Retrieve prescription history

## Environment Configuration

Required environment variables (loaded from `.env` file):
```env
# API Configuration
EKA_API_BASE_URL=https://api.eka.care

# Authentication (get from ekaconnect@eka.care)
EKA_CLIENT_ID=your_client_id
EKA_CLIENT_SECRET=your_client_secret
EKA_API_KEY=your_api_key  # Optional

# Server Configuration
MCP_SERVER_HOST=localhost
MCP_SERVER_PORT=8888
LOG_LEVEL=INFO
```

## Development Setup

1. **Installation**: `uv sync` or `pip install -e .`
2. **Configuration**: Copy `.env.example` to `.env` and update credentials
3. **Run Server**: `eka-mcp-server` (after `uv pip install -e .`)
4. **Testing**: Use with Claude Desktop or other MCP clients

## Extension Points

### Adding New API Modules
1. Create client in `clients/` extending `BaseEkaClient`
2. Implement MCP tools in `tools/`
3. Register tools in `server.py`
4. Update documentation

### Example for ABDM Module
```python
# clients/abdm_client.py
class ABDMClient(BaseEkaClient):
    def get_api_module_name(self) -> str:
        return "ABDM Connector"
    
    async def create_health_id(self, mobile: str) -> Dict[str, Any]:
        return await self._make_request(
            method="POST",
            endpoint="/abdm/v2/registration/mobile/init",
            data={"mobile": mobile}
        )

# tools/abdm_tools.py
def register_abdm_tools(mcp: FastMCP) -> None:
    client = ABDMClient()
    
    @mcp.tool()
    async def create_health_id(mobile: str) -> Dict[str, Any]:
        # Implementation
```

## Logging

Comprehensive HTTP logging is implemented:
- **INFO level**: Request/response status and high-level operations
- **DEBUG level**: Full request/response data, headers, payloads
- **ERROR level**: Detailed error information with context

Set `LOG_LEVEL=DEBUG` for full debugging information.

## Deployment

### Self-Hosted (Primary Use Case)
- Install package: `uv pip install -e .`
- Configure environment variables
- Run: `eka-mcp-server`
- Add to Claude Desktop configuration

### As Library for Hosted Solutions
```python
from eka_mcp_sdk.core import (
    BaseEkaClient,
    DoctorToolsClient,
    AuthContext,
    EkaAPIError
)
# Use components in hosted MCP implementation
```

## Technical Notes

- **Python Version**: Requires Python 3.10+
- **Framework**: Built on FastMCP for MCP protocol implementation
- **HTTP Client**: Uses httpx for async HTTP requests
- **Validation**: Pydantic v2 for data validation and settings
- **Authentication**: Token-based with automatic refresh
- **Transport**: Uses stdio transport for MCP communication

## Common Commands

```bash
# Development
uv sync                    # Install dependencies
uv pip install -e .       # Install package in editable mode
eka-mcp-server            # Run MCP server

# Testing
python -m eka_mcp_sdk.server  # Alternative run method

# Claude Desktop Integration
# Add server config to Claude Desktop MCP settings
```

## Future Extensions

The modular architecture supports easy addition of:
- **ABDM Connector**: Health ID creation, consent management
- **Self Assessment**: Health surveys, symptom checking
- **Custom Modules**: Organization-specific healthcare APIs
- **Multi-tenant Hosting**: For SaaS deployments

## Contact

- **Documentation**: [developer.eka.care](https://developer.eka.care)
- **Support**: ekaconnect@eka.care
- **Repository**: GitHub (when public)