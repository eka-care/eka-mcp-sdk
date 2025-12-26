# Testing Quick Reference

## 🚀 Quick Commands

```bash
# List all available tests
./run_tests.py --list
# OR
.venv/bin/python -m tests.test_patient_tools --list

# Run all read-only tests (safe)
./run_tests.py

# Run specific tests
./run_tests.py search list
# OR
.venv/bin/python -m tests.test_patient_tools search list

# Run with verbose output
./run_tests.py search --verbose

# Run all tests including write operations (creates/modifies data)
./run_tests.py all --test-write
```

## 📝 Common Test Scenarios

### Scenario 1: Verify APIs are working
```bash
# Start with list and search (safest tests)
./run_tests.py list search
```

### Scenario 2: Debug an API issue
```bash
# Run single test with verbose output
./run_tests.py search --verbose
```

### Scenario 3: Test specific patient
```bash
# Get patient ID from list first
./run_tests.py list

# Use that ID for detailed tests
./run_tests.py get_comprehensive --patient-id 176529070900934 --verbose
```

### Scenario 4: Test complete workflow
```bash
# Run all tests including write operations
./run_tests.py all --test-write
```

## 🔧 Debugging Common Issues

### Issue: Import Error for 'settings'
**Error:** `cannot import name 'settings' from 'eka_mcp_sdk.config.settings'`

**Fix:** Already fixed in storage.py. Ensure you have the latest code.

### Issue: Token Refresh Failed
**Error:** `Token refresh failed - Status: 400`

**Fix:**
```bash
# Clear stored tokens
rm -rf ~/.eka_mcp/tokens.json

# Re-run test (will prompt for OAuth)
./run_tests.py list
```

### Issue: API Returns 400 "Not Supported"
**Error:** `API error: 400 - {"message": "Not Supported"}`

**Fix:** Some endpoints may not be available. Try alternative endpoints:
- Instead of `search_patients`, use `list_patients`
- Check API documentation for correct endpoint

### Issue: API Returns 404
**Error:** `API error: 404 - <!doctype html>`

**Fix:** Endpoint URL is incorrect. Check:
1. API base URL in .env
2. Endpoint path in service/client code
3. API documentation for correct path

## 📊 Understanding Test Output

### Success Output
```
✅ list_patients                PASSED
```
API worked correctly, returned expected data.

### Failed Output
```
❌ search_patients              FAILED - Unexpected error: Not Supported
```
API call failed. Check error message for reason.

### Skipped Output
```
⏭️  add_patient                 SKIPPED
```
Test was skipped (usually write operations). Use `--test-write` to include.

## 🎯 Test Selection Guide

| What you want to test | Command |
|----------------------|---------|
| Check basic connectivity | `./run_tests.py list` |
| Verify search works | `./run_tests.py search` |
| Get detailed patient info | `./run_tests.py get_comprehensive` |
| Test all read operations | `./run_tests.py` |
| Test everything | `./run_tests.py all --test-write` |
| Debug specific issue | `./run_tests.py <test> --verbose` |

## 🔑 Environment Setup

### Required .env variables
```bash
EKA_CLIENT_ID=your_client_id           # Required
EKA_CLIENT_SECRET=your_client_secret   # Required
EKA_API_BASE_URL=https://api.eka.care  # Required
```

### Optional .env variables
```bash
EKA_TOKEN_STORAGE_DIR=/custom/path     # Custom token storage location
EKA_LOG_LEVEL=DEBUG                    # Enable debug logging
```

## 💡 Pro Tips

1. **Always start with `list`** - It's the most reliable test
2. **Use `--verbose` when debugging** - Shows full request/response
3. **Don't use `--test-write` in production** - Avoid creating test data
4. **Store patient IDs** - Use `--patient-id` to test specific patients
5. **Check both outputs** - Test output AND MCP client logs

## 📂 Log Locations

### Test Output
Displayed in terminal where you run the tests.

### MCP Client Logs
- **VS Code**: Output panel → "Model Context Protocol"
- **Claude Desktop**: `~/Library/Logs/Claude/mcp*.log` (macOS)
- **Cursor**: Client-specific location

## 🧪 Test Coverage

### Patient Tools - ✅ Complete
- ✅ search_patients
- ✅ list_patients
- ✅ get_patient_details_basic
- ✅ get_comprehensive_patient_profile
- ✅ get_patient_by_mobile
- ✅ add_patient
- ✅ update_patient
- ✅ archive_patient

### Coming Soon
- ⏳ Appointment tools
- ⏳ Prescription tools
- ⏳ Assessment tools
- ⏳ Doctor/Clinic tools

## 📞 Need Help?

1. Check test output for specific error messages
2. Run with `--verbose` for detailed logs
3. Review [tests/README.md](tests/README.md) for comprehensive docs
4. Check [LOGGING.md](LOGGING.md) for logging details
