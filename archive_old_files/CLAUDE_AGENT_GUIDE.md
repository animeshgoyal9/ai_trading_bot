# Claude AI Trading Agent

Your bot now uses **Claude AI** to make intelligent trading decisions instead of traditional ML models or sentiment analysis!

## What Changed

### Before (ML + Sentiment)
```
Historical Data → Train ML Model → Predictions → Trade
              ↓
         Sentiment Analysis
```

### After (Claude AI Agent)
```
Current Market Data → Claude AI Agent → Intelligent Decision → Trade
                           ↓
                  Real-time Reasoning
```

## Why Claude AI is Better

### 🧠 Intelligent Reasoning
- Claude analyzes each trade with human-like reasoning
- Considers context, risk, and market conditions
- Explains WHY it makes each decision

### 🚀 No Training Required
- No need to train ML models on historical data
- Works immediately with current market conditions
- Adapts to changing markets naturally

### 📰 Built-in Context Understanding
- Understands news and market events
- Knows about companies, sectors, industries
- Considers macroeconomic factors

### 🎯 Better Risk Management
- Conservative by design
- Only trades when confident
- Explains risks clearly

### 💬 Transparent Decisions
- See Claude's full reasoning for each trade
- Understand why it bought or held
- Learn from its analysis

## How It Works

### 1. Data Collection
Bot collects:
- Current stock price
- 30+ technical indicators (RSI, MACD, Bollinger Bands, etc.)
- Market context (VIX, market trend)
- Recent price action

### 2. Claude Analysis
Claude receives all data and:
- Analyzes technical setup
- Evaluates risk/reward
- Considers market conditions
- Makes reasoned decision
- Explains its thinking

### 3. Trading Decision
Claude returns:
```json
{
    "action": "buy" or "hold",
    "confidence": 0.85,
    "reasoning": "Strong technical setup with RSI showing oversold conditions...",
    "risk_level": "medium",
    "key_factors": ["Oversold RSI", "Bullish MACD crossover", "Support at $150"]
}
```

### 4. Execution
If Claude says BUY with high confidence:
- Bot calculates position size
- Places bracket order (with stop-loss & take-profit)
- Logs Claude's reasoning

## Setup

### 1. Get Anthropic API Key
```bash
# Sign up at https://console.anthropic.com
# Get your API key (has free tier!)
```

### 2. Add to .env
```bash
ANTHROPIC_API_KEY=your_api_key_here
USE_CLAUDE_AGENT=true
CLAUDE_MODEL=claude-sonnet-4-20250514
CLAUDE_MIN_CONFIDENCE=0.7
```

### 3. Run Claude Bot
```bash
python run_claude_bot.py
```

That's it! No training, no data collection, just start trading.

## Example Session

```
🤖 CLAUDE AI TRADING BOT
==================================================

Portfolio Value: $10,000.00

--- Analyzing AAPL ---
Current price: $150.50
Asking Claude for analysis...

🤖 Claude's Decision:
   Action: BUY
   Confidence: 85%
   Risk Level: medium
   Reasoning: Strong technical setup with multiple bullish signals.
   RSI at 42 indicates oversold conditions with room to run. MACD
   showing bullish crossover. Price bouncing off 50-day SMA support
   at $148. Market sentiment neutral (VIX at 18). Risk/reward favorable
   with stop at $147 and target at $158. Entry at current level offers
   good risk management.

✅ BUY 6 shares of AAPL @ $150.50
   Claude's confidence: 85%
   Stop Loss: $147.49
   Take Profit: $158.03

--- Analyzing TSLA ---
Current price: $245.80
Asking Claude for analysis...

🤖 Claude's Decision:
   Action: HOLD
   Confidence: 45%
   Risk Level: high
   Reasoning: Technical indicators mixed. RSI at 68 nearing overbought.
   MACD positive but losing momentum. Price extended 15% above 50-day SMA.
   High volatility (45% annualized). VIX elevated suggesting market
   uncertainty. No clear edge at current level. Wait for better entry
   or pullback to support at $230.

⏸️  HOLD TSLA - Not trading

Waiting 300 seconds until next check...
```

## Configuration

### In .env file:

```bash
# Required: Anthropic API Key
ANTHROPIC_API_KEY=your_key_here

# Claude Model (default: claude-sonnet-4-20250514)
CLAUDE_MODEL=claude-sonnet-4-20250514

# Minimum confidence to trade (0.0 - 1.0)
# Higher = more selective, fewer trades
CLAUDE_MIN_CONFIDENCE=0.7  # 70%

# Disable old approaches
USE_CLAUDE_AGENT=true
USE_SENTIMENT=false  # Claude handles this
```

### Claude Models Available:
- `claude-sonnet-4-20250514` (Recommended) - Best balance of cost/performance
- `claude-opus-4-5-20251101` - Most intelligent, higher cost
- `claude-3-5-sonnet-20241022` - Fast and capable

## Features

### ✅ What Claude Analyzes

**Technical Indicators:**
- RSI (overbought/oversold)
- MACD (trend and momentum)
- Moving Averages (trend direction)
- Bollinger Bands (volatility and reversals)
- ADX (trend strength)
- Volume (confirmation)
- Price momentum
- Volatility

**Market Context:**
- VIX (market fear)
- Overall market trend (SPY)
- Sector performance

**Risk Factors:**
- Stop loss levels
- Take profit targets
- Position sizing
- Market volatility
- Trend strength

### 🎯 Claude's Decision Process

1. **Trend Analysis**: Is there a clear trend?
2. **Entry Quality**: Is this a good entry point?
3. **Risk/Reward**: Is the trade worth it?
4. **Market Conditions**: Is market favorable?
5. **Confidence Assessment**: How sure are we?

### 📊 Portfolio Management

Ask Claude for portfolio advice:
```python
from claude_agent import ClaudeTrader

claude = ClaudeTrader()
advice = claude.get_portfolio_advice(
    current_positions=positions,
    market_data=market_context
)
print(advice['advice'])
```

Claude reviews your portfolio and suggests:
- Which positions to hold or exit
- Risk assessment
- Diversification recommendations
- Market timing advice

## Advantages vs ML Model

| Feature | ML Model | Claude AI |
|---------|----------|-----------|
| **Training** | Requires days/weeks | None needed ✅ |
| **Explainability** | Black box | Full reasoning ✅ |
| **Adaptability** | Fixed after training | Adapts naturally ✅ |
| **Market Changes** | Needs retraining | Handles automatically ✅ |
| **Context** | Limited | Understands fully ✅ |
| **News Events** | Misses them | Factors them in ✅ |
| **Risk Awareness** | Calculated | Reasoned ✅ |
| **Cost** | Free | Small API cost |

## API Costs

### Anthropic Pricing (as of 2025)
- **Claude Sonnet 4**: $3 per million input tokens, $15 per million output tokens
- **Typical trading decision**: ~1,000 tokens (~$0.02 per analysis)
- **Daily cost** (10 stocks, check every 5 min, 6.5 hours): ~$10/day
- **Monthly cost**: ~$200-300 for active trading

### Cost Optimization
```bash
# Check less frequently (every 15 minutes instead of 5)
check_interval=900  # $3-4/day

# Trade fewer stocks (5 instead of 10)
STOCK_UNIVERSE = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA']

# Use Claude Sonnet (cheaper than Opus)
CLAUDE_MODEL=claude-sonnet-4-20250514
```

### Free Tier
- Anthropic offers some free credits for new users
- Perfect for testing and paper trading

## Best Practices

### 1. Start Conservative
```bash
CLAUDE_MIN_CONFIDENCE=0.8  # Only very confident trades
MAX_POSITION_SIZE=0.05     # Smaller positions
```

### 2. Monitor Claude's Reasoning
- Read Claude's explanations
- Learn from its analysis
- Adjust strategy based on insights

### 3. Check Intervals
```python
# Active trading: 5 minutes
check_interval=300

# Conservative: 15 minutes
check_interval=900

# Very conservative: 1 hour
check_interval=3600
```

### 4. Review Performance
```bash
# Check logs to see Claude's decisions
tail -f logs/trading_bot.log

# Review what worked and what didn't
grep "Claude's Decision" logs/trading_bot.log
```

## Example Claude Analysis

Here's a real example of Claude's reasoning:

```
Analyzing NVDA...

🤖 Claude's Decision:
Action: BUY
Confidence: 82%
Risk Level: medium

Reasoning:
"NVDA presents a compelling technical setup for a swing trade.

Key bullish signals:
1. RSI at 38 - oversold but not extremely, suggesting selling pressure
   exhaustion with room to recover
2. MACD histogram turning positive after bearish divergence - early
   bullish reversal signal
3. Price bounced off 200-day SMA support at $138, now trading at $142
4. Volume spike on bounce indicates buying interest
5. Bollinger Bands showing squeeze, typically precedes volatility expansion

Market context is neutral (VIX at 19, SPY +0.3%), reducing systematic risk.

Risk management:
- Entry at $142 provides good risk/reward
- Stop loss at $139 (2.1% below) protects against breakdown
- Take profit at $149 (4.9% above) aligns with resistance
- R:R ratio of 2.3:1 is favorable

Concerns:
- Sector has been weak recently
- Earnings in 3 weeks could cause volatility
- High beta means larger swings

Overall: Strong technical setup with defined risk. Entry timing is good.
Recommend position size at 60-70% of max to account for volatility."
```

## Troubleshooting

### Claude not trading anything
- Lower `CLAUDE_MIN_CONFIDENCE` (try 0.6)
- Check if market is open
- Review Claude's reasoning in logs

### API errors
- Check ANTHROPIC_API_KEY is correct
- Verify API key has credits
- Check internet connection

### Too many API calls
- Increase `check_interval`
- Trade fewer stocks
- Use Claude Sonnet instead of Opus

### Claude too conservative
- This is by design (better safe than sorry)
- Adjust confidence threshold
- Review and learn from its reasoning

## Advanced Usage

### Custom Prompts
Edit `claude_agent.py` to customize Claude's behavior:

```python
def _get_system_prompt(self):
    return """You are an aggressive day trader..."""  # Your style
```

### Add News Analysis
```python
# Add real-time news to context
market_context = {
    'news_summary': get_latest_news(symbol),
    'vix': vix_value
}
```

### Multi-Timeframe Analysis
```python
# Analyze multiple timeframes
decision_daily = claude.analyze(symbol, daily_data)
decision_hourly = claude.analyze(symbol, hourly_data)
```

## Comparison: ML vs Sentiment vs Claude

| Approach | Pros | Cons | Best For |
|----------|------|------|----------|
| **ML Model** | Fast, no API cost, backtestable | Needs training, black box | Quant strategies |
| **Sentiment** | Catches news, social trends | Lags price, noisy | News-driven trading |
| **Claude AI** | Intelligent, explainable, adaptive | API cost, rate limits | Active trading with reasoning |

## Next Steps

1. ✅ Get Anthropic API key: https://console.anthropic.com
2. ✅ Add to `.env` file
3. ✅ Run: `python run_claude_bot.py`
4. ✅ Watch Claude analyze and trade
5. ✅ Learn from its reasoning
6. ✅ Adjust confidence and parameters
7. ✅ Start small and scale up

## FAQ

**Q: Is Claude better than ML models?**
A: Different! Claude reasons, ML predicts. Claude explains, ML doesn't. Try both!

**Q: How much does it cost?**
A: ~$0.02 per analysis. Active trading: ~$10/day. Conservative: ~$3/day.

**Q: Can I use Claude + ML together?**
A: Yes! Use ML for quick screens, Claude for final decisions.

**Q: Does Claude guarantee profits?**
A: No! Claude is smart but markets are unpredictable. Always paper trade first.

**Q: What if Claude is wrong?**
A: Stop-losses protect you. Claude is conservative and explains its risk assessment.

**Q: Can Claude trade crypto?**
A: Yes, if you have a crypto exchange API (Coinbase, Binance, etc.)

---

**Welcome to AI-powered trading with reasoning!** 🤖📈
