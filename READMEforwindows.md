# Eka.care MCP SDK

A simple, self-hosted Model Context Protocol (MCP) server that exposes Eka.care's healthcare APIs to LLM applications like Claude Desktop.

---

## Quick Start (Windows)

### Installation

```bash
# Clone the repository
git clone git@github.com:eka-care/eka-mcp-sdk.git
cd eka-mcp-sdk

# Create virtual environment
python -m venv venv

# Activate virtual environment (Windows)
venv\Scripts\Activate.ps1

# If conda is active
conda deactivate

# Install dependencies (recommended)
pip install uv
uv sync

# Upgrade pip
python -m pip install --upgrade pip

# Install SDK
pip install -e .
```

---

### Configuration

Create a `.env` file:

```env
# Eka.care MCP SDK Configuration

# ==============================================
# API CONFIGURATION
# ==============================================
EKA_API_BASE_URL=https://api.eka.care

# ==============================================
# AUTHENTICATION
# ==============================================
# Get these credentials from ekaconnect@eka.care
EKA_CLIENT_ID=
EKA_CLIENT_SECRET=
EKA_API_KEY=

# ==============================================
# MCP SERVER CONFIGURATION
# ==============================================
EKA_MCP_SERVER_HOST=localhost
EKA_MCP_SERVER_PORT=8888

# ==============================================
# LOGGING CONFIGURATION
# ==============================================
EKA_LOG_LEVEL=INFO
```

---

### Running the Server

```bash
eka-mcp-server
```

or

```bash
python -m eka_mcp_sdk.server
```

---

## Usage with Claude Desktop (Windows)

```json
{
  "mcpServers": {
    "eka-care": {
      "command": "C:\\absolute\\path\\to\\eka-mcp-sdk\\venv\\Scripts\\python.exe",
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

---

## Configuration Reference

| Variable            | Description   | Default                                      |
| ------------------- | ------------- | -------------------------------------------- |
| EKA_API_BASE_URL    | API base URL  | [https://api.eka.care](https://api.eka.care) |
| EKA_CLIENT_ID       | Client ID     | Required                                     |
| EKA_CLIENT_SECRET   | Client Secret | Required                                     |
| EKA_API_KEY         | API Key       | Optional                                     |
| EKA_MCP_SERVER_HOST | Server host   | localhost                                    |
| EKA_MCP_SERVER_PORT | Server port   | 8888                                         |
| EKA_LOG_LEVEL       | Log level     | INFO                                         |

---

## Support

* Email: [ekaconnect@eka.care](mailto:ekaconnect@eka.care)
* Issues: GitHub Issues



Perfect — these belong as **small README notes**, not prose.
Below are **minimal additions only**, matching your existing style.

---

## Prerequisites

```bash
# Install uv (Windows)
pip install uv
```

---

## Troubleshooting

### Port Already in Use
Edit `.env`:
```env
EKA_MCP_SERVER_PORT=8890
```
Restart the server:
```bash
eka-mcp-server
```

### `eka-mcp-server` Not Recognized
Ensure virtual environment is activated and package is installed:
```bash
venv\Scripts\Activate.ps1
pip install -e .
```
Alternative:
```bash
python -m eka_mcp_sdk.server
```