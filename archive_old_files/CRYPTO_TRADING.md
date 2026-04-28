# 🪙 Crypto Trading with Gemini AI

Yes! Your bot can trade **Bitcoin and other cryptocurrencies** using Alpaca's crypto paper trading!

## Quick Start - Trade Bitcoin Now!

### 1. Enable Crypto Mode

Edit your **[.env](.env)** file:

```bash
# Change this line:
TRADING_MODE=stocks

# To this:
TRADING_MODE=crypto
```

### 2. Run the Bot

```bash
python run_gemini_bot.py
```

That's it! Gemini will now trade Bitcoin, Ethereum, and other cryptos!

## Supported Cryptocurrencies

Your bot is configured to trade these by default:

```python
BTC/USD    # Bitcoin
ETH/USD    # Ethereum
DOGE/USD   # Dogecoin
SHIB/USD   # Shiba Inu
SOL/USD    # Solana
```

### Add More Cryptos

Edit **[config.py](config.py)** and add to `CRYPTO_UNIVERSE`:

```python
CRYPTO_UNIVERSE = [
    'BTC/USD',   # Bitcoin
    'ETH/USD',   # Ethereum
    'DOGE/USD',  # Dogecoin
    'SHIB/USD',  # Shiba Inu
    'SOL/USD',   # Solana
    'AVAX/USD',  # Avalanche
    'MATIC/USD', # Polygon
    'UNI/USD',   # Uniswap
    'LINK/USD',  # Chainlink
    'LTC/USD',   # Litecoin
]
```

## Example Crypto Trading Session

```
🤖 GEMINI AI TRADING BOT
============================================================

✅ Gemini Model: gemini-2.0-flash-exp
✅ Min Confidence: 70%
✅ Trading Capital: $10,000
✅ Trading Mode: CRYPTO
✅ Assets to Trade: 5

🎯 Starting Gemini AI Trading...
   Trading: BTC/USD, ETH/USD, DOGE/USD, SHIB/USD, SOL/USD

--- Analyzing BTC/USD ---
Current price: $42,500.00

Asking Gemini for analysis...

🤖 Gemini's Decision:
   Action: BUY
   Confidence: 78%
   Risk Level: medium
   Reasoning: Bitcoin showing strong technical setup. RSI at 45
   indicates neutral momentum with room to run. MACD histogram
   turning positive after consolidation. Price held above $40k
   support level multiple times. Volume increasing on breakout
   attempt. Market sentiment improving with institutional buying.
   Entry at $42,500 provides good risk/reward with stop at $41,500
   and target at $45,000.

✅ BUY 0.23 BTC @ $42,500.00
   Gemini's confidence: 78%
   Stop Loss: $41,650.00
   Take Profit: $44,625.00
```

## Crypto vs Stocks - Key Differences

### ⏰ **24/7 Trading**
- Stocks: 9:30 AM - 4:00 PM ET (weekdays)
- **Crypto: 24/7/365** ✅

Your bot can trade Bitcoin anytime, even on weekends!

### 📊 **Volatility**
- Stocks: Moderate (usually ±2-5% daily)
- **Crypto: HIGH** (can swing ±10-20% daily)

**Recommended adjustments for crypto:**

```bash
# In .env file:
STOP_LOSS_PERCENT=0.05      # 5% stop loss (crypto is volatile)
TAKE_PROFIT_PERCENT=0.10    # 10% take profit (bigger moves)
MAX_POSITION_SIZE=0.05      # 5% per trade (manage risk)
GEMINI_MIN_CONFIDENCE=0.75  # Higher threshold for crypto
```

### 💰 **Fractional Shares**
- Stocks: Can buy 0.1 shares
- **Crypto: Can buy 0.0001 BTC** ✅

Perfect for Bitcoin! You don't need $42,000 to trade BTC.

## Alpaca Crypto Trading

### Paper Trading
- **FREE paper trading** with virtual money
- Same API as stocks (seamless integration)
- Real-time crypto prices
- All major cryptocurrencies supported

### Symbol Format
```python
# Alpaca uses slash notation:
'BTC/USD'   ✅ Correct
'BTCUSD'    ❌ Wrong
'BTC-USD'   ❌ Wrong
```

### Available Cryptos on Alpaca

Alpaca supports 50+ cryptocurrencies including:

**Major Cryptos:**
- BTC/USD (Bitcoin)
- ETH/USD (Ethereum)
- USDT/USD (Tether)
- BNB/USD (Binance Coin)
- XRP/USD (Ripple)

**DeFi:**
- UNI/USD (Uniswap)
- AAVE/USD (Aave)
- LINK/USD (Chainlink)

**Meme Coins:**
- DOGE/USD (Dogecoin)
- SHIB/USD (Shiba Inu)

**Layer 1s:**
- SOL/USD (Solana)
- AVAX/USD (Avalanche)
- MATIC/USD (Polygon)

Full list: https://alpaca.markets/support/what-are-the-supported-crypto-assets-on-alpaca

## Gemini's Crypto Analysis

Gemini is excellent for crypto because it:

### 🧠 Understands Crypto Markets
- Knows about Bitcoin, Ethereum, etc.
- Understands blockchain concepts
- Recognizes crypto market patterns
- Considers crypto-specific factors

### 📰 Follows Crypto News
- Bitcoin ETF approvals
- Regulatory news
- Exchange hacks/issues
- Whale movements
- Social sentiment

### ⚡ Handles Volatility
- Adjusts for high crypto volatility
- More conservative with risk
- Recognizes extreme moves
- Considers market manipulation risks

## Configuration for Crypto

### Recommended Settings

```bash
# .env file for crypto trading:

TRADING_MODE=crypto
TRADING_CAPITAL=10000
MAX_POSITION_SIZE=0.05        # 5% per trade (crypto is risky)
STOP_LOSS_PERCENT=0.05        # 5% stop loss (volatile)
TAKE_PROFIT_PERCENT=0.10      # 10% take profit (bigger swings)
GEMINI_MIN_CONFIDENCE=0.75    # Higher bar for crypto trades
```

### Check Interval

```python
# Crypto moves fast - check more frequently
check_interval=300   # Every 5 minutes (default)

# Or even faster (but more API calls)
check_interval=60    # Every minute
```

## Gemini's Crypto Reasoning Example

```
🤖 Gemini's Analysis for ETH/USD:

Action: BUY
Confidence: 72%
Risk Level: medium-high

Reasoning:
"Ethereum showing bullish setup but with elevated risk:

Bullish Signals:
1. RSI at 38 - oversold after recent pullback
2. MACD histogram turning positive - momentum shift
3. Price held $2,200 support (tested 3x, held each time)
4. On-chain metrics show increasing activity
5. Bitcoin correlation positive - BTC leading up

Crypto-Specific Factors:
- Network upgrades reducing supply (deflationary pressure)
- DeFi activity increasing on Ethereum
- Institutional interest growing (Ethereum ETFs coming)
- Gas fees have decreased (better usability)

Risk Factors:
- High volatility (45% annualized) - larger position risk
- Regulatory uncertainty around crypto still present
- Market sentiment can shift rapidly on news
- Correlation with risk assets (stocks down, crypto may follow)

Market Context:
- Bitcoin stable around $42k (supportive for ETH)
- Crypto market sentiment neutral (fear & greed at 52)
- No major negative news in past 24 hours

Risk Management:
- Entry at $2,320 provides defined risk
- Stop loss at $2,204 (5% below) protects against breakdown
- Take profit at $2,552 (10% above) hits resistance zone
- Position size should be 50% of max due to volatility

Recommendation: BUY with reduced position size. The technical
setup is good but crypto volatility requires extra caution."
```

## Switch Between Stocks and Crypto

### Trade Stocks
```bash
# In .env:
TRADING_MODE=stocks
```

### Trade Crypto
```bash
# In .env:
TRADING_MODE=crypto
```

### Trade Both (Not Recommended)

If you want to trade both, you'll need to:
1. Run two separate bot instances
2. Use different capital allocations
3. Manage separately

## Tips for Crypto Trading

### 1. **Start Small**
```bash
TRADING_CAPITAL=1000        # Start with $1k
MAX_POSITION_SIZE=0.03      # 3% per trade
```

### 2. **Use Wider Stops**
Crypto is volatile - tight stops get hit constantly:
```bash
STOP_LOSS_PERCENT=0.05      # 5% minimum
TAKE_PROFIT_PERCENT=0.10    # 10% targets
```

### 3. **Higher Confidence**
Be more selective with crypto trades:
```bash
GEMINI_MIN_CONFIDENCE=0.75  # Only high-confidence trades
```

### 4. **Monitor More Closely**
- Check every few hours
- Review Gemini's reasoning
- Watch for major news events
- Be ready to intervene

### 5. **Understand the Risks**
- Crypto is highly volatile
- Can lose money fast
- Market manipulation exists
- Regulatory risk
- Exchange risk

### 6. **Paper Trade First**
- Test with fake money
- Learn crypto behavior
- Tune your settings
- Build confidence

## Example: Bitcoin Trading

### Step 1: Enable Crypto
```bash
# .env
TRADING_MODE=crypto
```

### Step 2: Configure for BTC
```python
# config.py - Just trade Bitcoin
CRYPTO_UNIVERSE = ['BTC/USD']
```

### Step 3: Adjust Settings
```bash
# .env - Conservative BTC trading
MAX_POSITION_SIZE=0.10       # 10% per trade
STOP_LOSS_PERCENT=0.04       # 4% stop
TAKE_PROFIT_PERCENT=0.08     # 8% target
GEMINI_MIN_CONFIDENCE=0.80   # Very selective
```

### Step 4: Run
```bash
python run_gemini_bot.py
```

## Troubleshooting

### "Symbol not found" error
- Check symbol format: `BTC/USD` not `BTCUSD`
- Verify Alpaca supports that crypto
- Check if symbol is available for paper trading

### No trades executing
- Lower `GEMINI_MIN_CONFIDENCE` (try 0.65)
- Check Gemini's reasoning (might see high risk)
- Crypto markets can be quiet sometimes
- Try different cryptos (BTC, ETH more active)

### High volatility losses
- Use wider stops (5%+ for crypto)
- Lower position sizes
- Increase confidence threshold
- Trade less volatile cryptos (BTC, ETH vs meme coins)

## Cost Comparison: Crypto vs Stocks

### With Gemini (FREE)
- **Stocks**: FREE (1,500 RPD)
- **Crypto**: FREE (1,500 RPD)
- **Same API calls**, works the same!

### Crypto Benefits
- 24/7 trading (more opportunities)
- Higher volatility (bigger gains/losses)
- Fractional trading (buy 0.01 BTC)
- Global market (never closes)

## Summary

✅ **Yes! Your bot can trade Bitcoin on paper**

### To Enable:
1. Set `TRADING_MODE=crypto` in .env
2. Adjust settings for volatility
3. Run `python run_gemini_bot.py`

### Key Points:
- ✅ FREE with Gemini AI
- ✅ Paper trading available
- ✅ 24/7 trading
- ✅ All major cryptos supported
- ⚠️ Higher risk/volatility
- ⚠️ Start small and careful

### Recommended Start:
```bash
TRADING_MODE=crypto
TRADING_CAPITAL=1000
MAX_POSITION_SIZE=0.05
STOP_LOSS_PERCENT=0.05
TAKE_PROFIT_PERCENT=0.10
GEMINI_MIN_CONFIDENCE=0.75
```

**Go trade some Bitcoin!** 🪙🚀

(Safely with paper trading first!)
