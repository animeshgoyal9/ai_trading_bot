# AI Trading Bot

An automated stock trading bot powered by Mistral AI that scans markets, analyzes stocks with technical indicators, executes paper trades via Alpaca, and sends a daily catalyst digest email.

---

## What It Does

| Component | File | What it does |
|-----------|------|--------------|
| **Trading Bot** | `stock_trader.py` | Runs continuously, scans 129 stocks every 3 hours during market hours, uses Mistral AI to decide BUY/SELL/HOLD, executes paper trades via Alpaca |
| **Dashboard** | `update_stock_data.py` | Refreshes `stock_analysis_v6.html` — a local HTML dashboard showing all holdings with scores, options flow, analyst targets, P/C ratios |
| **Catalyst Scanner** | `catalyst_scanner.py` | Scans SEC EDGAR 8-K filings + Google News RSS daily, screens S&P 500 + NASDAQ 100 for AI/semiconductor/defense catalysts, emails a digest |
| **Crypto Bot** | `crypto_trader.py` | Same bot logic but for BTC/ETH/SOL/XRP via Alpaca Crypto |
| **Backtesting** | `backtesting.py` + `generate_backtest_report.py` | Backtest strategies on historical data |

---

## Quick Start

### 1. Clone & create virtual environment

```bash
git clone git@github.com:animeshgoyal9/ai_trading_bot.git
cd ai_trading_bot
python3 -m venv trading
source trading/bin/activate      # Windows: trading\Scripts\activate
pip install -r requirements.txt
```

### 2. Create your `.env` file

```bash
cp .env.example .env
```

Then edit `.env` with your API keys (see [API Keys](#api-keys) below).

### 3. Create the logs directory

```bash
mkdir -p logs
```

### 4. Run the trading bot

```bash
source trading/bin/activate
caffeinate -i python -u stock_trader.py >> logs/stock_trader.log 2>&1 &
tail -f logs/stock_trader.log
```

### 5. Run the dashboard

```bash
python update_stock_data.py
open stock_analysis_v6.html
```

### 6. Run the catalyst scanner

```bash
python catalyst_scanner.py --email
```

---

## API Keys

You need accounts for the following (all have free tiers):

| Service | Purpose | Get key at |
|---------|---------|------------|
| **Alpaca** | Paper trading execution | [alpaca.markets](https://alpaca.markets) → Paper Trading |
| **Mistral AI** | Trading decisions (AI agent) | [console.mistral.ai](https://console.mistral.ai) |
| **NewsAPI** | News headlines for scanner | [newsapi.org](https://newsapi.org) |
| **Alpha Vantage** | Financial data | [alphavantage.co](https://www.alphavantage.co) |
| **Gmail App Password** | Email digest notifications | [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords) |

Optional (bot works without these):
| **Gemini** | Alternative AI agent | [aistudio.google.com](https://aistudio.google.com/apikey) |
| **Anthropic** | Alternative AI agent | [console.anthropic.com](https://console.anthropic.com) |

### `.env` template

```bash
# Alpaca (Paper Trading — free)
ALPACA_API_KEY=your_key
ALPACA_SECRET_KEY=your_secret
ALPACA_BASE_URL=https://paper-api.alpaca.markets

# Trading parameters
TRADING_CAPITAL=10000
MAX_POSITION_SIZE=0.2
STOP_LOSS_PERCENT=0.07
TAKE_PROFIT_PERCENT=0.15
TRADING_MODE=stocks           # 'stocks' or 'crypto'
ENABLE_EXTENDED_HOURS=true

# Mistral AI (primary AI agent — free tier)
MISTRAL_API_KEY=your_key
MISTRAL_MODEL=mistral-small-latest

# Email notifications (Gmail + App Password)
NOTIFY_EMAIL=you@gmail.com
NOTIFY_APP_PASSWORD=xxxx xxxx xxxx xxxx   # 4-word app password, spaces OK

# NewsAPI (free — 100 req/day)
NEWS_API_KEY=your_key

# Alpha Vantage (free — 500 req/day)
ALPHA_VANTAGE_KEY=your_key

# Optional: Gemini AI
GEMINI_API_KEY=your_key
USE_GEMINI_AGENT=false
GEMINI_MODEL=gemini-1.5-flash

# Optional: Claude AI
ANTHROPIC_API_KEY=your_key
USE_CLAUDE_AGENT=false
CLAUDE_MODEL=claude-sonnet-4-20250514
CLAUDE_MIN_CONFIDENCE=0.3
```

---

## Running Automatically (macOS cron)

To run the catalyst scanner Mon–Fri at 8 AM and Sunday at 9 AM:

```bash
crontab -e
```

Add:
```
0 8 * * 1-5 cd /path/to/ai_trading_bot && source trading/bin/activate && python3 catalyst_scanner.py --email >> logs/scanner.log 2>&1
0 9 * * 0   cd /path/to/ai_trading_bot && source trading/bin/activate && python3 catalyst_scanner.py --email >> logs/scanner.log 2>&1
```

---

## How the Trading Bot Works

1. **Pre-filter** — scans all 129 stocks using RSI, volume, MACD, SMA to pick the top 15 setups (fast, no AI)
2. **AI analysis** — sends each candidate's technical data to Mistral, gets BUY/SELL/HOLD + confidence + reasoning
3. **Trade execution** — if confidence ≥ 30%, places a bracket order on Alpaca with stop-loss and take-profit
4. **Email alert** — sends an email for every executed trade
5. **Repeat** — sleeps 3 hours, then runs again

---

## How the Catalyst Scanner Works

1. **SEC EDGAR** — searches 8-K filings for AI, joint venture, data center, machine learning keywords
2. **Google News RSS** — scans 8 query strings for AI/semiconductor/defense news, extracts tickers
3. **Hidden Gem Screener** — loads full S&P 500 + NASDAQ 100, filters for AI/semiconductor/defense theme, scores by: analyst upside, 52-week position, PEG ratio, P/C options ratio, revenue growth, margins
4. **Email + HTML** — injects results into `stock_analysis_v6.html` and emails a digest

### Scanner CLI options

```bash
python catalyst_scanner.py               # run all 3 engines, no email
python catalyst_scanner.py --email       # run all 3 engines + send email
python catalyst_scanner.py --quick       # skip screener (faster)
python catalyst_scanner.py --screen-only # screener only
python catalyst_scanner.py --days 3      # look back 3 days for EDGAR filings
```

---

## Customising Your Stock Universe

Edit `config.py`:

```python
STOCK_UNIVERSE = [
    'NVDA', 'AMD', 'TSM',   # add your stocks
]
```

The bot always monitors everything in `STOCK_UNIVERSE` plus the top candidates from `NASDAQ_100` that pass the pre-filter.

---

## Project Structure

```
ai_trading_bot/
├── stock_trader.py           # Entry point — starts the trading loop
├── claude_trading_bot.py     # Core bot logic (pre-filter, AI, order execution)
├── config.py                 # All configuration & stock universes
├── mistral_agent.py          # Mistral AI integration
├── data_collector.py         # Fetches price data from Alpaca
├── feature_engineering.py    # 40+ technical indicators (RSI, MACD, BB, etc.)
├── risk_management.py        # Position sizing, stop-loss, take-profit
├── notify.py                 # Email alerts via Gmail SMTP
├── catalyst_scanner.py       # Daily SEC + News + Screener scanner
├── update_stock_data.py      # Refreshes the HTML dashboard
├── stock_analysis_v6.html    # Live dashboard (open in browser)
├── discoveries.json          # Latest scanner output
├── crypto_trader.py          # Crypto trading bot (BTC/ETH/SOL/XRP)
├── backtesting.py            # Backtest strategies on historical data
├── generate_backtest_report.py  # Generate HTML backtest reports
├── requirements.txt
├── .env.example
└── archive_old_files/        # Old/replaced scripts (kept for reference)
```

---

## Safety

- **Paper trading only** by default — uses Alpaca's paper trading environment (fake money)
- Stop-loss: 7% below entry
- Take-profit: 15% above entry
- Max position size: 20% of capital
- Minimum confidence: 30% before any trade fires

> To switch to live trading, change `ALPACA_BASE_URL` to `https://api.alpaca.markets` in `.env`. Do so at your own risk.

---

## Disclaimer

This is an educational project. It trades paper (fake) money by default. Past performance does not guarantee future results. Do not use this with real money without fully understanding the risks.
