# Scheduled Trading Bot Setup

This guide explains how to set up your Claude trading bot to run automatically at 9 AM CST on weekdays.

## Quick Start

1. **Test the bot runs correctly:**
   ```bash
   python run_claude_bot_once.py
   ```
   This will run the bot once and show you what it would do.

2. **Install the scheduler:**
   ```bash
   python setup_scheduler.py
   ```
   This configures macOS to run the bot every day at 9 AM CST (weekdays only).

3. **That's it!** The bot now runs in the background automatically.

## How It Works

- **Schedule**: Every day at 9:00 AM (local time)
- **Weekdays Only**: The script checks if it's Monday-Friday and skips weekends
- **Background**: Runs even when terminal is closed
- **Logs**: All output saved to `logs/scheduled_bot.log`

## Checking Status

**See if the job is loaded:**
```bash
launchctl list | grep tradingbot
```

**View recent activity:**
```bash
tail -f logs/scheduled_bot.log
```

**View the full log file:**
```bash
cat logs/scheduled_bot.log
```

## Management Commands

**Disable the scheduler:**
```bash
python setup_scheduler.py uninstall
```

**Re-enable after disabling:**
```bash
python setup_scheduler.py
```

**Reload after making changes:**
```bash
launchctl unload ~/Library/LaunchAgents/com.tradingbot.claude.plist
launchctl load ~/Library/LaunchAgents/com.tradingbot.claude.plist
```

**Test run manually (doesn't wait for schedule):**
```bash
python run_claude_bot_once.py
```

## What Happens Each Day

At 9 AM CST on weekdays, the bot will:

1. ✅ Check if it's a weekday (skip if weekend)
2. ✅ Connect to Alpaca and Claude APIs
3. ✅ Get your current portfolio and positions
4. ✅ Analyze each stock in your universe (12 stocks)
5. ✅ For existing positions:
   - Ask Claude: Should we sell or hold?
   - Execute trades if Claude recommends with >30% confidence
6. ✅ For new opportunities:
   - Ask Claude: Should we buy or hold?
   - Execute trades if Claude recommends with >30% confidence
7. ✅ Log all decisions and trades
8. ✅ Exit (no continuous loop)

## Log Files

All activity is logged to:
- **Standard output**: `logs/scheduled_bot.log`
- **Errors**: `logs/scheduled_bot_error.log`
- **Trading logs**: `logs/trading_bot.log` (from loguru)

## Important Notes

⚠️ **Your computer must be awake at 9 AM** for the job to run. If your Mac is asleep, the job will be skipped.

⚠️ **Market hours**: The bot runs at 9 AM CST (8:30 AM before market opens in CT). If the market is closed, it will analyze but not execute trades.

⚠️ **API keys**: Make sure your `.env` file has valid API keys:
- `ANTHROPIC_API_KEY` (Claude)
- `ALPACA_API_KEY` (Alpaca)
- `ALPACA_SECRET_KEY` (Alpaca)

## Troubleshooting

**Job not running?**
1. Check if loaded: `launchctl list | grep tradingbot`
2. Check logs: `cat logs/scheduled_bot_error.log`
3. Test manually: `python run_claude_bot_once.py`

**Want to change the time?**
1. Uninstall: `python setup_scheduler.py uninstall`
2. Edit `setup_scheduler.py` and change the `Hour` value
3. Reinstall: `python setup_scheduler.py`

**Disable temporarily:**
```bash
launchctl unload ~/Library/LaunchAgents/com.tradingbot.claude.plist
```

**Re-enable:**
```bash
launchctl load ~/Library/LaunchAgents/com.tradingbot.claude.plist
```

## Comparison: Old vs New

**Old Way (run_claude_bot.py):**
- ❌ Continuous loop checking every 5 minutes
- ❌ Terminal must stay open
- ❌ Uses lots of API calls
- ❌ Computer must stay on all day

**New Way (run_claude_bot_once.py with scheduler):**
- ✅ Runs once per day at 9 AM
- ✅ Terminal closes automatically
- ✅ Minimal API usage
- ✅ Computer only needs to be on at 9 AM

## Example Log Output

```
============================================================
🤖 CLAUDE AI TRADING BOT - SCHEDULED RUN
Run time: 2026-02-10 09:00:00
============================================================

Weekday: Monday

Claude Model: claude-sonnet-4-20250514
Min Confidence: 30%
Trading Capital: $10,000
Stocks to Analyze: 12

📊 Account Info:
   Portfolio Value: $10,123.45
   Cash: $9,000.00
   Buying Power: $9,000.00

💼 Current Positions:
   NVDA: 1 shares @ $120.00
      P&L: $3.45 (2.9%)

🚀 Starting Analysis...

============================================================
Analyzing NVDA
============================================================
Current price: $123.45
Current position: 1 shares @ $120.00
P&L: $3.45 (2.9%)

Asking Claude for sell analysis...

🤖 Claude's Decision:
   Action: SELL
   Confidence: 75%
   Risk Level: medium
   Reasoning: Stock has reached take profit target and shows momentum weakening...

✅ SELL 1 shares of NVDA @ $123.45
   Claude's confidence: 75%

[... continues for all 12 stocks ...]

============================================================
📊 SESSION SUMMARY
============================================================

Stocks Analyzed: 12
Trades Executed: 3
Holds: 9

📊 Final Account Status:
   Portfolio Value: $10,156.78
   Cash: $9,123.45

✅ Analysis complete. Next run: Tomorrow at 9:00 AM CST
============================================================
```
