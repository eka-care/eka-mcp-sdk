# Eka.care MCP SDK

A simple, self-hosted Model Context Protocol (MCP) server that exposes Eka.care's healthcare APIs to LLM applications like Claude Desktop. This enables seamless integration of healthcare data and services into AI-powered workflows.

## 📚 Documentation

- **[Developer Guides](.code.guide/README.md)** - Comprehensive guides for developers
  - Architecture & Setup ([CLAUDE.md](.code.guide/CLAUDE.md))
  - Logging Guide ([LOGGING.md](.code.guide/LOGGING.md))
  - Testing Guide ([TESTING_GUIDE.md](.code.guide/TESTING_GUIDE.md))
  - Tool Selection Guide ([TOOL_SELECTION_GUIDE.md](.code.guide/TOOL_SELECTION_GUIDE.md))

## Features

- **Self-Hosted Deployment**: Clean, simple deployment for healthcare organizations
- **Modular Architecture**: Easy to extend with additional API modules  
- **Simple Authentication**: Client ID/Secret + optional API key authentication
- **Comprehensive Error Handling**: Direct forwarding of Eka.care API errors for transparency
- **LLM-Optimized Responses**: Structured data formats optimized for LLM consumption
- **Reusable Core**: Core components can be imported for building hosted MCP solutions

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

## Quick Start

### Installation

```bash
# Clone the repository
git clone git@github.com:eka-care/eka-mcp-sdk.git
cd eka-mcp-sdk

# Install with UV (recommended)
uv sync

# Activate the virtual environment
source .venv/bin/activate  # On macOS/Linux
# or
.venv\Scripts\activate     # On Windows

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

### Running the Server

```bash
# Make sure virtual environment is activated
source .venv/bin/activate  # On macOS/Linux

# Run the MCP server
eka-mcp-server

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

This SDK is designed to be modular and reusable. You can import components from their respective modules to build more complex hosted MCP solutions:

```python
# Import foundational components from their original modules
from eka_mcp_sdk.auth.models import AuthContext, EkaAPIError
from eka_mcp_sdk.clients.base_client import BaseEkaClient
from eka_mcp_sdk.clients.eka_emr_client import EkaEMRClient

# Import service classes for business logic
from eka_mcp_sdk.services import (
    PatientService,
    AppointmentService,
    PrescriptionService,
    DoctorClinicService
)

# Use these components in your hosted MCP implementation
```

This makes it easy to:
- Add multi-tenant capabilities
- Implement custom authentication flows  
- Build workspace isolation
- Add additional API modules

## Development

### Setup Development Environment

```bash
# Clone the repository
git clone https://github.com/ekacare/eka-mcp-sdk.git
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

## Development

### Development Setup

```bash
# Clone the repository
git clone git@github.com:eka-care/eka-mcp-sdk.git
cd eka-mcp-sdk

# Install development dependencies with UV
uv sync --dev

# Activate virtual environment
source .venv/bin/activate

# Run tests (if available)
pytest

# Run examples
python examples/direct_usage.py
python examples/crewai_usage.py  # Requires: pip install crewai
```

### Virtual Environment Management

The project uses `uv` for dependency management. Key commands:

```bash
# Create/update virtual environment and install dependencies
uv sync

# Add a new dependency
uv add package_name

# Add a development dependency  
uv add --dev package_name

# Activate the virtual environment
source .venv/bin/activate  # macOS/Linux
.venv\Scripts\activate     # Windows

# Deactivate
deactivate
```

### Running Examples

Make sure the virtual environment is activated before running examples:

```bash
source .venv/bin/activate

# Direct API usage
python examples/direct_usage.py

# CrewAI integration (requires crewai package)
uv add crewai  # Install CrewAI
python examples/crewai_usage.py

# MCP server documentation
cat examples/MCP_USAGE.md
```

## Configuration Reference

| Environment Variable | Description | Default |
|---------------------|-------------|---------|
| `EKA_API_BASE_URL` | Eka.care API base URL | `https://api.eka.care` |
| `EKA_CLIENT_ID` | Client ID from Eka.care | Required |
| `EKA_CLIENT_SECRET` | Client secret from Eka.care | Required |
| `EKA_API_KEY` | API key for additional auth | Required|
| `EKA_MCP_SERVER_HOST` | MCP server host | `localhost` |
| `EKA_MCP_SERVER_PORT` | MCP server port | `8000` |
| `EKA_LOG_LEVEL` | Logging level | `INFO` |

## Support

- **Documentation**: [developer.eka.care](https://developer.eka.care)
- **Email**: ekaconnect@eka.care
- **Issues**: [GitHub Issues](https://github.com/ekacare/eka-mcp-sdk/issues)

## License

MIT License - see LICENSE file for details.
