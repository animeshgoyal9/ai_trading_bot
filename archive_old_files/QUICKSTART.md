# Quick Start Guide

## Get Started in 5 Minutes

### Step 1: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 2: Get Free Alpaca Account
1. Go to https://alpaca.markets/
2. Sign up for a free account
3. Navigate to "Paper Trading"
4. Copy your API Key and Secret Key

### Step 3: Configure Environment
```bash
cp .env.example .env
```

Edit `.env` and add your credentials:
```
ALPACA_API_KEY=your_key_here
ALPACA_SECRET_KEY=your_secret_here
```

### Step 4: Train Your First Model
```bash
python main.py train --symbol AAPL
```

This will:
- Download AAPL historical data
- Train ML model
- Run backtest
- Show results
- Save model

Expected output:
```
Training model for AAPL
Fetched 1000+ records
Train set: 800 samples, Test set: 200 samples
Model training completed
Accuracy: 0.65, Precision: 0.68

BACKTEST SUMMARY
Total Return: 12.5%
Win Rate: 60%
Sharpe Ratio: 1.5
```

### Step 5: Run Paper Trading
```bash
python main.py trade
```

The bot will now:
- Monitor stocks in real-time
- Make buy/sell predictions
- Execute trades automatically
- Log all activity

Press `Ctrl+C` to stop.

### Step 6: Check Your Status
```bash
python main.py status
```

View:
- Portfolio value
- Current positions
- Profit/loss

## What Happens During Trading?

1. **Every 60 seconds**, the bot:
   - Fetches latest prices
   - Calculates technical indicators
   - Makes ML prediction
   - Checks confidence level

2. **On BUY signal** (confidence > 60%):
   - Calculates position size (10% of capital)
   - Places bracket order with:
     - Buy at market price
     - Stop loss at -2%
     - Take profit at +5%

3. **On SELL signal**:
   - Closes position
   - Logs profit/loss
   - Frees up capital

## Example Trading Session

```
09:30 - Market opens
09:31 - Checking 10 stocks...
09:31 - BUY signal: AAPL, confidence: 0.75
09:31 - Bought 10 shares @ $150.50
        Stop loss: $147.49
        Take profit: $158.03

10:15 - AAPL reached take profit!
10:15 - Sold 10 shares @ $158.03
        Profit: $75.30 (5%)

11:30 - BUY signal: MSFT, confidence: 0.68
11:30 - Bought 5 shares @ $340.20
        Stop loss: $333.40
        Take profit: $357.21

16:00 - Market closes
        Portfolio: $10,425.30 (+4.25%)
```

## Tips for First Time

1. **Start Small**: Default is $10,000 paper money
2. **Watch Closely**: Monitor first few trades
3. **Review Logs**: Check `logs/trading_bot.log`
4. **Adjust Settings**: Modify `config.py` as needed
5. **Be Patient**: May take hours to find good signals

## Common First Steps

### Trade Different Stocks
Edit `config.py`:
```python
STOCK_UNIVERSE = ['AAPL', 'GOOGL', 'MSFT', 'AMZN', 'NVDA']
```

### Adjust Risk
```python
MAX_POSITION_SIZE = 0.05  # 5% per trade (more conservative)
STOP_LOSS_PERCENT = 0.03  # 3% stop loss (wider)
```

### Change Check Interval
In `run_paper_trading.py`:
```python
bot.run_trading_loop(check_interval=300)  # Check every 5 minutes
```

## Troubleshooting

**Error: No trained models found**
```bash
python train_model.py
```

**Error: Invalid API credentials**
- Check `.env` file
- Verify credentials at https://app.alpaca.markets/

**No trades executing**
- Check if market is open (9:30-16:00 ET weekdays)
- Lower `MIN_CONFIDENCE` in config.py
- Check logs for details

**Bot stops running**
- Check internet connection
- Review error in logs
- Restart: `python main.py trade`

## Next Steps

1. **Backtest Multiple Stocks**: See which perform best
2. **Optimize Parameters**: Adjust indicators and thresholds
3. **Monitor Performance**: Track daily results
4. **Paper Trade for 30 Days**: Before considering real money
5. **Learn More**: Study technical analysis and ML

## Safety Reminders

- This is PAPER TRADING (fake money)
- Always test thoroughly before real money
- Start small even with real money
- Never invest more than you can lose
- Markets can be unpredictable

## Getting Help

- Read the full [README.md](README.md)
- Check `logs/trading_bot.log` for errors
- Review [config.py](config.py) for all settings
- Alpaca docs: https://alpaca.markets/docs/

Happy trading!
