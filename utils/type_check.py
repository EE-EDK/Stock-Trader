#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Comprehensive type verification for the Stock Trader project
Checks for common type-related issues that cause runtime errors
"""

import ast
import os
import sys
from pathlib import Path
from typing import List, Dict, Set, Tuple
import re

# Fix Windows Unicode issues
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


class TypeChecker(ast.NodeVisitor):
    def __init__(self, filename):
        self.filename = filename
        self.issues = []
        self.current_function = None
        self.function_returns = {}  # Track what functions return
        self.dict_accesses = []  # Track dictionary key accesses
        self.comparisons = []  # Track comparisons
        self.math_operations = []  # Track math operations

    def visit_FunctionDef(self, node):
        self.current_function = node.name

        # Check for type hints in return annotation
        return_type = None
        if node.returns:
            return_type = ast.unparse(node.returns)

        self.function_returns[node.name] = {
            'return_type': return_type,
            'lineno': node.lineno
        }

        self.generic_visit(node)
        self.current_function = None

    def visit_Subscript(self, node):
        """Check dictionary/list accesses"""
        # Check for dict.get() vs dict[] usage
        if isinstance(node.value, ast.Attribute):
            if node.value.attr == 'get':
                # Good - using .get()
                pass
        elif isinstance(node.value, ast.Name):
            # Direct subscription - might be risky
            self.dict_accesses.append({
                'lineno': node.lineno,
                'code': ast.unparse(node),
                'type': 'direct_subscript'
            })

        self.generic_visit(node)

    def visit_Compare(self, node):
        """Check comparisons for potential NoneType issues"""
        # Check for comparisons without None checks
        for op in node.ops:
            if isinstance(op, (ast.Lt, ast.LtE, ast.Gt, ast.GtE)):
                # Numeric comparison - check if operands might be None
                self.comparisons.append({
                    'lineno': node.lineno,
                    'code': ast.unparse(node),
                    'operator': op.__class__.__name__
                })

        self.generic_visit(node)

    def visit_BinOp(self, node):
        """Check binary operations (math)"""
        if isinstance(node.op, (ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Mod)):
            self.math_operations.append({
                'lineno': node.lineno,
                'code': ast.unparse(node),
                'operator': node.op.__class__.__name__
            })

        self.generic_visit(node)

    def visit_Call(self, node):
        """Check function calls"""
        # Check for .get() calls without defaults
        if isinstance(node.func, ast.Attribute):
            if node.func.attr == 'get' and len(node.args) == 1:
                # dict.get(key) without default - might return None
                self.issues.append({
                    'severity': 'warning',
                    'lineno': node.lineno,
                    'message': f".get() called without default value: {ast.unparse(node)}",
                    'suggestion': 'Consider providing a default value to handle missing keys'
                })

        self.generic_visit(node)


def analyze_file(filepath: str) -> List[Dict]:
    """Analyze a Python file for type issues"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            source = f.read()

        tree = ast.parse(source, filename=filepath)
        checker = TypeChecker(filepath)
        checker.visit(tree)

        return checker.issues, checker
    except SyntaxError as e:
        return [{'severity': 'error', 'lineno': e.lineno, 'message': f'Syntax error: {e}'}], None
    except Exception as e:
        return [{'severity': 'error', 'lineno': 0, 'message': f'Failed to parse: {e}'}], None


def check_dict_float_issues(filepath: str, source_lines: List[str]) -> List[Dict]:
    """
    Check for dict/float type confusion issues
    Common pattern: function returns Dict[str, Dict] but caller expects Dict[str, float]
    """
    issues = []

    # Pattern 1: db.get_latest_prices() returns dict but used as float
    source_all = ''.join(source_lines)
    if 'db.get_latest_prices()' in source_all:
        for i, line in enumerate(source_lines, 1):
            if 'db.get_latest_prices()' in line:
                # Check next few lines for direct math operations
                for j in range(i, min(i + 10, len(source_lines))):
                    next_line = source_lines[j - 1]
                    # Look for math operations without ['price'] extraction
                    if any(op in next_line for op in [' - ', ' + ', ' * ', ' / ']) and "['price']" not in next_line and '.get(' not in next_line:
                        issues.append({
                            'severity': 'error',
                            'lineno': j,
                            'message': 'Potential dict/float confusion: db.get_latest_prices() returns Dict[str, Dict], extract price first',
                            'suggestion': "Use: price_data = db.get_latest_prices().get(ticker); price = price_data['price']",
                            'code': next_line.strip()
                        })
                        break

    # Pattern 2: Variables named 'price' or 'current_price' assigned from dict
    for i, line in enumerate(source_lines, 1):
        # Check for: current_price = something.get(ticker) without ['price']
        match = re.search(r'(current_price|price)\s*=\s*.*\.get\([^)]+\)', line)
        if match:
            # Check if there's a ['price'] extraction on same or next line
            if "['price']" not in line:
                next_line = source_lines[i] if i < len(source_lines) else ""
                if "['price']" not in next_line:
                    issues.append({
                        'severity': 'warning',
                        'lineno': i,
                        'message': 'Variable assigned from .get() might be dict, not float',
                        'suggestion': 'If getting from price dict, extract: variable["price"]',
                        'code': line.strip()
                    })

    return issues


def check_none_comparison_issues(filepath: str, source_lines: List[str]) -> List[Dict]:
    """Check for comparisons that might fail with None values"""
    issues = []

    for i, line in enumerate(source_lines, 1):
        # Look for comparisons without None checks
        if any(op in line for op in [' < ', ' > ', ' <= ', ' >= ']):
            # Check if there's a None check before this
            has_none_check = False

            # Look back a few lines for None check
            for j in range(max(0, i - 5), i):
                if 'is None' in source_lines[j] or 'is not None' in source_lines[j]:
                    has_none_check = True
                    break

            # Extract variable being compared
            match = re.search(r'(\w+)\s*[<>=]+\s*', line)
            if match:
                var_name = match.group(1)

                # Check if this variable comes from .get()
                for j in range(max(0, i - 10), i):
                    if f"{var_name} = " in source_lines[j] and '.get(' in source_lines[j]:
                        if not has_none_check:
                            issues.append({
                                'severity': 'error',
                                'lineno': i,
                                'message': f'Comparison of "{var_name}" which might be None (from .get())',
                                'suggestion': f'Add check: if {var_name} is None: return False',
                                'code': line.strip()
                            })
                        break

    return issues


def check_json_loads_issues(filepath: str, source_lines: List[str]) -> List[Dict]:
    """Check for unsafe json.loads() calls"""
    issues = []

    for i, line in enumerate(source_lines, 1):
        if 'json.loads(' in line:
            # Check if there's error handling
            has_try = False
            for j in range(max(0, i - 5), i):
                if 'try:' in source_lines[j]:
                    has_try = True
                    break

            # Check if there's empty string check
            has_empty_check = '.strip()' in line or 'if ' in source_lines[i - 2] if i > 1 else False

            if not has_try and not has_empty_check:
                issues.append({
                    'severity': 'warning',
                    'lineno': i,
                    'message': 'json.loads() without try-except or empty string check',
                    'suggestion': 'Wrap in try-except or check: if json_str and json_str.strip()',
                    'code': line.strip()
                })

    return issues


def run_type_verification():
    """Run full type verification on the project"""
    print("=" * 80)
    print("STOCK TRADER - COMPREHENSIVE TYPE VERIFICATION")
    print("=" * 80)

    # Files to check
    python_files = []
    for root, dirs, files in os.walk('.'):
        # Skip venv, __pycache__, .git
        dirs[:] = [d for d in dirs if d not in ['venv', '__pycache__', '.git', '.pytest_cache', 'reports', 'logs']]

        for file in files:
            if file.endswith('.py') and not file.startswith('test_'):
                filepath = os.path.join(root, file)
                python_files.append(filepath)

    all_issues = []

    for filepath in sorted(python_files):
        print(f"\n{'='*80}")
        print(f"Checking: {filepath}")
        print('='*80)

        # Read source
        with open(filepath, 'r', encoding='utf-8') as f:
            source_lines = f.readlines()

        # AST analysis
        ast_issues, checker = analyze_file(filepath)

        # Specific pattern checks
        dict_float_issues = check_dict_float_issues(filepath, source_lines)
        none_comparison_issues = check_none_comparison_issues(filepath, source_lines)
        json_issues = check_json_loads_issues(filepath, source_lines)

        # Combine all issues
        file_issues = ast_issues + dict_float_issues + none_comparison_issues + json_issues

        if file_issues:
            all_issues.extend([(filepath, issue) for issue in file_issues])

            # Group by severity
            errors = [i for i in file_issues if i.get('severity') == 'error']
            warnings = [i for i in file_issues if i.get('severity') == 'warning']

            if errors:
                print(f"\n🔴 ERRORS ({len(errors)}):")
                for issue in errors:
                    print(f"\n  Line {issue['lineno']}: {issue['message']}")
                    if 'code' in issue:
                        print(f"    Code: {issue['code']}")
                    if 'suggestion' in issue:
                        print(f"    💡 {issue['suggestion']}")

            if warnings:
                print(f"\n⚠️  WARNINGS ({len(warnings)}):")
                for issue in warnings:
                    print(f"\n  Line {issue['lineno']}: {issue['message']}")
                    if 'code' in issue:
                        print(f"    Code: {issue['code']}")
                    if 'suggestion' in issue:
                        print(f"    💡 {issue['suggestion']}")
        else:
            print("  ✅ No issues found")

        # Additional stats
        if checker:
            if checker.comparisons:
                print(f"\n📊 Statistics:")
                print(f"  - {len(checker.comparisons)} comparisons found")
                print(f"  - {len(checker.math_operations)} math operations found")
                print(f"  - {len(checker.dict_accesses)} dict accesses found")

    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)

    errors = [(f, i) for f, i in all_issues if i.get('severity') == 'error']
    warnings = [(f, i) for f, i in all_issues if i.get('severity') == 'warning']

    print(f"\n📊 Total files checked: {len(python_files)}")
    print(f"🔴 Total errors: {len(errors)}")
    print(f"⚠️  Total warnings: {len(warnings)}")

    if errors:
        print("\n🔴 CRITICAL ISSUES BY FILE:")
        error_by_file = {}
        for filepath, issue in errors:
            if filepath not in error_by_file:
                error_by_file[filepath] = []
            error_by_file[filepath].append(issue)

        for filepath, issues in sorted(error_by_file.items()):
            print(f"\n  {filepath} ({len(issues)} errors):")
            for issue in issues:
                print(f"    Line {issue['lineno']}: {issue['message']}")

    if warnings:
        print("\n⚠️  WARNINGS BY FILE:")
        warning_by_file = {}
        for filepath, issue in warnings:
            if filepath not in warning_by_file:
                warning_by_file[filepath] = []
            warning_by_file[filepath].append(issue)

        for filepath, issues in sorted(warning_by_file.items()):
            print(f"\n  {filepath} ({len(issues)} warnings):")
            for issue in issues[:3]:  # Show first 3
                print(f"    Line {issue['lineno']}: {issue['message']}")
            if len(issues) > 3:
                print(f"    ... and {len(issues) - 3} more")

    print("\n" + "=" * 80)

    if errors:
        print("❌ TYPE VERIFICATION FAILED - Fix critical errors above")
        return 1
    elif warnings:
        print("⚠️  TYPE VERIFICATION PASSED WITH WARNINGS - Review warnings above")
        return 0
    else:
        print("✅ TYPE VERIFICATION PASSED - No issues found!")
        return 0


if __name__ == "__main__":
    exit(run_type_verification())
