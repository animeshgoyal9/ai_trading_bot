# Understanding Stock Price Differences

## Why You See Different Prices

When you're seeing different "real-time" prices for stocks across different sources, here's why:

### 1. **Data Source**
- **Yahoo Finance / Google / CNBC**: Use consolidated market data from exchanges
- **Alpaca (Trading Bot)**: Uses IEX (Investors Exchange) real-time data
- **Broker Apps**: Use their own data feeds

### 2. **Bid vs Ask vs Last Trade**
Different sources show different price types:

| Source | Price Shown | What It Means |
|--------|-------------|---------------|
| Yahoo Finance | Last Trade | Price of the most recent transaction |
| Google Finance | Mid-price | Average of bid and ask |
| Alpaca API | Bid/Ask | What buyers/sellers are offering |
| Trading Bot | Last Trade | Actual execution price |

**Example:**
- NVDA Bid: $122.50
- NVDA Ask: $122.52
- NVDA Last: $122.51
- **Different sources show different prices!**

### 3. **Market vs Extended Hours**
- **Regular Hours (9:30 AM - 4:00 PM ET)**: Most active, tightest spreads
- **Pre-Market (4:00 AM - 9:30 AM ET)**: Less liquidity, wider spreads
- **After-Hours (4:00 PM - 8:00 PM ET)**: Limited trading, different prices

### 4. **Data Delays**
- **Real-time**: Updated instantly (requires subscription)
- **15-minute delay**: Free data from most websites
- **End-of-day**: Only closing prices

### 5. **Exchange Differences**
Stocks trade on multiple exchanges simultaneously:
- **NYSE**: New York Stock Exchange
- **NASDAQ**: Electronic exchange
- **IEX**: Investors Exchange (what Alpaca uses)
- **ARCA**: NYSE Arca (ETFs like GLD)

Same stock, slightly different prices on each exchange!

## What The Trading Bot Sees

The bot uses **Alpaca's IEX data feed** which provides:
- ✅ Real-time prices (no delay)
- ✅ Actual tradeable quotes
- ✅ Bid/ask spreads
- ✅ Latest executed trades

When the bot makes a decision:
1. It gets the **last trade price** from IEX
2. It analyzes technical indicators using historical data
3. It places a **market order** which executes at the current **ask price**

## Why This Matters for Trading

### Example Trade Scenario:

**What you see on Yahoo Finance:**
- AAPL: $227.50 (last trade from NYSE)

**What the bot sees on Alpaca (IEX):**
- AAPL Bid: $227.48 (what buyers will pay)
- AAPL Ask: $227.52 (what sellers want)
- AAPL Last: $227.51 (most recent IEX trade)

**When bot places market BUY order:**
- Executes at: $227.52 (current ask price)
- You paid: $0.02 more than the "last" price

This is **normal** and called **slippage**!

## Price Discrepancy Examples

### Small Discrepancies (Normal)
```
Stock: NVDA
Yahoo: $122.50
Alpaca: $122.52
Difference: $0.02 (0.016%)
```
**Cause**: Different exchanges, bid/ask spread
**Impact**: Minimal - just normal market behavior

### Large Discrepancies (Check These)
```
Stock: LITE
Yahoo: $55.25
Alpaca: $56.10
Difference: $0.85 (1.5%)
```
**Cause**: Could be:
- Stale data (15-min delay on Yahoo)
- After-hours vs regular hours
- News event causing rapid price movement
- Wrong symbol or data error

## How To Check Prices When Bot Runs

### When NOT on Corporate Network:

**Check Alpaca prices:**
```bash
python check_prices.py
```

**Check Yahoo Finance prices:**
```bash
python check_yahoo_prices.py
```

**Compare side-by-side:**
Both scripts show:
- Current price
- Bid/ask spread
- Last trade time
- Change from previous close

### On Corporate Network:

Use external websites:
- https://finance.yahoo.com
- https://www.google.com/finance
- https://www.tradingview.com

## What To Do About Price Differences

### ✅ Normal - No Action Needed:
- Differences < 0.1% ($0.10 on a $100 stock)
- Consistent across all stocks
- Within bid/ask spread

### ⚠️ Review - Check Before Trading:
- Differences > 0.5% ($0.50 on a $100 stock)
- Only on one or two stocks
- Different from recent historical prices

### ❌ Problem - Don't Trade:
- Differences > 2% ($2.00 on a $100 stock)
- Prices seem frozen or stale
- Bot shows error messages

## Technical Details

### The Bot's Data Flow:

```
1. Alpaca API (IEX)
   ↓
2. Get last 100 days of daily prices
   ↓
3. Calculate technical indicators (RSI, MACD, etc.)
   ↓
4. Claude analyzes current price + indicators
   ↓
5. Place order at current market price
```

### Price Components:

**Market Order (what the bot uses):**
- Executes immediately
- At current ask price (buy) or bid price (sell)
- Small slippage expected

**Limit Order (more control):**
- Executes only at your specified price
- Might not fill if price moves away
- No slippage

## Summary

🔍 **You're seeing different prices because:**
1. Different data sources (IEX vs NYSE vs NASDAQ)
2. Bid/ask spreads
3. Timing differences
4. 15-minute delays on free data

📊 **The bot uses real-time IEX data:**
- No delay
- Actual tradeable prices
- Bid/ask spreads included

✅ **This is normal and expected:**
- Price differences < 0.1% are typical
- The bot executes at real market prices
- Slippage is factored into risk management

💡 **Bottom line:**
The bot trades at **actual market prices**, not the "last trade" prices you see on most websites. Small differences are normal and expected in live trading!

## When Bot Runs Tomorrow

When the bot runs at 9 AM and you want to verify prices:
1. Check logs: `tail -f logs/scheduled_bot.log`
2. Look for lines like: `Current price: $122.50`
3. Compare to Yahoo Finance at the same time
4. Expect 0-0.2% difference (normal)

If you see large discrepancies (>1%), the bot has safety features:
- Won't trade during extreme volatility
- Claude analyzes risk level
- Bracket orders limit losses
