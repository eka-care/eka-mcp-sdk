#!/usr/bin/env python3
"""
Quick test runner for eka-mcp-sdk

This is a convenience script that provides a simple interface to run tests.

Usage:
    ./run_tests.py                          # Run all patient tests
    ./run_tests.py appointments             # Run appointment tests
    ./run_tests.py patients list            # Run specific patient test
    ./run_tests.py appointments get_slots --doctor-id <id> --clinic-id <id>
    ./run_tests.py --list                   # List all available tests
    ./run_tests.py --verbose                # Run with verbose output
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
    
    # Determine which test module to run
    test_module = "tests.test_patient_tools"  # Default
    args = sys.argv[1:]
    
    # Check if first argument is a test suite selector
    if len(args) > 0:
        if args[0] == "appointments" or args[0] == "appointment":
            test_module = "tests.test_appointment_tools"
            args = args[1:]  # Remove the suite selector
        elif args[0] == "patients" or args[0] == "patient":
            test_module = "tests.test_patient_tools"
            args = args[1:]  # Remove the suite selector
        elif args[0] in ["--help", "-h"]:
            print(__doc__)
            print("\nAvailable test suites:")
            print("  patients      - Patient management APIs")
            print("  appointments  - Appointment management APIs")
            print("\nExamples:")
            print("  ./run_tests.py patients list")
            print("  ./run_tests.py appointments get_slots --doctor-id <id> --clinic-id <id>")
            print("  ./run_tests.py patients --verbose")
            print("  ./run_tests.py appointments all --test-write")
            return
    
    # Build the command
    cmd = [python_cmd, "-m", test_module]
    
    # Pass through remaining arguments
    if args:
        cmd.extend(args)
    
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
