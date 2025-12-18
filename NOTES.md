# Sentiment Velocity Tracker - Project Notes

## Project Overview
A Python-based daily pipeline that identifies stocks with unusual social momentum, cross-references against insider buying activity, and generates actionable trading signals.

**Version:** 1.0.0
**Last Updated:** 2025-12-18

---

## Quick Start Guide

### Initial Setup

1. **Clone and Navigate**
   ```bash
   cd /path/to/Stock-Trader
   ```

2. **Create Virtual Environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure Application**
   ```bash
   # Copy example config
   cp config/config.example.yaml config/config.yaml

   # Edit config.yaml with your API keys and email settings
   # Required: Finnhub API key (free from https://finnhub.io/register)
   # Optional: FRED API key for macro indicators (Phase 2)
   ```

5. **Initialize Database**
   ```bash
   python main.py --init-db
   ```

6. **Test Run**
   ```bash
   python main.py --skip-email
   ```

---

## Configuration

### Required API Keys

1. **Finnhub** (Required)
   - Sign up: https://finnhub.io/register
   - Free tier: 60 requests/minute
   - Used for: Price data and news sentiment

2. **FRED** (Optional - Phase 2)
   - Sign up: https://fred.stlouisfed.org/docs/api/api_key.html
   - Used for: Macro economic indicators

### Email Configuration

For Gmail users:
1. Enable 2-factor authentication
2. Generate app password: https://myaccount.google.com/apppasswords
3. Use app password in config (not your regular password)

---

## Running the Pipeline

### Manual Execution
```bash
# Full run with email
python main.py

# Skip email notification
python main.py --skip-email

# Use custom config
python main.py --config /path/to/custom-config.yaml

# Debug mode
python main.py --log-level DEBUG
```

### Automated Execution (Cron)

**Linux/Mac:**
```bash
crontab -e

# Run daily at 6 AM ET
0 6 * * * cd /path/to/Stock-Trader && /path/to/venv/bin/python main.py >> logs/cron.log 2>&1

# Run every 4 hours
0 */4 * * * cd /path/to/Stock-Trader && /path/to/venv/bin/python main.py >> logs/cron.log 2>&1
```

**Windows Task Scheduler:**
```powershell
$action = New-ScheduledTaskAction -Execute "python" -Argument "C:\path\to\Stock-Trader\main.py"
$trigger = New-ScheduledTaskTrigger -Daily -At 6am
Register-ScheduledTask -Action $action -Trigger $trigger -TaskName "SentimentVelocityTracker"
```

---

## Testing

### Run All Tests
```bash
pytest tests/ -v
```

### Run Specific Test Files
```bash
pytest tests/test_collectors.py -v
pytest tests/test_velocity.py -v
pytest tests/test_signals.py -v
```

### Run with Coverage
```bash
pytest tests/ --cov=src --cov-report=html
```

### Skip Integration Tests
```bash
pytest tests/ -v -m "not integration"
```

---

## Architecture Overview

### Data Flow
```
ApeWisdom API → Mentions DB
OpenInsider Scraper → Insiders DB
Finnhub API → Prices/Sentiment DB
    ↓
Velocity Calculator → Velocity Metrics
    ↓
Signal Generator → Trading Signals
    ↓
Email Reporter → HTML Email Report
```

### Key Components

1. **Collectors** (`src/collectors/`)
   - `apewisdom.py`: Social media mention data
   - `openinsider.py`: Insider trading activity (web scraping)
   - `finnhub.py`: Price and sentiment data (API)

2. **Database** (`src/database/`)
   - `models.py`: SQLite schema and ORM
   - `queries.py`: Query helper functions

3. **Metrics** (`src/metrics/`)
   - `velocity.py`: Velocity calculations and composite scoring

4. **Signals** (`src/signals/`)
   - `generator.py`: Signal detection and conviction scoring

5. **Reporters** (`src/reporters/`)
   - `email.py`: HTML email generation and sending
   - `charts.py`: Matplotlib visualization (optional)

---

## Database Schema

### Tables
- **mentions**: Social media mention counts over time
- **insiders**: Insider trading transactions
- **prices**: Price and sentiment data
- **velocity**: Calculated velocity metrics
- **signals**: Generated trading signals
- **macro**: Macro economic indicators (Phase 2)

### Location
`data/sentiment.db` (SQLite)

---

## Signal Types

### Velocity Spike
- **Criteria**: 100%+ increase in 24h mentions + composite score ≥ 60
- **Conviction Boost**: +30 points

### Insider Cluster
- **Criteria**: 2+ insiders buying within 14 days, total value ≥ $100k
- **Conviction Boost**: +40 points

### Sentiment Flip
- **Criteria**: 30%+ shift in sentiment velocity
- **Conviction Boost**: +20 points

### Combined Signal
- **Criteria**: Multiple triggers + insider activity
- **Conviction Boost**: +15 points for combination

---

## Customization

### Adjusting Thresholds

Edit `config/config.yaml`:
```yaml
thresholds:
  velocity_spike:
    mention_vel_24h_min: 150  # Increase for stricter filtering
    composite_score_min: 70   # Higher score requirement
  insider_cluster:
    min_insiders: 3           # Require more insiders
    min_value_total: 200000   # Higher dollar amount
  minimum_conviction: 50      # Only report signals ≥ 50
```

### Custom Weights

Modify velocity composite score weights in `src/metrics/velocity.py`:
```python
weights = {
    'mention_24h': 0.40,   # Increase importance of 24h velocity
    'mention_7d': 0.20,    # Decrease 7d trend weight
    'sentiment': 0.30,     # Increase sentiment weight
    'divergence': 0.10     # Decrease divergence weight
}
```

---

## Troubleshooting

### Common Issues

**1. "Configuration file not found"**
- Solution: Copy `config/config.example.yaml` to `config/config.yaml`

**2. "Finnhub API error: 401"**
- Solution: Check API key in config, verify it's valid

**3. "No signals generated"**
- Check logs for data collection issues
- Verify thresholds aren't too strict
- Ensure sufficient historical data (run for several days)

**4. "Email sending failed"**
- For Gmail: Use app password, not regular password
- Check SMTP settings in config
- Verify firewall isn't blocking port 587

**5. "OpenInsider scraping failed"**
- Website structure may have changed
- Check if site is accessible
- Respect rate limits (1 second delay between requests)

### Logs

All logs are written to `logs/pipeline.log` and stdout.

Enable debug logging:
```bash
python main.py --log-level DEBUG
```

---

## Performance Optimization

### Rate Limiting
- ApeWisdom: ~100 requests/day (be conservative)
- OpenInsider: 1 request per URL per run (with 1s delay)
- Finnhub: 55 requests/minute (free tier = 60/min)

### Database Maintenance
Consider pruning old data:
```sql
-- Delete data older than 90 days
DELETE FROM mentions WHERE collected_at < date('now', '-90 days');
DELETE FROM prices WHERE collected_at < date('now', '-90 days');
DELETE FROM velocity WHERE calculated_at < date('now', '-90 days');
```

---

## Development Notes

### Code Style
- All code uses Doxygen-style comments
- Follow PEP 8 style guide
- Use type hints where applicable

### Testing
- Unit tests for all major functions
- Mock external API calls in tests
- Integration tests marked with `@pytest.mark.integration`

### Documentation
- All updates and notes go in this file (NOTES.md)
- Do not create separate documentation files
- Keep README.md as technical specification

---

## Future Enhancements (Roadmap)

### Phase 2
- [ ] FRED macro indicator integration
- [ ] Backtesting module for signal validation
- [ ] Paper trading integration
- [ ] Performance metrics dashboard

### Phase 3
- [ ] Options flow data (Unusual Whales/Cheddar Flow)
- [ ] Congress trades tracking (Quiver Quant)
- [ ] Web dashboard (Flask/FastAPI)
- [ ] Discord/Telegram bot for notifications

### Phase 4
- [ ] Machine learning for signal optimization
- [ ] Multi-timeframe analysis
- [ ] Correlation with market regime
- [ ] Real broker API integration

---

## Known Limitations

1. **Data Sources**
   - ApeWisdom API is undocumented, may change without notice
   - OpenInsider scraping is brittle, depends on HTML structure
   - Free Finnhub tier has rate limits

2. **Analysis**
   - Requires several days of data for meaningful velocity calculations
   - Social sentiment can be manipulated
   - Insider trades are lagging indicators (filed after transaction)

3. **Execution**
   - No real-time monitoring (designed for daily batch runs)
   - Email only notification (no mobile push notifications)

---

## Risk Disclaimer

⚠️ **IMPORTANT**: This tool is for educational and research purposes only.

- NOT financial advice
- Past performance does not guarantee future results
- Social sentiment can be manipulated
- Always paper trade first before using real capital
- Verify all signals independently before trading
- Consider consulting a licensed financial advisor

---

## Version History

### v1.0.0 (2025-12-18)
- Initial release
- Core pipeline implementation
- ApeWisdom, OpenInsider, Finnhub collectors
- Velocity metrics calculator
- Signal generator with multi-factor scoring
- HTML email reporter
- Comprehensive test suite
- Full Doxygen documentation

---

## Contributing

To add features or fix bugs:
1. Update code with Doxygen comments
2. Add unit tests
3. Update this NOTES.md file
4. Test thoroughly before committing

---

## Support & Resources

- **Finnhub Documentation**: https://finnhub.io/docs/api
- **FRED API Documentation**: https://fred.stlouisfed.org/docs/api/
- **ApeWisdom**: https://apewisdom.io/
- **OpenInsider**: http://openinsider.com/

---

## License

See LICENSE file for details.

---

**End of Notes**
