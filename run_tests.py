#!/usr/bin/env python3
"""
Quick test runner for eka-mcp-sdk

This is a convenience script that provides a simple interface to run tests.

Usage:
    ./run_tests.py                          # Run all patient tests
    ./run_tests.py list                     # List all tests
    ./run_tests.py search --verbose         # Run search test with verbose output
    ./run_tests.py all --test-write         # Run all tests including write operations
"""

import sys
import subprocess
import os

def main():
    # Make sure we're in the right directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    
    # Use virtual environment Python if available
    venv_python = os.path.join(script_dir, ".venv", "bin", "python")
    python_cmd = venv_python if os.path.exists(venv_python) else sys.executable
    
    # Build the command
    cmd = [python_cmd, "-m", "tests.test_patient_tools"]
    
    # Pass through all arguments
    if len(sys.argv) > 1:
        cmd.extend(sys.argv[1:])
    
    # Run the test
    try:
        result = subprocess.run(cmd)
        sys.exit(result.returncode)
    except KeyboardInterrupt:
        print("\n\n⚠️  Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error running tests: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
