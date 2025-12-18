#!/usr/bin/env python3
"""
@file main.py
@brief Sentiment Velocity Tracker - Main Pipeline Orchestrator
@details Daily pipeline for collecting social data, calculating velocity, and generating trading signals
@usage Run daily via cron: 0 6 * * * cd /path/to/sentiment_velocity && python main.py
"""

import logging
import sys
from datetime import datetime
from pathlib import Path
import yaml
import argparse

from src.collectors.apewisdom import ApeWisdomCollector
from src.collectors.openinsider import OpenInsiderCollector
from src.collectors.finnhub import FinnhubCollector
from src.database.models import Database
from src.metrics.velocity import VelocityCalculator
from src.signals.generator import SignalGenerator
from src.reporters.email import EmailReporter

# Setup logging
def setup_logging(log_level: str = 'INFO'):
    """
    @brief Configure logging for the application
    @param log_level Logging level (DEBUG, INFO, WARNING, ERROR)
    """
    Path("logs").mkdir(exist_ok=True)

    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('logs/pipeline.log'),
            logging.StreamHandler(sys.stdout)
        ]
    )

logger = logging.getLogger(__name__)


def load_config(config_path: str = "config/config.yaml") -> dict:
    """
    @brief Load configuration from YAML file
    @param config_path Path to configuration file
    @return Configuration dictionary
    @throws FileNotFoundError if config file doesn't exist
    """
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
            logger.info(f"Configuration loaded from {config_path}")
            return config
    except FileNotFoundError:
        logger.error(f"Configuration file not found: {config_path}")
        logger.info("Please copy config/config.example.yaml to config/config.yaml and fill in your settings")
        raise
    except yaml.YAMLError as e:
        logger.error(f"Error parsing config file: {e}")
        raise


def run_pipeline(config: dict, skip_email: bool = False):
    """
    @brief Execute the full data collection and analysis pipeline
    @param config Configuration dictionary
    @param skip_email Whether to skip sending email report
    @return List of generated signals
    """
    logger.info("=" * 60)
    logger.info(f"Starting pipeline run at {datetime.now()}")
    logger.info("=" * 60)

    # Initialize database
    db_path = config['database']['path']
    db = Database(db_path)
    db.initialize()
    logger.info(f"Database initialized at {db_path}")

    # ========== Step 1: Collect Data ==========
    logger.info("Step 1: Collecting data from sources...")

    # ApeWisdom (social mentions)
    mentions = []
    try:
        ape = ApeWisdomCollector()
        mentions = ape.collect(top_n=config['collection']['apewisdom']['top_n'])
        if mentions:
            db.insert_mentions(mentions)
            logger.info(f"  [OK] ApeWisdom: {len(mentions)} tickers collected")
        else:
            logger.warning("  [WARN] ApeWisdom: No data collected")
        ape.close()
    except Exception as e:
        logger.error(f"  [ERROR] ApeWisdom failed: {e}")

    # OpenInsider (insider trades)
    trades = []
    try:
        insider = OpenInsiderCollector()
        trades = insider.collect_cluster_buys()
        trades += insider.collect_ceo_cfo_buys(
            min_value=config['collection']['openinsider']['min_value']
        )
        if trades:
            db.insert_insiders(trades)
            logger.info(f"  [OK] OpenInsider: {len(trades)} trades collected")
        else:
            logger.warning("  [WARN] OpenInsider: No trades collected")
        insider.close()
    except Exception as e:
        logger.error(f"  [ERROR] OpenInsider failed: {e}")

    # Finnhub (prices + sentiment)
    prices = []
    try:
        finnhub_key = config['api_keys'].get('finnhub')
        if not finnhub_key or finnhub_key == 'YOUR_FINNHUB_KEY':
            logger.warning("  [WARN] Finnhub: API key not configured, skipping")
        else:
            finnhub = FinnhubCollector(api_key=finnhub_key)

            # Get tickers we're tracking
            tracked_tickers = db.get_tracked_tickers(days=7)
            logger.info(f"  Fetching data for {len(tracked_tickers)} tracked tickers")

            # Collect combined price and sentiment data
            prices = finnhub.combine_price_and_sentiment(tracked_tickers)
            if prices:
                db.insert_prices(prices)
                logger.info(f"  [OK] Finnhub: {len(prices)} ticker data points collected")
            else:
                logger.warning("  [WARN] Finnhub: No data collected")
    except Exception as e:
        logger.error(f"  [ERROR] Finnhub failed: {e}")

    # ========== Step 2: Calculate Velocity Metrics ==========
    logger.info("Step 2: Calculating velocity metrics...")

    velocity_data = {}
    try:
        calc = VelocityCalculator(db)
        velocity_data = calc.calculate_all_velocities()
        if velocity_data:
            db.insert_velocity(velocity_data)
            logger.info(f"  [OK] Calculated velocity for {len(velocity_data)} tickers")
        else:
            logger.warning("  [WARN] No velocity data calculated")
    except Exception as e:
        logger.error(f"  [ERROR] Velocity calculation failed: {e}")

    # ========== Step 3: Generate Signals ==========
    logger.info("Step 3: Generating signals...")

    signals = []
    try:
        gen = SignalGenerator(thresholds=config.get('thresholds', {}))
        signals = gen.generate_signals(
            velocity_data=velocity_data,
            insider_data=db.get_recent_insiders(days=14),
            price_data=db.get_latest_prices()
        )

        # Filter by minimum conviction
        min_conviction = config.get('thresholds', {}).get('minimum_conviction', 40)
        signals = gen.filter_by_conviction(signals, min_conviction=min_conviction)

        if signals:
            db.insert_signals(signals)
            logger.info(f"  [OK] Generated {len(signals)} signals above {min_conviction} conviction")
        else:
            logger.info("  [INFO] No signals met conviction threshold")
    except Exception as e:
        logger.error(f"  [ERROR] Signal generation failed: {e}")

    # ========== Step 4: Generate and Send Report ==========
    logger.info("Step 4: Generating report...")

    if skip_email:
        logger.info("  [INFO] Email sending skipped (--skip-email flag)")
    elif not config.get('email', {}).get('enabled', False):
        logger.info("  [INFO] Email disabled in config")
    elif not signals:
        logger.info("  [INFO] No signals to report")
    else:
        try:
            reporter = EmailReporter(config['email'])
            report = reporter.generate_report(
                signals=signals[:config['report']['max_signals']],
                velocity_data=velocity_data,
                include_charts=config['report'].get('include_charts', False),
                watchlist_size=config['report'].get('watchlist_size', 20)
            )

            if reporter.send(report):
                logger.info("  [OK] Email report sent successfully")
            else:
                logger.error("  [ERROR] Failed to send email report")
        except Exception as e:
            logger.error(f"  [ERROR] Report generation/sending failed: {e}")

    # ========== Step 5: Output Summary ==========
    logger.info("=" * 60)
    logger.info("Pipeline complete. Summary:")
    logger.info(f"  - Mentions collected: {len(mentions)}")
    logger.info(f"  - Insider trades collected: {len(trades)}")
    logger.info(f"  - Price data points: {len(prices)}")
    logger.info(f"  - Velocity calculations: {len(velocity_data)}")
    logger.info(f"  - Signals generated: {len(signals)}")

    if signals:
        logger.info(f"  - Top signal: {signals[0].ticker} (conviction: {signals[0].conviction_score:.0f})")
        logger.info("  - Top 5 signals:")
        for s in signals[:5]:
            logger.info(f"    • {s.ticker}: {s.conviction_score:.0f} - {s.notes}")

    logger.info("=" * 60)

    db.close()
    return signals


def main():
    """
    @brief Main entry point for the application
    """
    parser = argparse.ArgumentParser(
        description='Sentiment Velocity Tracker - Trading Signal Pipeline',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        '--config',
        default='config/config.yaml',
        help='Path to configuration file (default: config/config.yaml)'
    )
    parser.add_argument(
        '--log-level',
        default='INFO',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        help='Logging level (default: INFO)'
    )
    parser.add_argument(
        '--skip-email',
        action='store_true',
        help='Skip sending email report'
    )
    parser.add_argument(
        '--init-db',
        action='store_true',
        help='Only initialize database and exit'
    )

    args = parser.parse_args()

    # Setup logging
    setup_logging(args.log_level)

    # Create necessary directories
    Path("logs").mkdir(exist_ok=True)
    Path("data").mkdir(exist_ok=True)

    try:
        # Load configuration
        config = load_config(args.config)

        # Initialize database only
        if args.init_db:
            logger.info("Initializing database...")
            db = Database(config['database']['path'])
            db.initialize()
            db.close()
            logger.info("Database initialized successfully")
            sys.exit(0)

        # Run full pipeline
        signals = run_pipeline(config, skip_email=args.skip_email)
        sys.exit(0)

    except FileNotFoundError as e:
        logger.error(f"Configuration error: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        logger.info("Pipeline interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.exception(f"Pipeline failed with error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
