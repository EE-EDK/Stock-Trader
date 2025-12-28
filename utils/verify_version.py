#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Version verification script - checks if you have all the bug fixes
"""

import os
import sys

# Fix Windows Unicode issues
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

print("=" * 70)
print("STOCK TRADER VERSION VERIFICATION")
print("=" * 70)

fixes = {
    "Paper trading price extraction fix": {
        "file": "main.py",
        "line": 391,
        "should_contain": "price_data['price']",
        "description": "Line 391 should extract price from dict"
    },
    "Dashboard variable initialization": {
        "file": "main.py",
        "line": 131,
        "should_contain": "macro_indicators = {}",
        "description": "Lines 130-133 should initialize optional variables"
    },
    "Signal generator NoneType check": {
        "file": "src/signals/generator.py",
        "line": 306,
        "should_contain": "if rsi is None:",
        "description": "Line 306 should check for None before comparison"
    },
    "Paper trading JSON parsing": {
        "file": "src/trading/paper_trading.py",
        "line": 266,
        "should_contain": "triggers_json.strip()",
        "description": "Line 266 should use .strip() to check empty string"
    },
    "FRED initialization": {
        "file": "main.py",
        "line": 268,
        "should_not_contain": "config=config",
        "description": "Line 268 should NOT pass config parameter to FREDCollector"
    }
}

all_good = True

for fix_name, details in fixes.items():
    filepath = details["file"]
    line_num = details["line"]

    if not os.path.exists(filepath):
        print(f"\n✗ {fix_name}")
        print(f"  File not found: {filepath}")
        all_good = False
        continue

    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    if line_num > len(lines):
        print(f"\n✗ {fix_name}")
        print(f"  Line {line_num} doesn't exist in {filepath}")
        all_good = False
        continue

    line_content = lines[line_num - 1]

    if "should_contain" in details:
        if details["should_contain"] in line_content:
            print(f"\n✓ {fix_name}")
            print(f"  {details['description']}")
        else:
            print(f"\n✗ {fix_name} - MISSING")
            print(f"  {details['description']}")
            print(f"  Current line {line_num}: {line_content.strip()}")
            print(f"  Should contain: {details['should_contain']}")
            all_good = False

    if "should_not_contain" in details:
        if details["should_not_contain"] not in line_content:
            print(f"\n✓ {fix_name}")
            print(f"  {details['description']}")
        else:
            print(f"\n✗ {fix_name} - NEEDS FIX")
            print(f"  {details['description']}")
            print(f"  Current line {line_num}: {line_content.strip()}")
            print(f"  Should NOT contain: {details['should_not_contain']}")
            all_good = False

print("\n" + "=" * 70)
if all_good:
    print("✅ ALL FIXES PRESENT - Your code is up to date!")
else:
    print("❌ MISSING FIXES - You need to pull the latest changes!")
    print("\nRun this command to get all fixes:")
    print("  git pull origin claude/integrate-free-data-sources-5pKwa")
print("=" * 70)
