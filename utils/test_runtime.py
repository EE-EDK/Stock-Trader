#!/usr/bin/env python3
"""
Runtime validation script - tests imports and basic functionality
"""

import sys
import os

print("=" * 70)
print("RUNTIME VALIDATION TEST - Testing imports and basic execution")
print("=" * 70)

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
    ('src.collectors.fmp', 'FMP collector'),
    ('src.collectors.yfinance_collector', 'YFinance collector'),
    ('src.collectors.vader_sentiment', 'VADER sentiment'),
    ('src.collectors.reddit_collector', 'Reddit collector'),
    ('src.collectors.fred', 'FRED collector'),
    ('src.collectors.congress', 'Congress collector'),
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
        successes.append(f"✅ {friendly_name}")
        print(f"  ✅ {friendly_name}")
    except Exception as e:
        errors.append(f"❌ {friendly_name}: {e}")
        print(f"  ❌ {friendly_name}: {e}")

# Test 2: Test collector class instantiation with test config
print("\n[TEST 2] Testing collector instantiation...")
test_collectors = []

try:
    from src.collectors.apewisdom import ApeWisdomCollector
    ape = ApeWisdomCollector()
    ape.close()
    successes.append("✅ ApeWisdomCollector instantiation")
    print("  ✅ ApeWisdomCollector instantiation")
except Exception as e:
    errors.append(f"❌ ApeWisdomCollector: {e}")
    print(f"  ❌ ApeWisdomCollector: {e}")

try:
    from src.collectors.openinsider import OpenInsiderCollector
    insider = OpenInsiderCollector()
    insider.close()
    successes.append("✅ OpenInsiderCollector instantiation")
    print("  ✅ OpenInsiderCollector instantiation")
except Exception as e:
    errors.append(f"❌ OpenInsiderCollector: {e}")
    print(f"  ❌ OpenInsiderCollector: {e}")

try:
    from src.collectors.finnhub import FinnhubCollector
    finnhub = FinnhubCollector(api_key="test_key")
    successes.append("✅ FinnhubCollector instantiation")
    print("  ✅ FinnhubCollector instantiation")
except Exception as e:
    errors.append(f"❌ FinnhubCollector: {e}")
    print(f"  ❌ FinnhubCollector: {e}")

try:
    from src.collectors.congress import CongressTradesCollector
    congress = CongressTradesCollector({'collection': {'congress': {'enabled': True, 'lookback_days': 90}}})
    successes.append("✅ CongressTradesCollector instantiation")
    print("  ✅ CongressTradesCollector instantiation")
except Exception as e:
    errors.append(f"❌ CongressTradesCollector: {e}")
    print(f"  ❌ CongressTradesCollector: {e}")

try:
    from src.collectors.fred import FREDCollector
    fred = FREDCollector(api_key="test_key", config={})
    successes.append("✅ FREDCollector instantiation")
    print("  ✅ FREDCollector instantiation")
except Exception as e:
    errors.append(f"❌ FREDCollector: {e}")
    print(f"  ❌ FREDCollector: {e}")

try:
    from src.collectors.yfinance_collector import YFinanceCollector
    yf = YFinanceCollector()
    successes.append("✅ YFinanceCollector instantiation")
    print("  ✅ YFinanceCollector instantiation")
except Exception as e:
    errors.append(f"❌ YFinanceCollector: {e}")
    print(f"  ❌ YFinanceCollector: {e}")

# Test 3: Test database initialization
print("\n[TEST 3] Testing database operations...")
try:
    from src.database.models import Database
    db = Database('data/test_runtime.db')
    db.initialize()
    db.close()
    if os.path.exists('data/test_runtime.db'):
        os.remove('data/test_runtime.db')
    successes.append("✅ Database initialization")
    print("  ✅ Database initialization")
except Exception as e:
    errors.append(f"❌ Database: {e}")
    print(f"  ❌ Database: {e}")

# Test 4: Test signal generation classes
print("\n[TEST 4] Testing signal generation...")
try:
    from src.signals.generator import SignalGenerator
    from datetime import datetime
    sg = SignalGenerator(min_sentiment_score=0.5, min_velocity_threshold=1.5)
    successes.append("✅ SignalGenerator instantiation")
    print("  ✅ SignalGenerator instantiation")
except Exception as e:
    errors.append(f"❌ SignalGenerator: {e}")
    print(f"  ❌ SignalGenerator: {e}")

# Test 5: Test metrics calculators
print("\n[TEST 5] Testing metrics calculators...")
try:
    from src.metrics.velocity import VelocityCalculator
    vc = VelocityCalculator()
    successes.append("✅ VelocityCalculator instantiation")
    print("  ✅ VelocityCalculator instantiation")
except Exception as e:
    errors.append(f"❌ VelocityCalculator: {e}")
    print(f"  ❌ VelocityCalculator: {e}")

try:
    from src.metrics.technical import TechnicalAnalyzer
    ta = TechnicalAnalyzer()
    successes.append("✅ TechnicalAnalyzer instantiation")
    print("  ✅ TechnicalAnalyzer instantiation")
except Exception as e:
    errors.append(f"❌ TechnicalAnalyzer: {e}")
    print(f"  ❌ TechnicalAnalyzer: {e}")

# Test 6: Test dashboard generator
print("\n[TEST 6] Testing dashboard generator...")
try:
    from src.reporters.dashboard import DashboardGenerator
    dashboard = DashboardGenerator(output_dir="reports_test")
    successes.append("✅ DashboardGenerator instantiation")
    print("  ✅ DashboardGenerator instantiation")

    # Test generate method signature
    import inspect
    sig = inspect.signature(dashboard.generate)
    params = list(sig.parameters.keys())
    required_params = ['signals', 'velocity_data', 'technical_data', 'sentiment_data',
                       'reddit_data', 'paper_trading_stats', 'macro_indicators',
                       'market_assessment', 'congress_trades']

    missing = [p for p in required_params if p not in params]
    if missing:
        errors.append(f"❌ Dashboard.generate missing parameters: {missing}")
        print(f"  ❌ Dashboard.generate missing parameters: {missing}")
    else:
        successes.append("✅ Dashboard.generate signature correct")
        print("  ✅ Dashboard.generate signature correct")

except Exception as e:
    errors.append(f"❌ DashboardGenerator: {e}")
    print(f"  ❌ DashboardGenerator: {e}")

# Test 7: Test paper trading system
print("\n[TEST 7] Testing paper trading system...")
try:
    from src.trading.paper_trading import PaperTradingSystem
    from src.database.models import Database
    db = Database('data/test_runtime2.db')
    db.initialize()
    pts = PaperTradingSystem(db, {'enabled': False, 'initial_capital': 10000})
    db.close()
    if os.path.exists('data/test_runtime2.db'):
        os.remove('data/test_runtime2.db')
    successes.append("✅ PaperTradingSystem instantiation")
    print("  ✅ PaperTradingSystem instantiation")
except Exception as e:
    errors.append(f"❌ PaperTradingSystem: {e}")
    print(f"  ❌ PaperTradingSystem: {e}")

# Test 8: Test backtester
print("\n[TEST 8] Testing backtester...")
try:
    from src.analysis.backtester import Backtester
    from src.database.models import Database
    db = Database('data/test_runtime3.db')
    db.initialize()
    bt = Backtester(db, {'initial_capital': 10000})
    db.close()
    if os.path.exists('data/test_runtime3.db'):
        os.remove('data/test_runtime3.db')
    successes.append("✅ Backtester instantiation")
    print("  ✅ Backtester instantiation")
except Exception as e:
    errors.append(f"❌ Backtester: {e}")
    print(f"  ❌ Backtester: {e}")

# Test 9: Check critical functions in main.py
print("\n[TEST 9] Testing main.py structure...")
try:
    import main

    # Check for run_pipeline function
    if hasattr(main, 'run_pipeline'):
        successes.append("✅ main.run_pipeline exists")
        print("  ✅ main.run_pipeline exists")
    else:
        errors.append("❌ main.run_pipeline not found")
        print("  ❌ main.run_pipeline not found")

    # Check for required imports
    if hasattr(main, 'Database'):
        successes.append("✅ main.py imports Database")
        print("  ✅ main.py imports Database")
    else:
        errors.append("❌ main.py missing Database import")
        print("  ❌ main.py missing Database import")

except Exception as e:
    errors.append(f"❌ main.py structure: {e}")
    print(f"  ❌ main.py structure: {e}")

# Final summary
print("\n" + "=" * 70)
print("RUNTIME VALIDATION SUMMARY")
print("=" * 70)
print(f"\n✅ Successes: {len(successes)}")
print(f"❌ Errors: {len(errors)}")

if errors:
    print("\n❌ ERRORS FOUND:")
    for error in errors:
        print(f"  {error}")
    sys.exit(1)
else:
    print("\n✅ ALL RUNTIME VALIDATION TESTS PASSED")
    print("=" * 70)
    sys.exit(0)
