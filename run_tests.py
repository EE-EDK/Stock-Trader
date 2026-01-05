#!/usr/bin/env python3
"""
Test runner for Stock Trader project
Provides clear guidance on running different types of tests
"""

import subprocess
import sys
import os

def check_dependencies():
    """Check if pytest is installed"""
    try:
        __import__('pytest')
        return True
    except ImportError:
        return False

def print_header(text):
    """Print formatted header"""
    print("\n" + "=" * 70)
    print(text)
    print("=" * 70 + "\n")

def main():
    """Run tests with proper guidance"""

    print_header("STOCK TRADER - TEST RUNNER")

    # Check if pytest is available
    if not check_dependencies():
        print("❌ pytest not installed")
        print("\nInstall test dependencies:")
        print("  pip install pytest pytest-cov pytest-mock")
        print("\nOr install all dependencies:")
        print("  pip install -r requirements.txt")
        print("\n" + "=" * 70)
        sys.exit(1)

    # Determine what to run based on arguments
    if len(sys.argv) > 1:
        test_path = sys.argv[1]
    else:
        test_path = "tests/"

    print(f"Running tests in: {test_path}\n")

    # Run pytest
    cmd = [
        sys.executable, "-m", "pytest",
        test_path,
        "-v",  # Verbose
        "--tb=short",  # Shorter traceback format
    ]

    # Add coverage if requested
    if "--cov" in sys.argv:
        cmd.extend(["--cov=src", "--cov-report=term-missing"])

    try:
        result = subprocess.run(cmd)
        sys.exit(result.returncode)
    except KeyboardInterrupt:
        print("\n\nTests interrupted by user")
        sys.exit(130)

if __name__ == "__main__":
    # Show usage if help requested
    if "--help" in sys.argv or "-h" in sys.argv:
        print_header("USAGE")
        print("Run all tests:")
        print("  python run_tests.py")
        print("\nRun specific test file:")
        print("  python run_tests.py tests/test_velocity.py")
        print("\nRun with coverage:")
        print("  python run_tests.py --cov")
        print("\nRun specific test class:")
        print("  python run_tests.py tests/test_velocity.py::TestVelocityCalculator")
        print("\nRun specific test:")
        print("  python run_tests.py tests/test_velocity.py::TestVelocityCalculator::test_calculate_velocity")
        print("\n" + "=" * 70)
        sys.exit(0)

    main()
