"""
@file test_dashboard.py
@brief Test suite for enhanced dashboard generation
"""

import pytest
from datetime import datetime, timedelta
from pathlib import Path
from src.reporters.dashboard_v2 import ModernDashboardGenerator
from src.database.models import Database


@pytest.fixture
def test_db(tmp_path):
    """Create a temporary test database with sample data"""
    db_path = tmp_path / "test_dashboard.db"
    db = Database(str(db_path))
    db.initialize()

    # Add sample data
    conn = db.connect()
    cursor = conn.cursor()

    # Velocity data
    for i in range(10):
        cursor.execute("""
            INSERT INTO velocity
            (ticker, mention_velocity_24h, price_velocity_24h, sentiment_velocity, composite_score, calculated_at)
            VALUES (?, ?, ?, ?, ?, datetime('now', '-' || ? || ' hours'))
        """, (f'VEL{i}', 10.0 + i, 5.0 + i, 0.5, 50.0 + i*5, i))

    # Insider trades
    for i in range(10):
        trade_type = 'Purchase' if i % 2 == 0 else 'Sale'
        cursor.execute("""
            INSERT INTO insider_trades
            (ticker, insider_name, trade_type, value, trade_date, collected_at)
            VALUES (?, ?, ?, ?, date('now', '-' || ? || ' days'), datetime('now'))
        """, (f'INS{i}', f'Insider {i}', trade_type, 100000 + i*10000, i))

    # Social mentions
    for i in range(10):
        cursor.execute("""
            INSERT INTO social_mentions
            (ticker, mention_count, upvotes, viral_score, collected_at)
            VALUES (?, ?, ?, ?, datetime('now', '-' || ? || ' hours'))
        """, (f'SOC{i}', 100 + i*10, 50 + i*5, 75.0 + i*2, i))

    # Signals
    signal_types = ['velocity_spike', 'insider_buy', 'technical_breakout']
    for i in range(15):
        signal_type = signal_types[i % len(signal_types)]
        cursor.execute("""
            INSERT INTO signals
            (ticker, signal_type, conviction_score, notes, created_at)
            VALUES (?, ?, ?, ?, datetime('now', '-' || ? || ' days'))
        """, (f'SIG{i}', signal_type, 60.0 + i, 'Test signal', i % 90))

        # Add paper trades for some signals
        if i % 3 == 0:
            signal_id = cursor.lastrowid
            pnl = (i % 2) * 200 - 100
            cursor.execute("""
                INSERT INTO paper_trades
                (signal_id, ticker, entry_price, exit_price, shares, pnl, entry_date, exit_date)
                VALUES (?, ?, ?, ?, ?, ?, datetime('now', '-' || ? || ' days'), datetime('now', '-' || ? || ' days'))
            """, (signal_id, f'SIG{i}', 100.0, 100.0 + pnl/10, 10, pnl, i % 90, (i % 90) - 1))

    # Macro indicators
    for i in range(30):
        cursor.execute("""
            INSERT INTO macro_indicators
            (indicator_name, value, collected_at)
            VALUES (?, ?, datetime('now', '-' || ? || ' days'))
        """, ('VIX', 20.0 + i*0.5, i))

        cursor.execute("""
            INSERT INTO macro_indicators
            (indicator_name, value, collected_at)
            VALUES (?, ?, datetime('now', '-' || ? || ' days'))
        """, ('TREASURY_10Y', 4.0 + i*0.01, i))

    conn.commit()
    yield db
    db.close()


@pytest.fixture
def dashboard_generator(tmp_path):
    """Create dashboard generator with temp output directory"""
    return ModernDashboardGenerator(output_dir=str(tmp_path))


@pytest.fixture
def sample_signals():
    """Create sample signal objects for testing"""
    class MockSignal:
        def __init__(self, ticker, signal_type, conviction):
            self.ticker = ticker
            self.signal_type = signal_type
            self.conviction_score = conviction
            self.created_at = datetime.now()
            self.notes = "Test signal"
            self.triggers = ["test_trigger"]

    return [
        MockSignal("AAPL", "velocity_spike", 75.0),
        MockSignal("TSLA", "insider_buy", 85.0),
        MockSignal("NVDA", "technical_breakout", 65.0)
    ]


@pytest.fixture
def sample_velocity_data():
    """Create sample velocity data"""
    return {
        "AAPL": {
            "mention_velocity_24h": 15.0,
            "price_velocity_24h": 5.0,
            "sentiment_velocity": 0.8,
            "composite_score": 75.0
        },
        "TSLA": {
            "mention_velocity_24h": 20.0,
            "price_velocity_24h": 8.0,
            "sentiment_velocity": 0.6,
            "composite_score": 85.0
        }
    }


@pytest.fixture
def sample_technical_data():
    """Create sample technical analysis data"""
    return {
        "AAPL": {
            "rsi_14": 65.0,
            "macd": 1.5,
            "macd_signal": 1.2,
            "macd_hist": 0.3,
            "bb_upper": 150.0,
            "bb_middle": 145.0,
            "bb_lower": 140.0
        },
        "TSLA": {
            "rsi_14": 45.0,
            "macd": -0.5,
            "macd_signal": -0.3,
            "macd_hist": -0.2,
            "bb_upper": 200.0,
            "bb_middle": 190.0,
            "bb_lower": 180.0
        }
    }


@pytest.fixture
def sample_sentiment_data():
    """Create sample sentiment data"""
    return {
        "AAPL": {
            "avg_sentiment": 0.75,
            "sentiment_count": 100,
            "positive_ratio": 0.8
        },
        "TSLA": {
            "avg_sentiment": 0.55,
            "sentiment_count": 150,
            "positive_ratio": 0.6
        }
    }


class TestDashboardGeneration:
    """Test basic dashboard generation"""

    def test_generate_basic_dashboard(self, dashboard_generator, sample_signals,
                                      sample_velocity_data, tmp_path):
        """Test generating dashboard with basic data"""
        output_path = dashboard_generator.generate(
            signals=sample_signals,
            velocity_data=sample_velocity_data
        )

        assert Path(output_path).exists()
        assert Path(output_path).suffix == '.html'

        # Read and verify HTML content
        with open(output_path, 'r') as f:
            html = f.read()
            assert 'Trading Signals' in html
            assert 'AAPL' in html
            assert 'TSLA' in html
            assert 'NVDA' in html

    def test_generate_with_all_data(self, dashboard_generator, sample_signals,
                                    sample_velocity_data, sample_technical_data,
                                    sample_sentiment_data, test_db, tmp_path):
        """Test generating dashboard with all data including database"""
        paper_trading_stats = {
            'total_trades': 10,
            'win_rate': 60.0,
            'total_pnl': 1500.0,
            'avg_pnl_per_trade': 150.0
        }

        macro_indicators = {
            'vix': 18.5,
            'treasury_10y': 4.25
        }

        market_assessment = {
            'risk_level': 'MEDIUM',
            'risk_score': 50,
            'conditions': ['Moderate volatility'],
            'recommendations': ['Monitor closely']
        }

        output_path = dashboard_generator.generate(
            signals=sample_signals,
            velocity_data=sample_velocity_data,
            technical_data=sample_technical_data,
            sentiment_data=sample_sentiment_data,
            paper_trading_stats=paper_trading_stats,
            macro_indicators=macro_indicators,
            market_assessment=market_assessment,
            db=test_db
        )

        assert Path(output_path).exists()

        # Read and verify enhanced HTML content
        with open(output_path, 'r') as f:
            html = f.read()

            # Check for new sections
            assert 'Top Movers' in html
            assert 'Insider Trading Activity' in html
            assert 'Technical Analysis Deep Dive' in html
            assert 'Historical Performance' in html
            assert 'Sentiment Breakdown' in html
            assert 'Macro Trends' in html
            assert 'Social Media Insights' in html

            # Check for Chart.js inclusion
            assert 'chart.js' in html.lower()

    def test_generate_without_database(self, dashboard_generator, sample_signals,
                                       sample_velocity_data, tmp_path):
        """Test generating dashboard without database (backward compatibility)"""
        output_path = dashboard_generator.generate(
            signals=sample_signals,
            velocity_data=sample_velocity_data,
            db=None
        )

        assert Path(output_path).exists()

        # Should still work without enhanced data
        with open(output_path, 'r') as f:
            html = f.read()
            assert 'Trading Signals' in html


class TestDashboardSections:
    """Test individual dashboard sections"""

    def test_header_generation(self, dashboard_generator):
        """Test header section generation"""
        market_assessment = {
            'risk_level': 'LOW',
            'risk_score': 25,
            'conditions': ['Low volatility', 'Positive trend'],
            'recommendations': ['Consider increasing exposure']
        }

        header_html = dashboard_generator._generate_header(75, market_assessment)

        assert 'Trading Signals' in header_html
        assert '75' in header_html  # Market score
        assert 'LOW' in header_html or '🟢' in header_html

    def test_top_movers_section(self, dashboard_generator):
        """Test top movers section generation"""
        velocity_gainers = [
            {'ticker': 'TEST1', 'composite_score': 85.5, 'mention_velocity_24h': 15, 'price_velocity_24h': 5, 'sentiment_velocity': 0.8}
        ]
        insider_trades = [
            {'ticker': 'TEST2', 'trade_type': 'Purchase', 'value': 150000, 'trade_date': '2024-01-01', 'insider_name': 'John Doe'}
        ]
        social_mentions = [
            {'ticker': 'TEST3', 'mention_count': 250, 'upvotes': 100, 'viral_score': 85.0}
        ]
        sentiment_shifts = [
            {'ticker': 'TEST4', 'sentiment_change': 0.45, 'current_sentiment': 0.75}
        ]

        html = dashboard_generator._generate_top_movers_section(
            velocity_gainers, insider_trades, social_mentions, sentiment_shifts
        )

        assert 'Top Movers' in html
        assert 'TEST1' in html
        assert 'TEST2' in html
        assert 'TEST3' in html
        assert 'TEST4' in html

    def test_insider_panel(self, dashboard_generator):
        """Test insider trading panel generation"""
        insider_trades = [
            {
                'ticker': 'AAPL',
                'insider_name': 'Tim Cook',
                'trade_type': 'Purchase',
                'value': 500000,
                'trade_date': '2024-01-01'
            }
        ]
        insider_ratio = {'buy': 15, 'sell': 5}

        html = dashboard_generator._generate_insider_panel(insider_trades, insider_ratio)

        assert 'Insider Trading Activity' in html
        assert 'AAPL' in html
        assert 'Tim Cook' in html
        assert 'Purchase' in html
        assert 'insiderRatioChart' in html  # Chart.js chart

    def test_technical_deepdive(self, dashboard_generator, sample_technical_data,
                                sample_velocity_data):
        """Test technical analysis deep dive section"""
        html = dashboard_generator._generate_technical_deepdive(
            sample_technical_data, sample_velocity_data
        )

        assert 'Technical Analysis Deep Dive' in html
        assert 'RSI Distribution' in html
        assert 'MACD Signals' in html
        assert 'rsiChart' in html  # Chart.js chart

    def test_performance_section(self, dashboard_generator):
        """Test historical performance section"""
        signal_performance = [
            {
                'signal_type': 'velocity_spike',
                'signal_count': 25,
                'win_rate': 65.0,
                'avg_pnl': 125.50
            }
        ]
        equity_curve = [
            {'date': '2024-01-01', 'cumulative_pnl': 500},
            {'date': '2024-01-02', 'cumulative_pnl': 650}
        ]
        paper_trading_stats = {
            'total_trades': 50,
            'win_rate': 62.0
        }

        html = dashboard_generator._generate_performance_section(
            signal_performance, equity_curve, paper_trading_stats
        )

        assert 'Historical Performance' in html
        assert 'velocity_spike' in html
        assert 'equityChart' in html  # Chart.js chart

    def test_sentiment_breakdown(self, dashboard_generator, sample_sentiment_data):
        """Test sentiment breakdown section"""
        sentiment_shifts = [
            {
                'ticker': 'AAPL',
                'sentiment_change': 0.35,
                'current_sentiment': 0.75,
                'previous_sentiment': 0.40
            }
        ]

        html = dashboard_generator._generate_sentiment_breakdown(
            sample_sentiment_data, sentiment_shifts
        )

        assert 'Sentiment Breakdown' in html
        assert 'sentimentChart' in html  # Chart.js chart

    def test_macro_trends(self, dashboard_generator):
        """Test macro trends section"""
        vix_history = [
            {'date': '2024-01-01', 'value': 18.5},
            {'date': '2024-01-02', 'value': 19.0}
        ]
        treasury_history = [
            {'date': '2024-01-01', 'value': 4.25},
            {'date': '2024-01-02', 'value': 4.30}
        ]
        macro_indicators = {'vix': 18.5, 'treasury_10y': 4.25}
        market_assessment = {'risk_level': 'MEDIUM'}

        html = dashboard_generator._generate_macro_trends(
            vix_history, treasury_history, macro_indicators, market_assessment
        )

        assert 'Macro Trends' in html
        assert 'vixChart' in html  # Chart.js chart
        assert 'treasuryChart' in html  # Chart.js chart

    def test_social_insights(self, dashboard_generator):
        """Test social media insights section"""
        social_mentions = [
            {
                'ticker': 'AAPL',
                'mention_count': 500,
                'upvotes': 250,
                'viral_score': 85.0
            }
        ]
        emerging_tickers = [
            {'ticker': 'NVDA', 'mention_count': 125}
        ]
        top_velocity = [
            {'ticker': 'TSLA', 'composite_score': 90.0}
        ]

        html = dashboard_generator._generate_social_insights(
            social_mentions, emerging_tickers, top_velocity
        )

        assert 'Social Media Insights' in html
        assert 'AAPL' in html
        assert 'NVDA' in html


class TestDashboardEdgeCases:
    """Test edge cases and error handling"""

    def test_empty_signals(self, dashboard_generator, tmp_path):
        """Test dashboard generation with empty signals"""
        output_path = dashboard_generator.generate(
            signals=[],
            velocity_data={}
        )

        assert Path(output_path).exists()

    def test_none_optional_params(self, dashboard_generator, sample_signals,
                                  sample_velocity_data, tmp_path):
        """Test dashboard generation with None optional parameters"""
        output_path = dashboard_generator.generate(
            signals=sample_signals,
            velocity_data=sample_velocity_data,
            technical_data=None,
            sentiment_data=None,
            paper_trading_stats=None,
            macro_indicators=None,
            market_assessment=None,
            db=None
        )

        assert Path(output_path).exists()

    def test_css_styles_present(self, dashboard_generator, sample_signals,
                                sample_velocity_data, tmp_path):
        """Test that all new CSS classes are present"""
        output_path = dashboard_generator.generate(
            signals=sample_signals,
            velocity_data=sample_velocity_data
        )

        with open(output_path, 'r') as f:
            html = f.read()

            # Check for new CSS classes
            assert '.grid-4' in html
            assert '.card' in html
            assert '.movers-list' in html
            assert '.badge' in html
            assert '.chart-container' in html
            assert '.emerging-ticker' in html
