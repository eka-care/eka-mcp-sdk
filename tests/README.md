# Eka MCP SDK - Test Suite

Comprehensive test suite for validating all eka-mcp-sdk APIs with detailed logging and debugging capabilities.

## 📁 Test Files

- **`test_patient_tools.py`** - Patient management APIs (search, list, add, update, etc.)
- More test files coming soon for appointments, prescriptions, assessments, etc.

## 🚀 Quick Start

### Prerequisites

1. **Environment Setup**
   ```bash
   # Copy .env.example to .env and fill in your credentials
   cp .env.example .env
   ```

2. **Required Environment Variables**
   ```bash
   EKA_CLIENT_ID=your_client_id
   EKA_CLIENT_SECRET=your_client_secret
   EKA_API_BASE_URL=https://api.eka.care
   ```

3. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

### Running Tests

#### Patient Tools Tests

```bash
# Activate virtual environment (if not already active)
source .venv/bin/activate

# List all available tests
python -m tests.test_patient_tools --list
# OR use the convenience script
./run_tests.py --list

# Run all read-only tests (safe, no data modifications)
python -m tests.test_patient_tools
# OR
./run_tests.py

# Run all tests including write operations
python -m tests.test_patient_tools all --test-write
# OR
./run_tests.py all --test-write

# Run specific tests
python -m tests.test_patient_tools search list get_basic

# Run with verbose output (shows full request/response)
python -m tests.test_patient_tools --verbose

# Test with specific patient ID
python -m tests.test_patient_tools get_basic --patient-id 123456789

# Test search with custom prefix
python -m tests.test_patient_tools search --prefix "john"

# Test get by mobile number
python -m tests.test_patient_tools get_by_mobile --mobile +919876543210
```

## 📋 Available Tests

### Patient Tools

| Test Name | Description | Type |
|-----------|-------------|------|
| `all` | Run all tests | Combo |
| `search` / `search_patients` | Search patients by prefix | Read |
| `list` / `list_patients` | List paginated patients | Read |
| `get_basic` / `get_patient_basic` | Get basic patient details | Read |
| `get_comprehensive` | Get comprehensive patient profile with appointments | Read |
| `get_by_mobile` | Get patient by mobile number | Read |
| `add` / `add_patient` | Create new patient | Write |
| `update` / `update_patient` | Update patient details | Write |
| `archive` / `archive_patient` | Archive patient (soft delete) | Write |

## 🎯 Test Output Examples

### Normal Output
```
======================================================================
🧪 Running test: search_patients
======================================================================

🔧 Setting up test environment
======================================================================
✅ API Base URL: https://api.eka.care
✅ Client initialized successfully

📤 REQUEST: search_patients
📥 RESPONSE: ✅ SUCCESS
   Summary: {"patients": [...], "currPageMeta": {...}}
   ✓ Found patients with prefix 'test'

✅ Test 'search_patients' completed successfully
```

### Verbose Output (`--verbose`)
```
📤 REQUEST: search_patients
   Parameters: {
     "prefix": "test",
     "limit": 10
   }
📥 RESPONSE: ✅ SUCCESS
   Response: {
     "success": true,
     "data": {
       "status": "success",
       "patients": [...],
       ...
     }
   }
```

### Error Output
```
📤 REQUEST: search_patients
📥 RESPONSE: ❌ FAILED
   Error: Unexpected error: Not Supported
   Status: 400

❌ Test 'search_patients' failed with API error:
   Message: Unexpected error: Not Supported
   Status: 400
```

## 🔍 Debugging Tips

### Enable Verbose Mode
```bash
python -m tests.test_patient_tools search --verbose
```

This shows:
- Full request parameters
- Complete API responses
- Detailed error traces

### Test Individual APIs
```bash
# Test just one API to isolate issues
python -m tests.test_patient_tools search
```

### Check Authentication
```bash
# If you get 401 errors, check your .env file
cat .env | grep EKA_CLIENT

# Re-authenticate by deleting tokens
rm -rf ~/.eka_mcp/tokens.json
python -m tests.test_patient_tools list
```

### Use Test Patient ID
```bash
# Get a patient ID from list
python -m tests.test_patient_tools list

# Use that ID for other tests
python -m tests.test_patient_tools get_comprehensive --patient-id 176529070900934
```

## 🏗️ Test Structure

### Test Function Template
```python
async def test_my_api(*args, **kwargs):
    """Test my_api functionality"""
    r = get_runner()
    await r.setup()
    
    # Get parameters
    param = kwargs.get("param", "default")
    
    # Log request
    r.log_request("my_api", param=param)
    
    try:
        # Call API
        result = await r.service.my_api(param=param)
        
        # Log response
        r.log_response({"success": True, "data": result})
        
        # Validate
        assert result is not None, "Result should not be None"
        print(f"   ✓ Success message")
        
        return result
        
    except EkaAPIError as e:
        r.log_response({"success": False, "error": {"message": str(e)}}, success=False)
        raise
    except Exception as e:
        r.log_error(e)
        raise
```

### Adding New Tests

1. Create test function following the template
2. Add to `TEST_FUNCTIONS` dictionary
3. Add command-line arguments if needed
4. Update this README

## 🔐 Authentication

Tests use OAuth2 authentication via the SDK:

1. First run prompts for OAuth login
2. Tokens stored in `~/.eka_mcp/tokens.json`
3. Subsequent runs reuse tokens
4. Expired tokens auto-refresh

## ⚠️ Safety Features

### Read-Only by Default
- By default, only read operations are run
- Write operations (add, update, archive) are skipped
- Use `--test-write` flag to enable write operations

### Data Protection
```bash
# Safe - only reads data
python -m tests.test_patient_tools all

# Writes data - use with caution
python -m tests.test_patient_tools all --test-write
```

## 📊 Test Reports

### Verbose Output
After running `test_all`:
```
📤 REQUEST: search_patients
   Parameters: {"prefix": "test", "limit": 10}

🔧 CURL COMMAND:
   curl -X GET -H 'Authorization: Bearer eyJhbGc...' -H 'client-id: EC_1234' 'https://api.eka.care/profiles/v1/patient/search?prefix=test&limit=10'

📥 RESPONSE: ✅ SUCCESS
   Response: {full JSON response}
```

The curl command shown in verbose mode can be copied and run directly in your terminal for debugging.

### Summary Output
After running `test_all`:
```
======================================================================
📊 TEST SUMMARY
======================================================================
✅ list_patients                PASSED
✅ search_patients              PASSED
✅ get_patient_basic            PASSED
✅ get_patient_comprehensive    PASSED
⏭️  add_patient                 SKIPPED
⏭️  update_patient              SKIPPED
⏭️  archive_patient             SKIPPED

Total: 7 | Passed: 4 | Failed: 0 | Skipped: 3
```

## 🧪 Coming Soon

- [ ] Appointment tools tests
- [ ] Prescription tools tests
- [ ] Assessment tools tests
- [ ] Doctor/Clinic tools tests
- [ ] Integration tests
- [ ] Performance tests
- [ ] CI/CD integration

## 📝 Notes

- Tests require valid OAuth credentials
- Some APIs may not be available in all environments
- Check LOGGING.md for log file locations
- Use `--verbose` for debugging API issues

## 🐛 Troubleshooting

### Import Error for 'settings'
```bash
# Fixed in storage.py - make sure you have latest code
# The import should be:
from ..config.settings import EkaSettings
settings = EkaSettings()
```

### Token Refresh Failed
```bash
# Clear tokens and re-authenticate
rm -rf ~/.eka_mcp/tokens.json
python -m tests.test_patient_tools list
```

### API Returns 404/400
- Check API endpoint URL in error message
- Verify API is available in your environment
- Check if you have correct scopes in OAuth

## 💡 Tips

1. **Start with list/search** - These establish baseline connectivity
2. **Use verbose mode** - When debugging API issues
3. **Test one at a time** - Easier to isolate problems
4. **Check logs** - Both test output and MCP client logs
5. **Validate credentials** - Ensure .env is properly configured
