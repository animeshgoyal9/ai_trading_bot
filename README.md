# AI Trading Bot - Claude Powered

Automated stock trading bot that uses Claude AI (Anthropic) to analyze stocks and make trading decisions.

## 📁 Project Structure

### Core Trading Files
- **`stock_analyzer.py`** - **NEW!** Analyzes all stocks and shows BUY/SELL/HOLD in a table
- **`run_claude_bot_once.py`** - Main script to run the bot (analyzes all stocks and executes trades)
- **`nasdaq_screener.py`** - Analyzes stocks and shows only high-confidence buy opportunities
- **`claude_trading_bot.py`** - Core trading bot logic
- **`claude_agent.py`** - Claude AI agent that analyzes stocks and makes decisions
- **`config.py`** - Configuration settings (stocks, risk parameters, API keys)

### Data & Analysis
- **`data_collector.py`** - Fetches stock price data from Alpaca
- **`feature_engineering.py`** - Calculates 40+ technical indicators (RSI, MACD, Bollinger Bands, etc.)
- **`risk_management.py`** - Position sizing, stop-loss, take-profit calculations

### Tools & Scripts
- **`check_prices.py`** - Check current real-time prices for your stocks
- **`setup_scheduler.py`** - Set up automated daily runs at 9 AM CST
- **`run_bot_wrapper.sh`** - Wrapper script used by scheduler

### Documentation
- **`SCREENER_GUIDE.md`** - How to use the stock screener
- **`PRICE_DIFFERENCES_EXPLAINED.md`** - Why prices differ between sources

### Configuration Files
- **`.env`** - API keys and configuration (create from `.env.example`)
- **`requirements.txt`** - Python dependencies
- **`trading/`** - Virtual environment directory

## 🚀 Quick Start

### 1. Setup Environment
```bash
# Activate virtual environment
source trading/bin/activate

# Install dependencies (if needed)
pip install -r requirements.txt
```

### 2. Configure API Keys
Edit `.env` file with your API keys:
```bash
# Alpaca API (Paper Trading)
ALPACA_API_KEY=your_key_here
ALPACA_SECRET_KEY=your_secret_here
ALPACA_BASE_URL=https://paper-api.alpaca.markets

# Claude API
ANTHROPIC_API_KEY=your_anthropic_key_here
```

### 3. Configure Your Portfolio
Edit `config.py` to set your stocks:
```python
STOCK_UNIVERSE = [
    'GLD', 'SNDK', 'LITE', 'AVGO', 'NVDA',
    'MP', 'RKLB', 'USAR', 'APLD', 'IREN',
    'UUUU', 'AAPL'
]
```

## 📊 Usage

### Analyze All Stocks (Recommended - Shows Table Summary)
Get a complete overview of all your stocks with BUY/SELL/HOLD recommendations in a table:
```bash
# Quick table view
python stock_analyzer.py

# With detailed reasoning for each stock
python stock_analyzer.py --detailed
```

**What it shows:**
- Clean table showing all stocks with action, confidence, price, and technical indicators
- Highlights SELL recommendations for stocks you currently hold
- Shows which stocks Claude recommends buying
- Organizes by priority: urgent sells first, then strong buys, then holds
- Saves detailed analysis to logs

### Run the Trading Bot Once
Analyzes all stocks and executes trades based on Claude's recommendations:
```bash
python run_claude_bot_once.py
```

**What it does:**
- Analyzes each stock in your portfolio
- Gets Claude's BUY/SELL/HOLD decision with confidence level
- Executes trades if confidence >= 30%
- Shows full reasoning for each decision
- Uses real-time prices (not yesterday's close)

### Screen for Buy Opportunities
Shows only high-confidence buy opportunities without executing trades:
```bash
# Show 70%+ confidence buys
python nasdaq_screener.py

# Show only "sure shot" 80%+ confidence buys
python nasdaq_screener.py --confidence 0.80
```

See [SCREENER_GUIDE.md](SCREENER_GUIDE.md) for more details.

### Check Current Prices
Verify what prices the bot sees from Alpaca:
```bash
python check_prices.py
```

### Set Up Automated Daily Runs
Run bot automatically every weekday at 9:00 AM CST:
```bash
python setup_scheduler.py
```

Then verify it's scheduled:
```bash
launchctl list | grep tradingbot
```

## ⚙️ Configuration

### Key Settings in `.env`

```bash
# Trading Parameters
TRADING_CAPITAL=10000              # Starting capital
MAX_POSITION_SIZE=0.1              # Max 10% per position
STOP_LOSS_PERCENT=0.05             # 5% stop loss
TAKE_PROFIT_PERCENT=0.10           # 10% take profit

# AI Agent
USE_CLAUDE_AGENT=true
CLAUDE_MODEL=claude-sonnet-4-20250514
CLAUDE_MIN_CONFIDENCE=0.3          # Trade if confidence >= 30%

# Market Hours
EXTENDED_HOURS=false               # Paper trading only supports regular hours
```

### Your Stock Portfolio
Edit `STOCK_UNIVERSE` in `config.py`:
```python
STOCK_UNIVERSE = [
    'AAPL',   # Add your stocks here
    'NVDA',
    # ... more stocks
]
```

## 🤖 How It Works

1. **Data Collection**: Fetches 100 days of price history from Alpaca
2. **Technical Analysis**: Calculates 40+ indicators (RSI, MACD, Bollinger Bands, etc.)
3. **AI Analysis**: Claude analyzes the data and technical indicators
4. **Decision Making**: Claude returns action (BUY/SELL/HOLD), confidence (0-100%), risk level, and reasoning
5. **Trade Execution**: If confidence >= threshold, executes bracket order with stop-loss and take-profit
6. **Position Management**: Claude analyzes existing positions for sell decisions

## 📈 Trading Logic

### Buy Orders
- Claude recommends BUY with confidence >= 30%
- Position size calculated based on risk (max 10% of capital)
- Bracket order placed with:
  - Stop Loss: 5% below entry
  - Take Profit: 10% above entry

### Sell Orders
- Claude analyzes existing positions daily
- Sells if Claude recommends SELL with confidence >= 30%
- Risk manager can override (force sell if stop-loss hit)

## 📝 Logs

All bot activity is logged to:
- `logs/trading_bot.log` - Manual runs
- `logs/scheduled_bot.log` - Scheduled runs
- `logs/screen_results_*.txt` - Screener results

## 🔧 Troubleshooting

### Bot showing wrong prices
The bot now fetches **real-time prices** using `get_current_price()` instead of yesterday's close.

See [PRICE_DIFFERENCES_EXPLAINED.md](PRICE_DIFFERENCES_EXPLAINED.md) for details on price variations.

### Network Issues
If running through Claude Code or on corporate network:
1. Run from your own terminal (not through Claude Code)
2. Be on a non-corporate network (home WiFi, mobile hotspot)

### Check if scheduler is running
```bash
# View scheduled jobs
launchctl list | grep tradingbot

# Check recent logs
tail -50 logs/scheduled_bot.log
```

## 🛡️ Safety Features

- **Paper Trading**: Uses Alpaca paper trading (fake money) by default
- **Position Limits**: Max 10% of capital per position
- **Stop Loss**: Automatic 5% stop loss on all positions
- **Take Profit**: Automatic 10% take profit target
- **Confidence Threshold**: Only trades with >= 30% confidence
- **Risk Manager**: Safety override can force exits

## 📚 Key Files Explained

| File | Purpose |
|------|---------|
| `stock_analyzer.py` | **NEW!** Complete overview with table - shows BUY/SELL/HOLD for all stocks |
| `run_claude_bot_once.py` | Main entry point - run this to trade |
| `nasdaq_screener.py` | Screen stocks without trading |
| `claude_agent.py` | Claude AI integration |
| `claude_trading_bot.py` | Core bot logic |
| `config.py` | All configuration settings |
| `data_collector.py` | Fetch stock data |
| `feature_engineering.py` | Calculate indicators |
| `risk_management.py` | Position sizing & risk |
| `check_prices.py` | Verify current prices |
| `setup_scheduler.py` | Set up daily automation |

## 🗂️ Archived Files

Old/unused files have been moved to `archive_old_files/`:
- Gemini integration (replaced by Claude)
- ML models (not used)
- Backtesting code (not needed for live trading)
- Test scripts
- Old documentation

## 📞 Support

- Check logs in `logs/` directory
- Review configuration in `.env` and `config.py`
- See `SCREENER_GUIDE.md` for screener usage
- See `PRICE_DIFFERENCES_EXPLAINED.md` for price questions

## ⚠️ Disclaimer

This bot is for educational purposes. Always test with paper trading before using real money. Past performance does not guarantee future results.
