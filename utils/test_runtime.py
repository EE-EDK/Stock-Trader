#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Runtime validation script - tests imports and basic functionality
"""

import sys
import os

# Add project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

print("=" * 70)
print("RUNTIME VALIDATION TEST - Testing imports and basic execution")
print("=" * 70)

# Check for critical dependencies first
print("\n[DEPENDENCY CHECK] Checking critical Python packages...")
missing_deps = []
critical_packages = [
    ('bs4', 'beautifulsoup4'),
    ('numpy', 'numpy'),
    ('yaml', 'pyyaml'),
    ('requests', 'requests'),
]

for import_name, package_name in critical_packages:
    try:
        __import__(import_name)
        print(f"  [OK] {package_name}")
    except ImportError:
        print(f"  [MISSING] {package_name}")
        missing_deps.append(package_name)

if missing_deps:
    print(f"\n  WARNING: {len(missing_deps)} critical packages missing")
    print(f"   Missing: {', '.join(missing_deps)}")
    print("\nInstall missing packages:")
    print(f"  pip install {' '.join(missing_deps)}")
    print("\nOr install all dependencies:")
    print("  pip install -r requirements.txt")
    print("\nContinuing with tests (some will fail)...\n")

errors = []
successes = []

# Test 1: Import all main modules
print("\n[TEST 1] Testing module imports...")
modules_to_test = [
    ('main', 'main'),
    ('backtest', 'backtest'),
    ('src.collectors.apewisdom', 'ApeWisdom collector'),
    ('src.collectors.openinsider', 'OpenInsider collector'),
    ('src.collectors.finnhub', 'Finnhub collector'),
    ('src.collectors.alphavantage', 'AlphaVantage collector'),
    ('src.collectors.yfinance_collector', 'YFinance collector'),
    ('src.collectors.vader_sentiment', 'VADER sentiment'),
    ('src.collectors.fred', 'FRED collector'),
    ('src.database.models', 'Database models'),
    ('src.database.queries', 'Database queries'),
    ('src.metrics.velocity', 'Velocity metrics'),
    ('src.metrics.technical', 'Technical metrics'),
    ('src.signals.generator', 'Signal generator'),
    ('src.reporters.dashboard', 'Dashboard generator'),
    ('src.reporters.charts', 'Charts'),
    ('src.reporters.email', 'Email reporter'),
    ('src.trading.paper_trading', 'Paper trading'),
    ('src.analysis.backtester', 'Backtester'),
]

for module_name, friendly_name in modules_to_test:
    try:
        __import__(module_name)
        successes.append(f"[OK] {friendly_name}")
        print(f"  [OK] {friendly_name}")
    except Exception as e:
        errors.append(f"[FAIL] {friendly_name}: {e}")
        print(f"  [FAIL] {friendly_name}: {e}")

# Test 2: Test collector class instantiation with test config
print("\n[TEST 2] Testing collector instantiation...")
test_collectors = []

try:
    from src.collectors.apewisdom import ApeWisdomCollector
    ape = ApeWisdomCollector()
    ape.close()
    successes.append("[OK] ApeWisdomCollector instantiation")
    print("  [OK] ApeWisdomCollector instantiation")
except Exception as e:
    errors.append(f"[FAIL] ApeWisdomCollector: {e}")
    print(f"  [FAIL] ApeWisdomCollector: {e}")

try:
    from src.collectors.openinsider import OpenInsiderCollector
    insider = OpenInsiderCollector()
    insider.close()
    successes.append("[OK] OpenInsiderCollector instantiation")
    print("  [OK] OpenInsiderCollector instantiation")
except Exception as e:
    errors.append(f"[FAIL] OpenInsiderCollector: {e}")
    print(f"  [FAIL] OpenInsiderCollector: {e}")

try:
    from src.collectors.finnhub import FinnhubCollector
    finnhub = FinnhubCollector(api_key="test_key")
    successes.append("[OK] FinnhubCollector instantiation")
    print("  [OK] FinnhubCollector instantiation")
except Exception as e:
    errors.append(f"[FAIL] FinnhubCollector: {e}")
    print(f"  [FAIL] FinnhubCollector: {e}")

try:
    from src.collectors.fred import FREDCollector
    fred = FREDCollector(api_key="test_key")
    successes.append("[OK] FREDCollector instantiation")
    print("  [OK] FREDCollector instantiation")
except Exception as e:
    errors.append(f"[FAIL] FREDCollector: {e}")
    print(f"  [FAIL] FREDCollector: {e}")

try:
    from src.collectors.yfinance_collector import YFinanceCollector
    yf = YFinanceCollector()
    successes.append("[OK] YFinanceCollector instantiation")
    print("  [OK] YFinanceCollector instantiation")
except Exception as e:
    errors.append(f"[FAIL] YFinanceCollector: {e}")
    print(f"  [FAIL] YFinanceCollector: {e}")

# Test 3: Test database initialization
print("\n[TEST 3] Testing database operations...")
try:
    from src.database.models import Database
    db = Database('data/test_runtime.db')
    db.initialize()
    db.close()
    if os.path.exists('data/test_runtime.db'):
        os.remove('data/test_runtime.db')
    successes.append("[OK] Database initialization")
    print("  [OK] Database initialization")
except Exception as e:
    errors.append(f"[FAIL] Database: {e}")
    print(f"  [FAIL] Database: {e}")

# Test 4: Test signal generation classes
print("\n[TEST 4] Testing signal generation...")
try:
    from src.signals.generator import SignalGenerator
    from datetime import datetime
    sg = SignalGenerator()
    successes.append("[OK] SignalGenerator instantiation")
    print("  [OK] SignalGenerator instantiation")
except Exception as e:
    errors.append(f"[FAIL] SignalGenerator: {e}")
    print(f"  [FAIL] SignalGenerator: {e}")

# Test 5: Test metrics calculators
print("\n[TEST 5] Testing metrics calculators...")
try:
    from src.metrics.velocity import VelocityCalculator
    from src.database.models import Database
    test_db = Database(':memory:')
    test_db.initialize()
    vc = VelocityCalculator(database=test_db)
    successes.append("[OK] VelocityCalculator instantiation")
    print("  [OK] VelocityCalculator instantiation")
except Exception as e:
    errors.append(f"[FAIL] VelocityCalculator: {e}")
    print(f"  [FAIL] VelocityCalculator: {e}")

try:
    from src.metrics.technical import TechnicalAnalyzer
    from src.database.models import Database
    test_db = Database(':memory:')
    test_db.initialize()
    ta = TechnicalAnalyzer(database=test_db)
    successes.append("[OK] TechnicalAnalyzer instantiation")
    print("  [OK] TechnicalAnalyzer instantiation")
except Exception as e:
    errors.append(f"[FAIL] TechnicalAnalyzer: {e}")
    print(f"  [FAIL] TechnicalAnalyzer: {e}")

# Test 6: Test dashboard generator
print("\n[TEST 6] Testing dashboard generator...")
try:
    # Pipeline uses dashboard_v2 (ModernDashboardGenerator), not dashboard.py
    from src.reporters.dashboard_v2 import ModernDashboardGenerator as DashboardGenerator
    dashboard = DashboardGenerator(output_dir="reports_test")
    successes.append("[OK] DashboardGenerator (dashboard_v2) instantiation")
    print("  [OK] DashboardGenerator (dashboard_v2) instantiation")

    # Test generate method signature (must match main.py call)
    import inspect
    sig = inspect.signature(dashboard.generate)
    params = list(sig.parameters.keys())
    required_params = ['signals', 'velocity_data', 'technical_data', 'sentiment_data',
                       'paper_trading_stats', 'macro_indicators', 'market_assessment', 'db']

    missing = [p for p in required_params if p not in params]
    if missing:
        errors.append(f"[FAIL] Dashboard.generate missing parameters: {missing}")
        print(f"  [FAIL] Dashboard.generate missing parameters: {missing}")
    else:
        successes.append("[OK] Dashboard.generate signature correct")
        print("  [OK] Dashboard.generate signature correct")

except Exception as e:
    errors.append(f"[FAIL] DashboardGenerator: {e}")
    print(f"  [FAIL] DashboardGenerator: {e}")

# Test 7: Test paper trading system (PaperTradingManager expects db_path: str, config: dict)
print("\n[TEST 7] Testing paper trading system...")
try:
    from src.trading.paper_trading import PaperTradingManager
    from src.database.models import Database
    db_path = 'data/test_runtime2.db'
    db = Database(db_path)
    db.initialize()
    pts = PaperTradingManager(db_path, {'paper_trading': {'enabled': False}})
    db.close()
    if os.path.exists(db_path):
        os.remove(db_path)
    successes.append("[OK] PaperTradingManager instantiation")
    print("  [OK] PaperTradingManager instantiation")
except Exception as e:
    errors.append(f"[FAIL] PaperTradingManager: {e}")
    print(f"  [FAIL] PaperTradingManager: {e}")

# Test 8: Test backtester (Backtester expects db_path: str, config: dict)
print("\n[TEST 8] Testing backtester...")
try:
    from src.analysis.backtester import Backtester
    from src.database.models import Database
    db_path = 'data/test_runtime3.db'
    db = Database(db_path)
    db.initialize()
    bt = Backtester(db_path, {'backtesting': {'initial_capital': 10000}})
    db.close()
    if os.path.exists(db_path):
        os.remove(db_path)
    successes.append("[OK] Backtester instantiation")
    print("  [OK] Backtester instantiation")
except Exception as e:
    errors.append(f"[FAIL] Backtester: {e}")
    print(f"  [FAIL] Backtester: {e}")

# Test 9: Check critical functions in main.py
print("\n[TEST 9] Testing main.py structure...")
try:
    import main

    # Check for run_pipeline function
    if hasattr(main, 'run_pipeline'):
        successes.append("[OK] main.run_pipeline exists")
        print("  [OK] main.run_pipeline exists")
    else:
        errors.append("[FAIL] main.run_pipeline not found")
        print("  [FAIL] main.run_pipeline not found")

    # Check for required imports
    if hasattr(main, 'Database'):
        successes.append("[OK] main.py imports Database")
        print("  [OK] main.py imports Database")
    else:
        errors.append("[FAIL] main.py missing Database import")
        print("  [FAIL] main.py missing Database import")

except Exception as e:
    errors.append(f"[FAIL] main.py structure: {e}")
    print(f"  [FAIL] main.py structure: {e}")

# Final summary
print("\n" + "=" * 70)
print("RUNTIME VALIDATION SUMMARY")
print("=" * 70)
print(f"\n[OK] Successes: {len(successes)}")
print(f"[FAIL] Errors: {len(errors)}")

# Categorize errors
dependency_errors = [e for e in errors if any(dep in e for dep in ['bs4', 'numpy', 'matplotlib', 'yfinance', 'No module'])]
code_errors = [e for e in errors if e not in dependency_errors]

if errors:
    if dependency_errors:
        print(f"\n[DEPS] DEPENDENCY ERRORS ({len(dependency_errors)}):")
        for error in dependency_errors:
            print(f"  {error}")
        print("\n  Fix by running: pip install -r requirements.txt")

    if code_errors:
        print(f"\n[CODE] CODE ERRORS ({len(code_errors)}):")
        for error in code_errors:
            print(f"  {error}")

    if code_errors:
        print("\n[FAIL] CRITICAL: Code errors found - fix required!")
        sys.exit(1)
    else:
        print("\nWARNING  Tests incomplete due to missing dependencies")
        print("   Install dependencies to run full validation")
        sys.exit(0)
else:
    print("\n[OK] ALL RUNTIME VALIDATION TESTS PASSED")
    print("=" * 70)
    sys.exit(0)
