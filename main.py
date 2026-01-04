#!/usr/bin/env python3
"""
@file main.py
@brief Sentiment Velocity Tracker - Main Pipeline Orchestrator
@details Daily pipeline for collecting social data, calculating velocity, and generating trading signals
@usage Run daily via cron: 0 6 * * * cd /path/to/sentiment_velocity && python main.py
"""

import logging
import sys
import os
from datetime import datetime
from pathlib import Path
import yaml
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed

from src.collectors.apewisdom import ApeWisdomCollector
from src.collectors.openinsider import OpenInsiderCollector
from src.collectors.finnhub import FinnhubCollector
from src.database.models import Database
from src.metrics.velocity import VelocityCalculator
from src.metrics.technical import TechnicalAnalyzer
from src.signals.generator import SignalGenerator
from src.reporters.email import EmailReporter
from src.reporters.dashboard_v2 import ModernDashboardGenerator as DashboardGenerator
from src.trading.paper_trading import PaperTradingManager

# Setup logging first (before other imports that may need it)
def setup_logging(log_level: str = 'INFO', project_root: str = '.'):
    """
    @brief Configure logging for the application
    @param log_level Logging level (DEBUG, INFO, WARNING, ERROR)
    @param project_root Project root directory for logs
    """
    logs_dir = os.path.join(project_root, "logs")
    Path(logs_dir).mkdir(exist_ok=True)

    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(os.path.join(logs_dir, 'pipeline.log')),
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
    REDDIT_AVAILABLE = False

try:
    from src.collectors.fred import FREDCollector
    FRED_AVAILABLE = True
except ImportError:
    FRED_AVAILABLE = False

# Congress trades collector removed - no longer supported
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


# Parallel collection helper functions
def collect_apewisdom(config):
    """Collect ApeWisdom data in parallel"""
    try:
        ape = ApeWisdomCollector()
        mentions = ape.collect(top_n=config['collection']['apewisdom']['top_n'])
        ape.close()
        return ('apewisdom', mentions, None)
    except Exception as e:
        return ('apewisdom', [], str(e))


def collect_openinsider(config):
    """Collect OpenInsider data in parallel"""
    try:
        insider = OpenInsiderCollector()
        trades = insider.collect_cluster_buys()
        trades += insider.collect_ceo_cfo_buys(
            min_value=config['collection']['openinsider']['min_value']
        )
        insider.close()
        return ('openinsider', trades, None)
    except Exception as e:
        return ('openinsider', [], str(e))


def collect_alphavantage(config, top_tickers):
    """Collect Alpha Vantage sentiment in parallel"""
    if not ALPHAVANTAGE_AVAILABLE or not config.get('collection', {}).get('alphavantage', {}).get('enabled', False):
        return ('alphavantage', {}, None)
    
    try:
        alpha_key = config['api_keys'].get('alphavantage')
        if not alpha_key or alpha_key == 'YOUR_ALPHAVANTAGE_KEY':
            return ('alphavantage', {}, None)
        
        alpha = AlphaVantageCollector(api_key=alpha_key)
        sentiments = alpha.collect_news_sentiment(
            top_tickers,
            limit_per_ticker=config.get('collection', {}).get('alphavantage', {}).get('articles_per_ticker', 50)
        )
        alpha_sentiment = {s['ticker']: s for s in sentiments}
        return ('alphavantage', alpha_sentiment, None)
    except Exception as e:
        return ('alphavantage', {}, str(e))


def collect_yfinance(tracked_tickers):
    """Collect YFinance data in parallel"""
    if not YFINANCE_AVAILABLE:
        return ('yfinance', {}, None)
    
    try:
        yf_collector = YFinanceCollector()
        yf_info = yf_collector.collect_stock_info(tracked_tickers)
        yfinance_data = {d['ticker']: d for d in yf_info}
        return ('yfinance', yfinance_data, None)
    except Exception as e:
        return ('yfinance', {}, str(e))


def collect_vader(top_tickers, yfinance_data, config):
    """Collect VADER sentiment in parallel"""
    if not VADER_AVAILABLE or not config.get('collection', {}).get('vader_sentiment', {}).get('enabled', True):
        return ('vader', {}, None)
    
    try:
        vader = VaderSentimentAnalyzer()
        vader_sentiment = {}
        for ticker in top_tickers[:10]:
            company_name = yfinance_data.get(ticker, {}).get('company_name')
            sentiment = vader.analyze_ticker_sentiment(ticker, company_name)
            if sentiment.get('total_headlines', 0) > 0:
                vader_sentiment[ticker] = sentiment
        return ('vader', vader_sentiment, None)
    except Exception as e:
        return ('vader', {}, str(e))


def collect_fred(config):
    """Collect FRED macro indicators in parallel"""
    if not FRED_AVAILABLE or not config.get('collection', {}).get('fred', {}).get('enabled', False):
        return ('fred', {}, {}, None)
    
    try:
        fred_key = config['api_keys'].get('fred')
        if not fred_key or fred_key == 'YOUR_FRED_KEY':
            return ('fred', {}, {}, None)
        
        fred = FREDCollector(api_key=fred_key)
        indicators = fred.collect_all_indicators()
        assessment = {}
        if indicators:
            assessment = fred.assess_market_conditions(indicators)
        return ('fred', indicators, assessment, None)
    except Exception as e:
        return ('fred', {}, {}, str(e))


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

    # ========== Step 1: Collect Data IN PARALLEL ==========
    logger.info("Step 1: Collecting data from sources (PARALLEL MODE)...")
    
    # Get tracked tickers first (needed by multiple collectors)
    tracked_tickers = db.get_tracked_tickers(days=7)
    top_tickers = list(tracked_tickers)[:20]
    
    # Run initial collectors in parallel
    mentions = []
    trades = []
    prices = []
    alpha_sentiment = {}
    yfinance_data = {}
    vader_sentiment = {}
    macro_indicators = {}
    market_assessment = {}
    
    with ThreadPoolExecutor(max_workers=4) as executor:
        # Submit initial collection tasks
        future_ape = executor.submit(collect_apewisdom, config)
        future_insider = executor.submit(collect_openinsider, config)
        
        # Wait for results
        for future in as_completed([future_ape, future_insider]):
            collector_name, data, error = future.result()
            
            if collector_name == 'apewisdom':
                mentions = data
                if error:
                    logger.error(f"  [ERROR] ApeWisdom failed: {error}")
                elif mentions:
                    db.insert_mentions(mentions)
                    logger.info(f"  [OK] ApeWisdom: {len(mentions)} tickers collected")
                else:
                    logger.warning("  [WARN] ApeWisdom: No data collected")
            
            elif collector_name == 'openinsider':
                trades = data
                if error:
                    logger.error(f"  [ERROR] OpenInsider failed: {error}")
                elif trades:
                    db.insert_insiders(trades)
                    logger.info(f"  [OK] OpenInsider: {len(trades)} trades collected")
                else:
                    logger.warning("  [WARN] OpenInsider: No trades collected")
    
    # Finnhub (still sequential as it needs tracked_tickers immediately)
    try:
        finnhub_key = config['api_keys'].get('finnhub')
        if finnhub_key and finnhub_key != 'YOUR_FINNHUB_KEY':
            logger.info(f"  Fetching data for {len(tracked_tickers)} tracked tickers")
            finnhub = FinnhubCollector(api_key=finnhub_key)
            prices = finnhub.combine_price_and_sentiment(tracked_tickers)
            if prices:
                db.insert_prices(prices)
                logger.info(f"  [OK] Finnhub: {len(prices)} ticker data points collected")
        else:
            logger.warning("  [WARN] Finnhub: API key not configured, skipping")
    except Exception as e:
        logger.error(f"  [ERROR] Finnhub failed: {e}")
    
    # ========== Step 1b: Collect FREE data sources IN PARALLEL ==========
    logger.info("Step 1b: Collecting FREE data sources (PARALLEL MODE)...")
    
    with ThreadPoolExecutor(max_workers=4) as executor:
        # Submit all free data collectors in parallel
        future_yf = executor.submit(collect_yfinance, tracked_tickers)
        future_fred = executor.submit(collect_fred, config)
        future_alpha = executor.submit(collect_alphavantage, config, top_tickers)
        
        # Collect YFinance first as VADER depends on it
        collector_name, data, error = future_yf.result()
        yfinance_data = data
        if error:
            logger.error(f"  [ERROR] YFinance failed: {error}")
        elif yfinance_data:
            logger.info(f"  [OK] YFinance: {len(yfinance_data)} stock info records")
        
        # Now submit VADER with yfinance_data
        future_vader = executor.submit(collect_vader, top_tickers, yfinance_data, config)
        
        # Collect remaining results
        for future in as_completed([future_alpha, future_fred, future_vader]):
            result = future.result()
            
            if result[0] == 'alphavantage':
                _, alpha_sentiment, error = result
                if error:
                    logger.error(f"  [ERROR] Alpha Vantage failed: {error}")
                elif alpha_sentiment:
                    logger.info(f"  [OK] Alpha Vantage: {len(alpha_sentiment)} sentiment analyses")
                else:
                    logger.info("  [SKIP] Alpha Vantage: API key not configured")
            
            elif result[0] == 'vader':
                _, vader_sentiment, error = result
                if error:
                    logger.error(f"  [ERROR] VADER Sentiment failed: {error}")
                else:
                    logger.info(f"  [OK] VADER Sentiment: {len(vader_sentiment)} tickers analyzed")
            
            elif result[0] == 'fred':
                _, macro_indicators, market_assessment, error = result
                if error:
                    logger.error(f"  [ERROR] FRED failed: {error}")
                elif macro_indicators:
                    db.insert_macro_indicators(macro_indicators)
                    logger.info(f"  [OK] FRED: {len(macro_indicators)} macro indicators")
                    if market_assessment:
                        db.insert_market_assessment(market_assessment)
                        logger.info(f"  [OK] FRED: Market risk level {market_assessment.get('risk_level')}")
                else:
                    logger.info("  [SKIP] FRED: API key not configured")
    
    
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
    all_signals = []
    try:
        gen = SignalGenerator(thresholds=config.get('thresholds', {}))
        all_signals = gen.generate_signals(
            velocity_data=velocity_data,
            insider_data=db.get_recent_insiders(days=14),
            price_data=db.get_latest_prices(),
            technical_data=technical_data,      # NEW!
            sentiment_data=sentiment_data,      # NEW!
        )

        # Insert ALL signals into database for historical analysis
        if all_signals:
            db.insert_signals(all_signals)
            logger.info(f"  [OK] Inserted {len(all_signals)} signals into database")

        # Filter by minimum conviction for reporting/trading
        min_conviction = config.get('thresholds', {}).get('minimum_conviction', 40)
        signals = gen.filter_by_conviction(all_signals, min_conviction=min_conviction)

        if signals:
            logger.info(f"  [OK] {len(signals)} signals meet {min_conviction} conviction threshold")
        else:
            logger.info("  [INFO] No signals met conviction threshold for trading")
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
                    price_data = db.get_latest_prices().get(signal.ticker)
                    if price_data and 'price' in price_data:
                        trade_id = paper_trading.create_paper_trade(
                            ticker=signal.ticker,
                            entry_price=price_data['price'],
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

        # Determine project root for dashboard
        import os
        project_root = os.path.dirname(os.path.abspath(__file__))

        dashboard = DashboardGenerator(output_dir="reports", project_root=project_root)
        dashboard_path = dashboard.generate(
            signals=signals,
            velocity_data=velocity_data,
            technical_data=technical_data,
            sentiment_data=sentiment_data,
            paper_trading_stats=paper_trading_stats,
            macro_indicators=macro_indicators,
            market_assessment=market_assessment
        )
        logger.info(f"  [OK] Dashboard saved to: {dashboard_path}")
        logger.info(f"  [TIP] Open {dashboard_path} in your browser to view results!")
    except Exception as e:
        import traceback
        logger.error(f"  [ERROR] Dashboard generation failed: {e}")
        logger.error(f"  [TRACEBACK] {traceback.format_exc()}")

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


def get_project_root():
    """Get project root folder - prompt if running as exe and not set"""
    # If running as exe, prompt for project root
    if getattr(sys, 'frozen', False):
        # Try to load from settings file in AppData
        if sys.platform == 'win32':
            appdata = os.environ.get('APPDATA', os.path.expanduser('~'))
            settings_dir = os.path.join(appdata, 'StockTrader')
        else:
            settings_dir = os.path.expanduser('~/.stocktrader')

        settings_file = os.path.join(settings_dir, 'settings.yaml')

        if os.path.exists(settings_file):
            try:
                with open(settings_file, 'r') as f:
                    settings = yaml.safe_load(f) or {}
                    project_root = settings.get('project_root')
                    if project_root and os.path.isdir(project_root):
                        return project_root
            except:
                pass

        # Need to prompt - use tkinter dialog
        try:
            import tkinter as tk
            from tkinter import filedialog, messagebox

            root = tk.Tk()
            root.withdraw()

            messagebox.showinfo(
                "Select Stock Trader Folder",
                "Please select your Stock-Trader folder containing:\n"
                "• config/\n• data/\n• logs/\n• src/\n• utils/"
            )

            folder = filedialog.askdirectory(
                title="Select Stock-Trader Folder",
                mustexist=True
            )

            root.destroy()

            if folder:
                return folder
        except:
            pass

        print("ERROR: Could not determine project root folder")
        print("Please run with --project-root <path> argument")
        sys.exit(1)
    else:
        # Running as script - use script directory
        return os.path.dirname(os.path.abspath(__file__))


def main():
    """
    @brief Main entry point for the application
    """
    parser = argparse.ArgumentParser(
        description='Sentiment Velocity Tracker - Trading Signal Pipeline',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        '--project-root',
        help='Path to Stock-Trader project root folder'
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

    # Get project root (from args or auto-detect)
    project_root = args.project_root if args.project_root else get_project_root()

    # Change working directory to project root
    os.chdir(project_root)

    # Setup logging with project root
    setup_logging(args.log_level, project_root)

    # Create necessary directories
    Path(os.path.join(project_root, "logs")).mkdir(exist_ok=True)
    Path(os.path.join(project_root, "data")).mkdir(exist_ok=True)

    logger.info("=" * 60)
    logger.info("Sentiment Velocity Tracker - Pipeline Starting")
    logger.info(f"Project Root: {project_root}")
    logger.info(f"Timestamp: {datetime.now().isoformat()}")
    logger.info("=" * 60)

    try:
        # Build config path relative to project root
        config_path = args.config if os.path.isabs(args.config) else os.path.join(project_root, args.config)

        # Load configuration
        config = load_config(config_path)

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
