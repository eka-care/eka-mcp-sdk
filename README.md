# Eka.care MCP SDK

A Python library and self-hosted MCP server that exposes Eka.care's healthcare APIs to LLM applications. Use it as an importable library in your own projects, or run it directly as a standalone MCP server.

## 📚 Documentation

- **[Developer Guides](.code.guide/README.md)** - Comprehensive guides for developers
  - Architecture & Setup ([CLAUDE.md](.code.guide/CLAUDE.md))
  - Logging Guide ([LOGGING.md](.code.guide/LOGGING.md))
  - Testing Guide ([TESTING_GUIDE.md](.code.guide/TESTING_GUIDE.md))
  - Tool Selection Guide ([TOOL_SELECTION_GUIDE.md](.code.guide/TOOL_SELECTION_GUIDE.md))

## Features

- **Importable Library**: Use services and clients directly in your Python applications
- **Self-Hosted MCP Server**: Run as stdio or HTTP for Claude Desktop and other MCP clients
- **Modular Architecture**: Easy to extend with additional API modules
- **Simple Authentication**: Client ID/Secret + optional API key authentication
- **Comprehensive Error Handling**: Direct forwarding of Eka.care API errors for transparency
- **LLM-Optimized Responses**: Structured data formats optimized for LLM consumption
- **Multi-Tenant Workspace Routing**: Route requests to different client implementations

## Supported API Modules

### Doctor Tools
- **Appointment Management**: Create, update, and retrieve appointments
- **Digital Prescriptions**: Generate and manage digital prescriptions
- **Patient Records**: Access and manage patient medical records
- **Prescription History**: Retrieve patient prescription history

### Extensible Modules
You can easily add more API modules like:
- **ABDM Connector**: Health ID creation, consent management, health record sharing  
- **Self Assessment**: Health surveys, symptom checking, record analysis
- **Custom Modules**: Build your own using the base client architecture

## Installation

### As a library (in your project)

```bash
# Latest from main
pip install git+https://github.com/eka-care/eka-mcp-sdk.git@main

# Or pin to a specific release tag
pip install git+https://github.com/eka-care/eka-mcp-sdk.git@v0.1.0
```

With `uv`:
```bash
uv add "eka-mcp-sdk @ git+https://github.com/eka-care/eka-mcp-sdk.git@main"
```

### For local development / self-hosted server

```bash
git clone https://github.com/eka-care/eka-mcp-sdk.git
cd eka-mcp-sdk

# Install with UV (recommended)
uv sync

# Or with pip
pip install -e .
```

### Configuration

Create a `.env` file:

```env
# API Configuration
EKA_API_BASE_URL=https://api.eka.care

# Authentication (get from ekaconnect@eka.care)
EKA_CLIENT_ID=your_client_id
EKA_CLIENT_SECRET=your_client_secret
EKA_API_KEY=your_api_key  # Optional

# Server configuration
EKA_MCP_SERVER_HOST=localhost
EKA_MCP_SERVER_PORT=8000
EKA_LOG_LEVEL=INFO
```

### Using as a Python Library

```python
from eka_mcp_sdk.services import PatientService, AppointmentService
from eka_mcp_sdk.clients.eka_emr_client import EkaEMRClient

client = EkaEMRClient()
patient_service = PatientService(client)
result = await patient_service.search_patients("john")
```

For sync contexts (e.g. CrewAI):
```python
from eka_mcp_sdk.lib import search_patients_sync, get_appointments_enriched_sync

patients = search_patients_sync("john", limit=10)
```

### Running as MCP Server

```bash
source .venv/bin/activate  # On macOS/Linux

# stdio (for Claude Desktop)
eka-mcp-server

# HTTP mode
eka-mcp-server --transport http --host 0.0.0.0 --port 8000

# Or alternatively
python -m eka_mcp_sdk.server
```

## Usage with Claude Desktop

Add to your Claude Desktop MCP configuration. **Important**: Use the full path to the virtual environment's Python executable:

```json
{
  "mcpServers": {
    "eka-care": {
      "command": "/absolute/path/to/eka-mcp-sdk/.venv/bin/python",
      "args": ["-m", "eka_mcp_sdk.server"],
      "env": {
        "EKA_CLIENT_ID": "your_client_id",
        "EKA_CLIENT_SECRET": "your_client_secret", 
        "EKA_API_KEY": "your_api_key"
      }
    }
  }
}
```

### Alternative Configuration (if eka-mcp-server is in PATH)

If you installed the package globally or added the virtual environment to your PATH:

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

## API Documentation

### Doctor Tools Examples

```python
# Create an appointment
create_appointment(
    doctor_id="doc-456",
    patient_id="patient-789", 
    appointment_date="2024-01-15",
    appointment_time="10:30",
    appointment_type="consultation"
)

# Generate a prescription  
generate_prescription(
    patient_id="patient-789",
    doctor_id="doc-456",
    medications=[
        {
            "name": "Amoxicillin",
            "dosage": "500mg", 
            "frequency": "3 times daily",
            "duration": "7 days"
        }
    ],
    diagnosis="Upper respiratory infection",
    instructions="Take with food. Complete the full course."
)

# Get patient records
get_patient_records(
    patient_id="patient-789",
    record_type="lab_reports"
)
```

## Building Hosted Solutions

This SDK supports **multi-tenant workspace routing** where different clients (Eka, Moolchand, etc.) can use the same tools with their own API implementations.

### Architecture

```
Tools (client-agnostic) → Services → Client (all orchestration + API calls)
                                       ↑
                              ClientFactory.create_client(workspace_id)
```

### Creating a New Client

**1. Implement `BaseEMRClient`:**

```python
# eka_mcp_sdk/clients/moolchand_client.py
from .base_emr_client import BaseEMRClient

class MoolchandClient(BaseEMRClient):
    def get_workspace_name(self) -> str:
        return "moolchand"
    
    # Implement all abstract methods with your API logic
    async def doctor_availability_elicitation(self, ...): ...
    async def book_appointment_with_validation(self, ...): ...
```

**2. Configure via environment:**

```env
# Map workspace IDs to client classes (JSON format)
WORKSPACE_CLIENT_DICT={"moolchand": "eka_mcp_sdk.clients.moolchand_client.MoolchandClient"}

# Default workspace when no header present
EKA_WORKSPACE_CLIENT_TYPE=ekaemr
```

**3. Workspace routing** happens automatically via `x-eka-jwt-payload` header containing `w-id`.

## Development

```bash
git clone https://github.com/eka-care/eka-mcp-sdk.git
cd eka-mcp-sdk

# Install with development dependencies
uv sync --extra dev

# Run tests
uv run pytest

# Format code
uv run black .
uv run isort .

# Type checking
uv run mypy .
```

### Adding New API Modules

1. Create client in `eka_mcp_sdk/clients/`
2. Implement MCP tools in `eka_mcp_sdk/tools/`
3. Register tools in `server.py`
4. Update documentation

### Running Examples

```bash
python examples/direct_usage.py
python examples/crewai_usage.py  # Requires: uv add crewai
cat examples/MCP_USAGE.md
```

## Configuration Reference

| Environment Variable | Description | Default |
|---------------------|-------------|---------|
| `EKA_API_BASE_URL` | Eka.care API base URL | `https://api.eka.care` |
| `EKA_CLIENT_ID` | Client ID from Eka.care | Required |
| `EKA_CLIENT_SECRET` | Client secret from Eka.care | Required |
| `EKA_API_KEY` | API key for additional auth | Optional |
| `EKA_MCP_SERVER_HOST` | MCP server host | `localhost` |
| `EKA_MCP_SERVER_PORT` | MCP server port | `8000` |
| `EKA_LOG_LEVEL` | Logging level | `INFO` |

## Troubleshooting

**Git tag versioning (hatch-vcs)**
- Tags must follow PEP 440: `v0.2.0a1`, `v0.2.0rc1`, `v0.2.0.dev1` — not `v0.1.0-test`
- If an invalid tag exists alongside a valid one on the same commit, `setuptools_scm` may pick the invalid one → delete the bad tag: `git push origin --delete <bad-tag>`
- After fixing tags, clear uv's build cache: `uv cache clean`

---

## Support

- **Documentation**: [developer.eka.care](https://developer.eka.care)
- **Email**: ekaconnect@eka.care
- **Issues**: [GitHub Issues](https://github.com/eka-care/eka-mcp-sdk/issues)

## License

MIT License - see LICENSE file for details.


