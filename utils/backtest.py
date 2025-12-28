#!/usr/bin/env python3
"""
@file backtest.py
@brief CLI tool for backtesting trading signals
@details Runs backtest against historical signal data and generates report
@usage python backtest.py --start 2024-01-01 --end 2024-12-31
"""

import argparse
import yaml
import sys
import os
from datetime import datetime, timedelta
from pathlib import Path

# Add project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.analysis.backtester import Backtester


def load_config(config_path: str = "config/config.yaml") -> dict:
    """Load configuration from YAML file"""
    try:
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        print(f"Error: Configuration file not found: {config_path}")
        print("Please copy config/config.example.yaml to config/config.yaml")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description='Backtest trading signals against historical data',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Backtest last 90 days
  python backtest.py --days 90

  # Backtest specific date range
  python backtest.py --start 2024-01-01 --end 2024-12-31

  # Backtest with custom config
  python backtest.py --days 60 --config custom_config.yaml

  # Export results to file
  python backtest.py --days 90 --output backtest_results.txt
        """
    )

    parser.add_argument(
        '--start',
        type=str,
        help='Start date (YYYY-MM-DD)'
    )
    parser.add_argument(
        '--end',
        type=str,
        help='End date (YYYY-MM-DD)'
    )
    parser.add_argument(
        '--days',
        type=int,
        default=90,
        help='Number of days to backtest (default: 90, used if --start not provided)'
    )
    parser.add_argument(
        '--config',
        default='config/config.yaml',
        help='Path to configuration file (default: config/config.yaml)'
    )
    parser.add_argument(
        '--output',
        type=str,
        help='Output file for results (default: print to console)'
    )
    parser.add_argument(
        '--db',
        type=str,
        help='Database path (overrides config)'
    )

    args = parser.parse_args()

    # Load config
    config = load_config(args.config)

    # Determine date range
    if args.start and args.end:
        try:
            start_date = datetime.strptime(args.start, '%Y-%m-%d')
            end_date = datetime.strptime(args.end, '%Y-%m-%d')
        except ValueError:
            print("Error: Invalid date format. Use YYYY-MM-DD")
            sys.exit(1)
    else:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=args.days)

    # Get database path
    db_path = args.db or config['database']['path']

    print("=" * 70)
    print("STOCK TRADING SIGNALS - BACKTEST")
    print("=" * 70)
    print(f"Database: {db_path}")
    print(f"Period: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
    print(f"Duration: {(end_date - start_date).days} days")
    print()

    # Create backtester
    print("Initializing backtester...")
    backtester = Backtester(db_path=db_path, config=config)

    # Display settings
    print(f"Settings:")
    print(f"  Initial Capital:    ${backtester.initial_capital:,.2f}")
    print(f"  Position Size:      ${backtester.position_size:,.2f}")
    print(f"  Max Positions:      {backtester.max_positions}")
    print(f"  Min Conviction:     {backtester.min_conviction}")
    print(f"  Stop Loss:          {backtester.stop_loss_pct}%")
    print(f"  Take Profit:        {backtester.take_profit_pct}%")
    print(f"  Max Hold Days:      {backtester.hold_days}")
    print(f"  Conviction Weighted: {'Yes' if backtester.use_conviction_weighted else 'No'}")
    print()

    # Run backtest
    print("Running backtest...")
    results = backtester.run_backtest(start_date, end_date)

    # Generate report
    report = backtester.generate_report(results)

    # Output results
    if args.output:
        with open(args.output, 'w') as f:
            f.write(report)
        print(f"\n✅ Results saved to: {args.output}")
    else:
        print("\n" + report)

    # Summary
    print("\n" + "=" * 70)
    if results.total_trades == 0:
        print("⚠️  No trades executed - check if signals exist in this date range")
    elif results.win_rate >= 60 and results.total_return_pct > 0:
        print("✅ EXCELLENT PERFORMANCE - Strategy shows strong potential")
    elif results.win_rate >= 50 and results.total_return_pct > 0:
        print("✅ GOOD PERFORMANCE - Strategy is profitable")
    elif results.total_return_pct > 0:
        print("⚠️  MARGINAL PERFORMANCE - Consider adjusting thresholds")
    else:
        print("❌ POOR PERFORMANCE - Strategy needs significant improvement")
    print("=" * 70)


if __name__ == "__main__":
    main()
