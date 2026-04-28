# Stock Screener - Usage Guide

## What It Does
Analyzes your 12 portfolio stocks using Claude AI and shows you only the **high-confidence BUY opportunities**.

**Your Portfolio:**
- GLD, SNDK, LITE, AVGO, NVDA, MP, RKLB, USAR, APLD, IREN, UUUU, AAPL

## Quick Start

### Basic Usage (70% confidence threshold)
```bash
cd /Users/animeshgoyal/Downloads/ai_trading_bot
source trading/bin/activate
python nasdaq_screener.py
```

### Only Show "Sure Shot" Buys (80%+ confidence)
```bash
python nasdaq_screener.py --confidence 0.80
```

### Ultra Conservative (90%+ confidence)
```bash
python nasdaq_screener.py --confidence 0.90
```

## Parameters

- `--confidence` : Minimum confidence threshold (0.60 = 60%, 0.80 = 80%, etc.)
  - Default: 0.70 (70%)
  - Recommended for "sure shots": 0.80 or higher

## Output

The screener will:
1. Show live progress for each of your 12 stocks
2. Display BUY/HOLD decision in real-time as it analyzes
3. Show final summary with only high-confidence buys
4. Save detailed results to `logs/screen_results_TIMESTAMP.txt`

## Example Output

```
🔎 Analyzing stocks...

   [1/12] Analyzing GLD... ⏸️  HOLD (65%)
   [2/12] Analyzing SNDK... 🎯 BUY @ $89.50 (Confidence: 82%)
   [3/12] Analyzing LITE... ⏸️  BUY but low confidence (55%)
   [4/12] Analyzing NVDA... 🎯 BUY @ $135.50 (Confidence: 85%)
   ...

📊 SCREENING RESULTS
Stocks Analyzed: 12
Buy Opportunities Found: 2

🎯 BUY OPPORTUNITIES (Confidence >= 70%)

1. NVDA @ $135.50
   Confidence: 85% | Risk: medium
   Reasoning: Strong momentum with RSI at 58, MACD bullish crossover...
   💰 Suggested Position: 7 shares ($948.50)

2. SNDK @ $89.50
   Confidence: 82% | Risk: low
   Reasoning: Oversold on RSI (32), approaching support level...
   💰 Suggested Position: 11 shares ($984.50)
```

## Tips

- **For sure shots**: Use `--confidence 0.80` or higher
- **Market hours**: Best results during market hours (9:30 AM - 4:00 PM ET)
- **Cost**: Analyzes 12 stocks = ~$0.24 in Claude API costs

## What Happens Next?

The screener only SHOWS opportunities - it doesn't trade automatically.

To actually trade the recommendations, you have two options:

### Option 1: Use the regular bot to trade all recommendations
The regular bot ([run_claude_bot_once.py](run_claude_bot_once.py)) will analyze and trade all your stocks automatically.

### Option 2: Manual trading
Review the reasoning and manually place trades through your broker.

