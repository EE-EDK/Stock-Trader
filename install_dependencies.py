#!/usr/bin/env python3
"""
Install missing dependencies for Stock Trader
Checks for missing packages and installs them
"""

import subprocess
import sys

def check_and_install_dependencies():
    """Check for missing dependencies and install them"""

    # Core dependencies
    dependencies = [
        'requests',
        'beautifulsoup4',
        'pyyaml',
        'numpy',
        'matplotlib',
        'pandas',
        'ttkbootstrap',
        'yfinance',
        'vaderSentiment',
        'pytest',
        'pytest-cov',
        'pytest-mock'
    ]

    missing = []
    installed = []

    print("=" * 70)
    print("STOCK TRADER - DEPENDENCY CHECKER")
    print("=" * 70)
    print("\nChecking installed packages...\n")

    for package in dependencies:
        # Map package names to import names
        import_name = package
        if package == 'beautifulsoup4':
            import_name = 'bs4'
        elif package == 'pyyaml':
            import_name = 'yaml'
        elif package == 'vaderSentiment':
            import_name = 'vaderSentiment'
        elif package == 'pytest-cov':
            import_name = 'pytest_cov'
        elif package == 'pytest-mock':
            import_name = 'pytest_mock'

        try:
            __import__(import_name)
            print(f"  ✅ {package}")
            installed.append(package)
        except ImportError:
            print(f"  ❌ {package} - MISSING")
            missing.append(package)

    print("\n" + "=" * 70)
    print(f"Summary: {len(installed)}/{len(dependencies)} packages installed")
    print("=" * 70)

    if missing:
        print(f"\n❌ Missing {len(missing)} packages: {', '.join(missing)}")
        print("\nInstall missing packages with:")
        print(f"  pip install {' '.join(missing)}")
        print("\nOr install all from requirements.txt:")
        print("  pip install -r requirements.txt")
        return False
    else:
        print("\n✅ All dependencies installed!")
        return True

if __name__ == "__main__":
    success = check_and_install_dependencies()
    sys.exit(0 if success else 1)
