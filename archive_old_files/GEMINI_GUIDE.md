# Gemini AI Trading Bot Guide

🎉 Your bot now uses **Google's Gemini AI** to make intelligent trading decisions!

## Why Gemini?

### ✅ **100% FREE Tier**
- Generous free quota (1,500 requests/day)
- No credit card required
- Perfect for paper trading

### 🚀 **Fast & Powerful**
- Gemini 2.0 Flash - Lightning fast responses
- Advanced reasoning capabilities
- Understands financial markets

### 🧠 **Intelligent Analysis**
- Analyzes technical indicators
- Considers market context
- Explains every decision
- Conservative risk management

### 💰 **Cost Effective**
- **Free tier**: 1,500 RPD (requests per day)
- **Paid tier**: Starts at $0.075 per 1M tokens
- **Much cheaper than Claude**: ~10x less expensive

## Quick Start

### 1. Get FREE Gemini API Key (30 seconds)

```bash
1. Go to: https://aistudio.google.com/apikey
2. Click "Create API Key"
3. Copy the key
```

### 2. Add to .env File

```bash
GEMINI_API_KEY=your_key_here
USE_GEMINI_AGENT=true
```

### 3. Run the Bot

```bash
python run_gemini_bot.py
```

That's it! Gem

ini will start analyzing stocks and making trades.

## How It Works

### Data → Gemini → Decision → Trade

```
1. Bot collects stock data (price, indicators, market context)
2. Sends to Gemini for analysis
3. Gemini reasons about the trade
4. Returns decision with explanation
5. Bot executes if confident
```

### Example Analysis

```
--- Analyzing AAPL ---
Current price: $150.50

Asking Gemini for analysis...

🤖 Gemini's Decision:
   Action: BUY
   Confidence: 82%
   Risk Level: medium
   Reasoning: Strong technical setup. RSI at 42 shows oversold
   conditions with room to recover. MACD showing bullish crossover.
   Price bounced off 50-day SMA support. Market sentiment neutral.
   Risk/reward favorable with defined stop at $147.

✅ BUY 6 shares of AAPL @ $150.50
   Gemini's confidence: 82%
   Stop Loss: $147.49
   Take Profit: $158.03
```

## Configuration

### In .env file:

```bash
# Required: Gemini API Key (FREE at aistudio.google.com)
GEMINI_API_KEY=your_key_here

# Gemini Model (gemini-2.0-flash-exp is recommended - fastest & free)
GEMINI_MODEL=gemini-2.0-flash-exp

# Enable Gemini agent
USE_GEMINI_AGENT=true

# Minimum confidence to trade (0.0-1.0)
GEMINI_MIN_CONFIDENCE=0.7  # 70%

# Disable old approaches
USE_SENTIMENT=false
USE_CLAUDE_AGENT=false
```

### Available Gemini Models

| Model | Speed | Cost | Best For |
|-------|-------|------|----------|
| **gemini-2.0-flash-exp** | ⚡️ Fastest | FREE | Trading (Recommended!) |
| gemini-2.0-flash | Fast | Cheap | Production |
| gemini-1.5-pro | Slower | Higher | Complex analysis |

## What Gemini Analyzes

### 📊 Technical Indicators (30+)
- **Trend**: SMA, EMA, MACD, ADX
- **Momentum**: RSI, Stochastic, ROC
- **Volatility**: Bollinger Bands, ATR
- **Volume**: OBV, Volume patterns
- **Price Action**: Support/resistance, momentum

### 🌍 Market Context
- **VIX**: Market fear/volatility
- **SPY**: Overall market trend
- **Sector**: Industry performance

### 🎯 Risk Assessment
- Stop loss levels
- Position sizing
- Risk/reward ratio
- Volatility analysis

## Example Session

```
🤖 GEMINI AI TRADING BOT
============================================================

✅ Gemini Model: gemini-2.0-flash-exp
✅ Min Confidence: 70%
✅ Trading Capital: $10,000
✅ Stocks to Trade: 10

🚀 Initializing Gemini AI Trading Bot...

📊 Account Info:
   Portfolio Value: $10,000.00
   Cash: $10,000.00
   Buying Power: $10,000.00

💼 No current positions

🎯 Starting Gemini AI Trading...

============================================================
Portfolio Value: $10,000.00
============================================================

--- Analyzing AAPL ---
Current price: $150.50
Asking Gemini for analysis...

🤖 Gemini's Decision:
   Action: BUY
   Confidence: 85%
   Risk Level: medium
   Reasoning: Excellent technical setup with multiple bullish signals.
   RSI at 38 indicates oversold but not extreme, MACD histogram turning
   positive after bearish divergence. Price bounced off 200-day SMA
   support at $148. Volume spike on bounce shows buying interest.
   Market VIX at 19 is neutral. Entry at $150.50 provides good R:R
   with stop at $147 and target at $158.

✅ BUY 6 shares of AAPL @ $150.50
   Gemini's confidence: 85%
   Stop Loss: $147.49
   Take Profit: $158.03

--- Analyzing TSLA ---
Current price: $245.80
Asking Gemini for analysis...

🤖 Gemini's Decision:
   Action: HOLD
   Confidence: 45%
   Risk Level: high
   Reasoning: Mixed signals. RSI at 68 nearing overbought territory.
   MACD positive but losing momentum. Price extended 15% above 50-day
   SMA which is concerning. High volatility (45% annualized) adds risk.
   VIX elevated suggesting market uncertainty. No clear edge at current
   level. Better to wait for pullback to support around $230.

⏸️  HOLD TSLA - Not trading

Waiting 300 seconds until next check...
Next check at: 14:35:00
```

## Free Tier Limits

### Gemini 2.0 Flash (Recommended)
- **1,500 requests per day** - FREE!
- **4 million tokens per minute**
- **10,000 tokens per request**

### Usage Calculation
```
Trading 10 stocks, check every 5 minutes, 6.5 hours = 78 requests/day

You can run the bot ALL DAY for FREE! 🎉
```

### If You Hit Limits
```bash
# Check less frequently
check_interval=600  # Every 10 minutes

# Trade fewer stocks
STOCK_UNIVERSE = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA']

# Use Gemini Pro (higher limits)
GEMINI_MODEL=gemini-1.5-pro
```

## Gemini vs Claude vs ML

| Feature | Gemini | Claude | ML Model |
|---------|--------|--------|----------|
| **Cost** | FREE ✅ | $10-20/day | Free |
| **Training** | None ✅ | None | Days/weeks |
| **Reasoning** | Excellent ✅ | Excellent ✅ | Black box |
| **Explainable** | Yes ✅ | Yes ✅ | No |
| **Speed** | Fast ✅ | Good | Fast |
| **Adaptability** | Natural ✅ | Natural ✅ | Needs retraining |
| **Setup Time** | 1 minute ✅ | 2 minutes | Hours |

## Features

### 🎯 Intelligent Decision Making
Gemini considers:
- Technical setup quality
- Entry point timing
- Risk/reward ratio
- Market conditions
- Confidence level

### 📝 Transparent Reasoning
See exactly why Gemini:
- Recommends BUY or HOLD
- Assesses risk level
- Chooses confidence score
- Identifies key factors

### 🛡️ Risk Management
Gemini is conservative:
- Only trades with clear setups
- Considers downside risk
- Explains concerns
- Recommends stop losses

### 💬 Natural Language
Gemini explains in plain English:
- Technical analysis
- Market context
- Risk factors
- Trading rationale

## Advanced Usage

### Custom Analysis

```python
from gemini_agent import GeminiTrader

gemini = GeminiTrader()
decision = gemini.analyze_and_decide(
    symbol='AAPL',
    technical_data=indicators,
    market_context=context
)

print(f"Action: {decision['action']}")
print(f"Confidence: {decision['confidence']:.0%}")
print(f"Reasoning: {decision['reasoning']}")
```

### Portfolio Review

```python
advice = gemini.get_portfolio_advice(
    current_positions=positions,
    market_data=market_context
)
print(advice['advice'])
```

### Multi-Timeframe

```python
# Daily analysis
daily_decision = gemini.analyze_and_decide(symbol, daily_data)

# Hourly confirmation
hourly_decision = gemini.analyze_and_decide(symbol, hourly_data)

# Trade only if both agree
if daily_decision['action'] == 'buy' and hourly_decision['action'] == 'buy':
    place_trade()
```

## Best Practices

### 1. Start Conservative
```bash
GEMINI_MIN_CONFIDENCE=0.8  # Only very confident trades
MAX_POSITION_SIZE=0.05     # 5% per position
```

### 2. Learn from Gemini
- Read its reasoning
- Understand its analysis
- See what it considers
- Improve your own trading

### 3. Monitor Performance
```bash
# Check logs
tail -f logs/trading_bot.log

# Review decisions
grep "Gemini's Decision" logs/trading_bot.log
```

### 4. Optimize Check Interval
```python
# Active: Every 5 minutes
check_interval=300

# Moderate: Every 15 minutes
check_interval=900

# Conservative: Every hour
check_interval=3600
```

## Troubleshooting

### "API key not set"
```bash
# Get key at: https://aistudio.google.com/apikey
# Add to .env:
GEMINI_API_KEY=your_actual_key_here
```

### Gemini not trading
- Lower `GEMINI_MIN_CONFIDENCE` (try 0.6)
- Check if market is open
- Review Gemini's reasoning (it might see risks)

### Rate limit errors
- Reduce check frequency
- Trade fewer stocks
- Upgrade to paid tier (still cheap!)

### API errors
- Check internet connection
- Verify API key is correct
- Check Google AI Studio status

## Cost Comparison

### Daily Trading Costs

| Service | Checks/Day | Cost/Day | Cost/Month |
|---------|-----------|----------|------------|
| **Gemini Free** | 78 | $0 | **$0** ✅ |
| Gemini Paid | 500 | ~$0.50 | ~$15 |
| Claude | 78 | ~$10 | ~$300 |
| ML Model | Unlimited | $0 | $0 |

**Gemini = Best of both worlds!** Free like ML, smart like Claude 🎉

## Why Gemini is Perfect for Trading

### 1. **Free Tier is Generous**
- 1,500 requests/day is more than enough
- Trade all day without paying
- Perfect for paper trading and learning

### 2. **Fast Responses**
- Gemini 2.0 Flash is lightning quick
- Get decisions in 1-2 seconds
- No waiting around

### 3. **Smart Analysis**
- Understands financial markets
- Considers context
- Explains reasoning clearly

### 4. **Conservative by Default**
- Won't chase risky trades
- Considers downside
- Protects your capital

### 5. **Easy to Use**
- Get API key in 30 seconds
- No training needed
- Start trading immediately

## Example Gemini Reasoning

Here's a real example of Gemini's analysis:

```
🤖 Gemini's Decision for NVDA:
Action: BUY
Confidence: 78%
Risk Level: medium

Reasoning:
"NVDA shows a compelling technical setup for entry:

Bullish Signals:
1. RSI at 41 - oversold but recovering, room to run upward
2. MACD histogram just turned positive - early bullish reversal
3. Price bounced cleanly off 200-day SMA at $138, now at $142
4. Volume increased 40% on the bounce - institutional buying
5. Bollinger Band squeeze suggests volatility expansion coming

Market Context:
- VIX at 18 (neutral) - not excessive fear
- SPY up 0.4% today - market supportive
- Tech sector showing relative strength

Risk Management:
- Entry at $142 provides good risk/reward
- Stop loss at $139 (2.1% risk) protects downside
- Take profit at $149 (4.9% gain) hits resistance
- Risk/reward ratio of 2.3:1 is favorable

Concerns:
- Semiconductor sector has been choppy
- Earnings announcement in 3 weeks could bring volatility
- High beta stock means larger price swings

Recommendation: BUY with 60-70% of max position size to account
for volatility. The technical setup is strong with defined risk."
```

## Next Steps

1. ✅ **Get Gemini API key** (https://aistudio.google.com/apikey)
2. ✅ **Add to .env file**
3. ✅ **Run**: `python run_gemini_bot.py`
4. ✅ **Watch Gemini analyze and trade**
5. ✅ **Learn from its reasoning**
6. ✅ **Adjust confidence thresholds**
7. ✅ **Scale up gradually**

## FAQ

**Q: Is Gemini really free?**
A: Yes! 1,500 requests/day for free. More than enough for trading.

**Q: Is Gemini better than ML models?**
A: Different! Gemini reasons and explains. ML just predicts. Try both!

**Q: How much does it cost if I exceed free tier?**
A: Still very cheap! ~$0.075 per 1M tokens. Way less than Claude.

**Q: Can Gemini guarantee profits?**
A: No! Gemini is smart but markets are unpredictable. Always use risk management.

**Q: What if Gemini makes a bad call?**
A: Stop-losses protect you. Gemini is conservative and manages risk.

**Q: Can I use Gemini + ML together?**
A: Yes! Use ML for quick screens, Gemini for final analysis.

**Q: Does Gemini work for crypto?**
A: Yes, if you have a crypto exchange API!

**Q: How often should I check?**
A: Every 5-15 minutes is good. Gemini is fast enough for frequent checks.

---

**Welcome to AI-powered trading with Google Gemini!** 🤖📈🚀

**Best of all: IT'S FREE!** 🎉
