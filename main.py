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
from src.metrics.technical import TechnicalAnalyzer
from src.signals.generator import SignalGenerator
from src.reporters.email import EmailReporter
from src.reporters.dashboard import DashboardGenerator
from src.trading.paper_trading import PaperTradingManager

# Setup logging first (before other imports that may need it)
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


# NEW FREE DATA SOURCE COLLECTORS (import after logger is defined)
try:
    from src.collectors.alphavantage import AlphaVantageCollector
    ALPHAVANTAGE_AVAILABLE = True
except ImportError:
    ALPHAVANTAGE_AVAILABLE = False

try:
    from src.collectors.yfinance_collector import YFinanceCollector
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False

try:
    from src.collectors.vader_sentiment import VaderSentimentAnalyzer
    VADER_AVAILABLE = True
except ImportError:
    VADER_AVAILABLE = False

try:
    from src.collectors.reddit_collector import RedditCollector
    REDDIT_AVAILABLE = True
except ImportError:
    REDDIT_AVAILABLE = False

try:
    from src.collectors.fred import FREDCollector
    FRED_AVAILABLE = True
except ImportError:
    FRED_AVAILABLE = False

try:
    from src.collectors.congress import CongressTradesCollector
    CONGRESS_AVAILABLE = True
except ImportError:
    CONGRESS_AVAILABLE = False


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

    # Initialize paper trading manager
    paper_trading = PaperTradingManager(db_path, config)
    if paper_trading.enabled:
        logger.info("Paper trading system enabled")
        # Backfill on first run (idempotent - safe to run multiple times)
        paper_trading.backfill_from_signals(days=config.get('paper_trading', {}).get('backfill_days', 30))

    # Initialize optional data collection variables (Phase 3)
    macro_indicators = {}
    market_assessment = {}
    congress_trades = []

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

    # ========== NEW: Collect Free Data Sources ==========
    logger.info("Step 1b: Collecting FREE data sources...")

    # Get tracked tickers for free data collection
    tracked_tickers = db.get_tracked_tickers(days=7)
    top_tickers = list(tracked_tickers)[:20]  # Top 20 to save API calls

    # Alpha Vantage sentiment (100 calls/day - FREE!)
    alpha_sentiment = {}
    if ALPHAVANTAGE_AVAILABLE and config.get('collection', {}).get('alphavantage', {}).get('enabled', False):
        try:
            alpha_key = config['api_keys'].get('alphavantage')
            if alpha_key and alpha_key != 'YOUR_ALPHAVANTAGE_KEY':
                alpha = AlphaVantageCollector(api_key=alpha_key)
                sentiments = alpha.collect_news_sentiment(
                    top_tickers,
                    limit_per_ticker=config.get('collection', {}).get('alphavantage', {}).get('articles_per_ticker', 50)
                )
                alpha_sentiment = {s['ticker']: s for s in sentiments}
                logger.info(f"  [OK] Alpha Vantage: {len(sentiments)} sentiment analyses")
            else:
                logger.info("  [SKIP] Alpha Vantage: API key not configured")
        except Exception as e:
            logger.error(f"  [ERROR] Alpha Vantage failed: {e}")

    # YFinance data (unlimited - FREE!)
    yfinance_data = {}
    if YFINANCE_AVAILABLE and config.get('collection', {}).get('yfinance', {}).get('enabled', True):
        try:
            yf_collector = YFinanceCollector()
            yf_info = yf_collector.collect_stock_info(tracked_tickers)
            yfinance_data = {d['ticker']: d for d in yf_info}
            logger.info(f"  [OK] YFinance: {len(yf_info)} stock info records")
        except Exception as e:
            logger.error(f"  [ERROR] YFinance failed: {e}")

    # VADER sentiment (local, no API - FREE!)
    vader_sentiment = {}
    if VADER_AVAILABLE and config.get('collection', {}).get('vader_sentiment', {}).get('enabled', True):
        try:
            vader = VaderSentimentAnalyzer()
            for ticker in top_tickers[:10]:  # Limit scraping to top 10 to avoid being blocked
                company_name = yfinance_data.get(ticker, {}).get('company_name')
                sentiment = vader.analyze_ticker_sentiment(ticker, company_name)
                if sentiment.get('total_headlines', 0) > 0:
                    vader_sentiment[ticker] = sentiment
            logger.info(f"  [OK] VADER Sentiment: {len(vader_sentiment)} tickers analyzed")
        except Exception as e:
            logger.error(f"  [ERROR] VADER Sentiment failed: {e}")

    # Reddit data (FREE with API key)
    reddit_data = {}
    if REDDIT_AVAILABLE and config.get('collection', {}).get('reddit', {}).get('enabled', False):
        try:
            reddit_config = config['api_keys'].get('reddit', {})
            if reddit_config.get('client_id') and reddit_config['client_id'] != 'YOUR_REDDIT_CLIENT_ID':
                reddit = RedditCollector(
                    client_id=reddit_config['client_id'],
                    client_secret=reddit_config['client_secret'],
                    user_agent=reddit_config['user_agent']
                )
                mentions = reddit.collect_ticker_mentions(
                    hours=config.get('collection', {}).get('reddit', {}).get('lookback_hours', 24)
                )
                reddit_data = {m['ticker']: m for m in mentions}
                logger.info(f"  [OK] Reddit: {len(mentions)} ticker mentions")
            else:
                logger.info("  [SKIP] Reddit: API credentials not configured")
        except Exception as e:
            logger.error(f"  [ERROR] Reddit failed: {e}")

    # FRED Macro Indicators (100 calls/day - FREE!)
    if FRED_AVAILABLE and config.get('collection', {}).get('fred', {}).get('enabled', False):
        try:
            fred_key = config['api_keys'].get('fred')
            if fred_key and fred_key != 'YOUR_FRED_KEY':
                fred = FREDCollector(api_key=fred_key, config=config)
                indicators = fred.collect_all_indicators()
                if indicators:
                    db.insert_macro_indicators(indicators)
                    macro_indicators = indicators
                    logger.info(f"  [OK] FRED: {len(indicators)} macro indicators")

                    # Assess market conditions
                    assessment = fred.assess_market_conditions(indicators)
                    if assessment:
                        db.insert_market_assessment(assessment)
                        market_assessment = assessment
                        logger.info(f"  [OK] FRED: Market risk level {assessment.get('risk_level')}")
            else:
                logger.info("  [SKIP] FRED: API key not configured")
        except Exception as e:
            logger.error(f"  [ERROR] FRED failed: {e}")

    # Congress Stock Trades (100% FREE - no API key needed!)
    if CONGRESS_AVAILABLE and config.get('collection', {}).get('congress', {}).get('enabled', False):
        try:
            congress = CongressTradesCollector(config)
            trades = congress.collect_all_trades()
            if trades:
                db.insert_congress_trades(trades)
                congress_trades = trades
                logger.info(f"  [OK] Congress Trades: {len(trades)} trades")
            else:
                logger.info("  [INFO] Congress Trades: No recent trades")
        except Exception as e:
            logger.error(f"  [ERROR] Congress Trades failed: {e}")

    # ========== Update Paper Trading Positions ==========
    if paper_trading.enabled:
        logger.info("Updating paper trading positions with current prices...")
        try:
            # Get latest prices for all open positions
            current_prices = db.get_latest_prices()
            paper_trading.update_positions(current_prices, datetime.now())
            logger.info(f"  [OK] Paper trading positions updated")
        except Exception as e:
            logger.error(f"  [ERROR] Paper trading update failed: {e}")

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

    # ========== NEW: Technical Analysis (Zero API calls!) ==========
    logger.info("Step 2b: Running technical analysis...")

    technical_data = {}
    if config.get('collection', {}).get('technical_analysis', {}).get('enabled', True):
        try:
            tech_analyzer = TechnicalAnalyzer(db)
            for ticker in velocity_data.keys():
                tech_analysis = tech_analyzer.analyze_ticker(ticker)
                if tech_analysis:
                    tech_score = tech_analyzer.get_technical_score(tech_analysis)
                    tech_analysis['technical_score'] = tech_score
                    technical_data[ticker] = tech_analysis
            logger.info(f"  [OK] Technical analysis for {len(technical_data)} tickers")
        except Exception as e:
            logger.error(f"  [ERROR] Technical analysis failed: {e}")

    # ========== Step 3: Generate Signals with FREE Data ==========
    logger.info("Step 3: Generating signals with FREE data sources...")

    # Merge sentiment data (prefer Alpha Vantage, fallback to VADER)
    sentiment_data = {}
    for ticker in velocity_data.keys():
        if ticker in alpha_sentiment:
            sentiment_data[ticker] = alpha_sentiment[ticker]
        elif ticker in vader_sentiment:
            sentiment_data[ticker] = vader_sentiment[ticker]

    signals = []
    try:
        gen = SignalGenerator(thresholds=config.get('thresholds', {}))
        signals = gen.generate_signals(
            velocity_data=velocity_data,
            insider_data=db.get_recent_insiders(days=14),
            price_data=db.get_latest_prices(),
            technical_data=technical_data,      # NEW!
            sentiment_data=sentiment_data,      # NEW!
            reddit_data=reddit_data             # NEW!
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

    # ========== Create Paper Trades from Signals ==========
    if paper_trading.enabled and signals:
        logger.info("Creating paper trades from new signals...")
        try:
            created_count = 0
            for signal in signals:
                # Check if signal meets paper trading conviction threshold
                if signal.conviction_score >= paper_trading.min_conviction:
                    # Get current price for this ticker
                    current_price = db.get_latest_prices().get(signal.ticker)
                    if current_price:
                        trade_id = paper_trading.create_paper_trade(
                            ticker=signal.ticker,
                            entry_price=current_price,
                            conviction=int(signal.conviction_score),
                            signal_types=signal.triggers,
                            entry_date=datetime.now()
                        )
                        if trade_id:
                            created_count += 1
            logger.info(f"  [OK] Created {created_count} new paper trades")
        except Exception as e:
            logger.error(f"  [ERROR] Paper trade creation failed: {e}")

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

    # ========== NEW: Generate HTML Dashboard ==========
    logger.info("Step 4b: Generating HTML dashboard...")
    try:
        # Get paper trading stats for dashboard
        paper_trading_stats = {}
        if paper_trading.enabled:
            paper_trading_stats = paper_trading.get_performance_summary()

        dashboard = DashboardGenerator(output_dir="reports")
        dashboard_path = dashboard.generate(
            signals=signals,
            velocity_data=velocity_data,
            technical_data=technical_data,
            sentiment_data=sentiment_data,
            reddit_data=reddit_data,
            paper_trading_stats=paper_trading_stats,
            macro_indicators=macro_indicators,
            market_assessment=market_assessment,
            congress_trades=congress_trades
        )
        logger.info(f"  [OK] Dashboard saved to: {dashboard_path}")
        logger.info(f"  [TIP] Open {dashboard_path} in your browser to view results!")
    except Exception as e:
        logger.error(f"  [ERROR] Dashboard generation failed: {e}")

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
