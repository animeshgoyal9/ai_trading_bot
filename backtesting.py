"""
Backtesting Engine for Claude AI Trading Bot
Simulates the bot's strategy using the same technical indicators
WITHOUT calling Claude API (saves money, runs instantly)

Usage:
    python3 backtest.py                     # Backtest all stocks
    python3 backtest.py --symbol NVDA       # Backtest single stock
    python3 backtest.py --start 2022-01-01  # Custom start date
    python3 backtest.py --confidence 0.75   # Higher confidence threshold
"""

import pandas as pd
import numpy as np
import argparse
import json
import time
import requests
from datetime import datetime, timedelta
from ta.trend import SMAIndicator, EMAIndicator, MACD, ADXIndicator
from ta.momentum import RSIIndicator
from ta.volatility import BollingerBands, AverageTrueRange
import alpaca_trade_api as tradeapi
from dotenv import load_dotenv
import os
load_dotenv()

_api = tradeapi.REST(
    os.getenv('ALPACA_API_KEY'),
    os.getenv('ALPACA_SECRET_KEY'),
    os.getenv('ALPACA_BASE_URL', 'https://paper-api.alpaca.markets'),
    api_version='v2'
)

def fetch_stock_data(symbol, start, end):
    """Fetch daily bars from Alpaca for stocks."""
    try:
        bars = _api.get_bars(symbol, '1Day',
                             start=start + 'T00:00:00Z',
                             end=end + 'T00:00:00Z').df
        if bars.empty:
            return None
        if isinstance(bars.index, pd.MultiIndex):
            bars = bars.xs(symbol, level='symbol')
        bars.columns = bars.columns.str.lower()
        bars.index.name = 'date'
        return bars
    except Exception as e:
        print(f"  Error fetching {symbol}: {e}")
        return None

def fetch_crypto_data(symbol, start, end):
    """Fetch daily bars from Alpaca for crypto (e.g. BTC/USD)."""
    try:
        bars = _api.get_crypto_bars([symbol], '1Day',
                                    start=start + 'T00:00:00Z',
                                    end=end + 'T00:00:00Z')
        rows = [{'date': b.t, 'open': b.o, 'high': b.h,
                 'low': b.l, 'close': b.c, 'volume': b.v}
                for b in bars]
        if not rows:
            return None
        df = pd.DataFrame(rows).set_index('date')
        df.index.name = 'date'
        return df
    except Exception as e:
        print(f"  Error fetching {symbol}: {e}")
        return None


# ─────────────────────────────────────────────
# CONFIGURATION (mirrors your config.py)
# ─────────────────────────────────────────────
STOCK_UNIVERSE = [
    'LITE', 'LASR', 'COHR', 'AAOI', 'LPTH', 'LWLG', 'FN',
    'ALAB', 'ANET', 'NVDA', 'TSM', 'AVGO', 'MU', 'AMD', 'INTC', 'TXN',
    'MRVL', 'CRDO', 'AMKR', 'PLAB', 'AXTI', 'AOSL', 'AEHR', 'POET', 'SKYT', 'CAMT',
    'VRT', 'PLTR', 'APP', 'NBIS', 'CRWV', 'DELL', 'ORCL', 'HPE', 'GLW', 'CIEN', 'APH',
    'IONQ', 'QBTS', 'ARQQ',
    'SERV', 'RCAT', 'BKSY', 'ASTS', 'RKLB', 'OUST', 'VWAV',
    'BE',
    'CCJ', 'UUUU', 'NXE', 'UEC', 'LEU',
    'SNDK', 'STX', 'WDC',
    'AG', 'GLD', 'COPX', 'MP', 'TMC', 'WCP',
    'APLD', 'CORZ', 'CIFR', 'WULF', 'IREN', 'CRML',
    'USAR', 'WWR', 'ONDS', 'OKLL', 'NUAI', 'BBAI', 'RXRX', 'LAES',
    'STRL', 'EME', 'ETN', 'PWR', 'JBL',
    'QQQ', 'SPY', 'AAPL',
]
CRYPTO_UNIVERSE = ['BTC/USD', 'ETH/USD']

TRADING_CAPITAL     = 10_000
MAX_POSITION_SIZE   = 0.10   # 10% per trade
STOP_LOSS_PCT       = 0.05   # 5%
TAKE_PROFIT_PCT     = 0.10   # 10%
MIN_CONFIDENCE      = 0.70   # Minimum signal confidence to trade
COMMISSION_PER_SIDE = 0.00   # Alpaca charges $0 commission
AGGRESSIVE          = False  # set via --aggressive flag


# ─────────────────────────────────────────────
# TECHNICAL INDICATORS
# ─────────────────────────────────────────────
def add_indicators(df):
    """Add the same indicators your bot uses"""
    df = df.copy()
    df.columns = df.columns.str.lower()

    # Returns
    df['returns'] = df['close'].pct_change()

    # Trend
    df['sma_fast'] = SMAIndicator(df['close'], window=10).sma_indicator()
    df['sma_slow'] = SMAIndicator(df['close'], window=30).sma_indicator()
    df['sma_50']   = SMAIndicator(df['close'], window=50).sma_indicator()
    df['sma_60']   = SMAIndicator(df['close'], window=60).sma_indicator()
    df['sma_200']  = SMAIndicator(df['close'], window=200).sma_indicator()
    macd = MACD(df['close'], window_fast=12, window_slow=26, window_sign=9)
    df['macd']        = macd.macd()
    df['macd_signal'] = macd.macd_signal()
    df['macd_diff']   = macd.macd_diff()
    df['adx']         = ADXIndicator(df['high'], df['low'], df['close'], window=14).adx()

    # Momentum
    df['rsi'] = RSIIndicator(df['close'], window=14).rsi()

    # Volatility
    bb = BollingerBands(df['close'], window=20, window_dev=2)
    df['bb_upper']    = bb.bollinger_hband()
    df['bb_lower']    = bb.bollinger_lband()
    df['bb_position'] = (df['close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'])
    df['atr']         = AverageTrueRange(df['high'], df['low'], df['close'], window=14).average_true_range()

    # Volume
    df['volume_sma']   = df['volume'].rolling(20).mean()
    df['volume_ratio'] = df['volume'] / df['volume_sma']

    return df.dropna()


# ─────────────────────────────────────────────
# EARNINGS — yfinance (always-on for stocks)
# ─────────────────────────────────────────────
import yfinance as yf

_yf_earnings_cache = {}   # symbol → DataFrame of quarterly earnings

def fetch_yf_earnings(symbol):
    """Return quarterly earnings history for a stock via yfinance.
    Columns: date (index), epsEstimate, epsActual, surprisePercent
    Returns empty DataFrame if unavailable (e.g. crypto)."""
    if '/' in symbol:          # crypto — no earnings
        return pd.DataFrame()
    if symbol in _yf_earnings_cache:
        return _yf_earnings_cache[symbol]
    try:
        hist = yf.Ticker(symbol).earnings_history
        if hist is None or hist.empty:
            _yf_earnings_cache[symbol] = pd.DataFrame()
            return pd.DataFrame()
        hist = hist.copy()
        hist.index = pd.to_datetime(hist.index)
        hist = hist.sort_index()
        # Normalise column names
        hist.columns = [c.lower().replace(' ', '_') for c in hist.columns]
        _yf_earnings_cache[symbol] = hist
        return hist
    except Exception as e:
        print(f"  [earnings] yfinance error for {symbol}: {e}")
        _yf_earnings_cache[symbol] = pd.DataFrame()
        return pd.DataFrame()


def add_earnings_signals(df, symbol):
    """Add per-row earnings columns to df:
      earnings_surprise_last  — surprise % of most recent past earnings (NaN if none)
      earnings_beat_streak    — consecutive beats (positive) or misses (negative) up to this date
      days_to_earnings        — calendar days until next known earnings date (NaN if unknown)
      pre_earnings_window     — 1 if earnings is 3-14 days away, else 0
    """
    df = df.copy()
    df['earnings_surprise_last'] = np.nan
    df['earnings_beat_streak']   = 0
    df['days_to_earnings']       = np.nan
    df['pre_earnings_window']    = 0

    hist = fetch_yf_earnings(symbol)
    if hist.empty:
        return df

    surprise_col = next((c for c in hist.columns if 'surprise' in c), None)
    if surprise_col is None:
        return df

    dates = hist.index.normalize()

    for i, idx in enumerate(df.index):
        trade_date = pd.Timestamp(idx).normalize()

        # ── Past earnings: most recent before trade_date ──
        past = hist[dates < trade_date]
        if not past.empty:
            last_surprise = float(past[surprise_col].iloc[-1])
            df.at[idx, 'earnings_surprise_last'] = last_surprise

            # Beat streak: count consecutive beats/misses from most recent backwards
            surprises = past[surprise_col].dropna().tolist()[::-1]  # most recent first
            streak = 0
            for s in surprises:
                if s > 0:
                    if streak >= 0:
                        streak += 1
                    else:
                        break
                elif s < 0:
                    if streak <= 0:
                        streak -= 1
                    else:
                        break
                else:
                    break
            df.at[idx, 'earnings_beat_streak'] = streak

        # ── Future earnings: next known date after trade_date ──
        future = hist[dates > trade_date]
        if not future.empty:
            next_date = future.index[0].normalize()
            days_away = (next_date - trade_date).days
            df.at[idx, 'days_to_earnings'] = days_away
            if 3 <= days_away <= 14:
                df.at[idx, 'pre_earnings_window'] = 1

    return df


# ─────────────────────────────────────────────
# EARNINGS + NEWS (Alpha Vantage) — Enhanced mode
# ─────────────────────────────────────────────
ENHANCED        = False   # set via --enhanced flag
AV_KEY          = os.getenv('ALPHA_VANTAGE_KEY', '')
_earnings_cache = {}      # symbol → list of earnings dicts
_news_cache     = {}      # symbol → list of news dicts
_av_call_count  = 0
_AV_RATE_LIMIT  = 25      # free tier: 25/day, ~5/min

def _av_get(params):
    """Call Alpha Vantage API with basic rate limiting."""
    global _av_call_count
    _av_call_count += 1
    if _av_call_count % 5 == 0:
        time.sleep(12)   # stay under 5 req/min limit
    params['apikey'] = AV_KEY
    try:
        r = requests.get('https://www.alphavantage.co/query', params=params, timeout=10)
        return r.json()
    except Exception as e:
        print(f"  AV API error: {e}")
        return {}

def fetch_earnings(symbol):
    """Fetch historical earnings (EPS estimate vs actual) from Alpha Vantage.
    Returns list of dicts: {date, estimated_eps, reported_eps, surprise_pct}
    Cached per symbol so we only fetch once per run."""
    if symbol in _earnings_cache:
        return _earnings_cache[symbol]
    data = _av_get({'function': 'EARNINGS', 'symbol': symbol})
    records = []
    for q in data.get('quarterlyEarnings', []):
        try:
            reported  = float(q.get('reportedEPS', 0) or 0)
            estimated = float(q.get('estimatedEPS', 0) or 0)
            surprise  = float(q.get('surprisePercentage', 0) or 0)
            date_str  = q.get('reportedDate') or q.get('fiscalDateEnding', '')
            if date_str:
                records.append({
                    'date':         datetime.strptime(date_str, '%Y-%m-%d').date(),
                    'reported_eps': reported,
                    'estimated_eps': estimated,
                    'surprise_pct': surprise,
                })
        except Exception:
            continue
    _earnings_cache[symbol] = records
    return records

def fetch_news_sentiment(symbol):
    """Fetch news sentiment scores from Alpha Vantage.
    Returns list of dicts: {date, sentiment_score, relevance}
    Cached per symbol."""
    if symbol in _news_cache:
        return _news_cache[symbol]
    data = _av_get({
        'function': 'NEWS_SENTIMENT',
        'tickers':  symbol,
        'limit':    200,
        'sort':     'EARLIEST',
    })
    records = []
    for item in data.get('feed', []):
        try:
            ts = item.get('time_published', '')[:8]   # YYYYMMDD
            date = datetime.strptime(ts, '%Y%m%d').date()
            # Find this ticker's sentiment in the ticker_sentiments list
            for ts_entry in item.get('ticker_sentiment', []):
                if ts_entry.get('ticker', '').upper() == symbol.upper():
                    score     = float(ts_entry.get('ticker_sentiment_score', 0))
                    relevance = float(ts_entry.get('relevance_score', 0))
                    records.append({'date': date, 'sentiment': score, 'relevance': relevance})
                    break
        except Exception:
            continue
    _news_cache[symbol] = records
    return records

def get_earnings_adjustment(symbol, trade_date):
    """Return a confidence adjustment [-0.3, +0.2] based on the most
    recent earnings report before trade_date."""
    if not ENHANCED:
        return 0.0
    earnings = fetch_earnings(symbol)
    if not earnings:
        return 0.0
    td = trade_date.date() if hasattr(trade_date, 'date') else trade_date
    # Find the most recent earnings before this trade date (within 60 days)
    recent = [e for e in earnings if e['date'] <= td and (td - e['date']).days <= 60]
    if not recent:
        return 0.0
    latest = max(recent, key=lambda x: x['date'])
    sp = latest['surprise_pct']
    if sp >= 15:   return  0.20   # big beat  → strong buy boost
    elif sp >= 5:  return  0.10   # beat      → mild boost
    elif sp >= -5: return  0.00   # in-line   → no change
    elif sp >= -15:return -0.15   # miss      → mild penalty
    else:          return -0.30   # big miss  → avoid

def get_news_adjustment(symbol, trade_date):
    """Return a confidence adjustment [-0.2, +0.2] based on average
    news sentiment in the 7 days before trade_date."""
    if not ENHANCED:
        return 0.0
    news = fetch_news_sentiment(symbol)
    if not news:
        return 0.0
    td = trade_date.date() if hasattr(trade_date, 'date') else trade_date
    window = [n for n in news
              if 0 <= (td - n['date']).days <= 7 and n['relevance'] >= 0.3]
    if not window:
        return 0.0
    avg_sentiment = np.mean([n['sentiment'] for n in window])
    # Alpha Vantage sentiment: -1 (very bearish) to +1 (very bullish)
    # Scale to [-0.20, +0.20] adjustment
    return round(float(np.clip(avg_sentiment * 0.20, -0.20, 0.20)), 3)


# ─────────────────────────────────────────────
# SIGNAL GENERATOR
# ─────────────────────────────────────────────
def generate_signal(row):
    """
    Conservative mode:  uptrend filter + strict thresholds
    Aggressive mode:    no hard filters, lower thresholds, buys dips too
    """
    score = 0
    max_score = 0

    sma_fast   = row.get('sma_fast', 0)
    sma_slow   = row.get('sma_slow', 0)
    sma_50     = row.get('sma_50',  0)
    sma_200    = row.get('sma_200', 0)
    in_uptrend = sma_fast > sma_slow
    above_200  = sma_200 > 0 and row.get('close', 0) > sma_200
    above_50   = sma_50  > 0 and row.get('close', 0) > sma_50
    atr        = row.get('atr', 0)
    close      = row.get('close', 1)
    atr_pct    = atr / close if close > 0 else 0

    if not AGGRESSIVE:
        # ── HARD FILTER 1: Don't buy in a downtrend ──
        if not in_uptrend:
            return 'hold', 0.0
        # ── HARD FILTER 2: Skip extremely volatile days ──
        if atr_pct > 0.04:
            return 'hold', 0.0
        # ── HARD FILTER 3: Don't buy below 200-day MA (bear territory) ──
        if sma_200 > 0 and not above_200:
            return 'hold', 0.0

    # ── RSI ───────────────────────────────────────────
    max_score += 2
    rsi = row.get('rsi', 50)
    if AGGRESSIVE:
        if rsi < 35:
            score += 2    # deeply oversold — aggressive buy the dip
        elif rsi < 50:
            score += 1
        elif rsi > 75:
            score -= 1    # overbought but still consider it
    else:
        if 40 <= rsi <= 55:
            score += 2
        elif rsi < 40:
            score += 1
        elif rsi > 70:
            score -= 2
        elif rsi > 60:
            score -= 1

    # ── MACD ──────────────────────────────────────────
    max_score += 3
    macd_diff = row.get('macd_diff', 0)
    macd      = row.get('macd', 0)
    if macd_diff > 0 and macd < 0:
        score += 3
    elif macd_diff > 0:
        score += 2
    else:
        score -= 1 if AGGRESSIVE else -2

    # ── ADX ───────────────────────────────────────────
    max_score += 2
    adx = row.get('adx', 0)
    if adx > 30:
        score += 2
    elif adx > 20:
        score += 1
    elif not AGGRESSIVE:
        score -= 1

    # ── Bollinger Bands ───────────────────────────────
    max_score += 1
    bb_pos = row.get('bb_position', 0.5)
    if bb_pos < 0.35:
        score += 1
    elif bb_pos < 0.2 and AGGRESSIVE:
        score += 1    # extra point for deep dips in aggressive mode
    elif bb_pos > 0.85:
        score -= 1

    # ── Volume ────────────────────────────────────────
    max_score += 1
    vol_ratio = row.get('volume_ratio', 1)
    if vol_ratio > 1.3:
        score += 1
    elif vol_ratio < 0.7 and not AGGRESSIVE:
        score -= 1

    # ── 200-day MA (long-term trend) ─────────────────
    max_score += 3
    if sma_200 > 0:
        if above_200:
            score += 2    # above 200-day = healthy long-term uptrend
        else:
            score -= 3    # below 200-day = bear territory, avoid

    # ── 50-day MA (medium-term trend) ────────────────
    max_score += 2
    if sma_50 > 0:
        if above_50:
            score += 1    # above 50-day = medium-term momentum
        else:
            score -= 1
        # 50-day above 200-day = sustained bull regime
        if sma_50 > sma_200 > 0:
            score += 1

    # ── Earnings (bonus — only fires when data present) ──
    beat_streak = row.get('earnings_beat_streak', 0)
    surprise    = row.get('earnings_surprise_last', 0)
    pre_window  = row.get('pre_earnings_window', 0)

    if beat_streak >= 3:
        # Serial beater (3+ consecutive beats) — strong lean-in
        score     += 2
        max_score += 2
    elif beat_streak == 2:
        score     += 1
        max_score += 2
    elif beat_streak <= -2:
        # Serial misser — avoid
        score     -= 2
        max_score += 2

    if pre_window and beat_streak >= 2:
        # Pre-earnings window + serial beater = buy-the-rumor bonus
        score     += 1
        max_score += 1

    try:
        if not np.isnan(float(surprise)):
            if surprise >= 15:
                score     += 1   # last quarter was a big beat
                max_score += 1
            elif surprise <= -15:
                score     -= 1   # last quarter was a big miss
                max_score += 1
    except (TypeError, ValueError):
        pass

    # ── Trend bonus in aggressive mode ────────────────
    if AGGRESSIVE and in_uptrend:
        score += 1    # small bonus for being in uptrend
        max_score += 1

    # ── Derive action & confidence ────────────────────
    confidence = abs(score) / max_score if max_score > 0 else 0
    buy_threshold  = 2 if AGGRESSIVE else 4
    sell_threshold = 2 if AGGRESSIVE else 3

    if score >= buy_threshold and confidence >= MIN_CONFIDENCE:
        return 'buy', confidence
    elif score <= -sell_threshold and confidence >= MIN_CONFIDENCE:
        return 'sell', confidence
    else:
        return 'hold', confidence


# ─────────────────────────────────────────────
# BACKTESTER
# ─────────────────────────────────────────────
class Backtester:
    def __init__(self, capital=TRADING_CAPITAL):
        self.initial_capital = capital
        self.cash            = capital
        self.positions       = {}   # symbol → {shares, entry_price, stop_loss, take_profit}
        self.trades          = []
        self.portfolio_history = []

    def run(self, symbol, df, already_has_indicators=False):
        """Run backtest for a single symbol"""
        if not already_has_indicators:
            df = add_indicators(df)

        # Add earnings signals (no-op for crypto)
        df = add_earnings_signals(df, symbol)

        for i in range(1, len(df)):
            row         = df.iloc[i]
            price       = row['close']
            date        = df.index[i]

            # ── Check stop loss / take profit for existing position ──
            if symbol in self.positions:
                pos = self.positions[symbol]

                hit_sl = price <= pos['stop_loss']
                hit_tp = price >= pos['take_profit']

                if hit_sl or hit_tp:
                    reason = 'stop_loss' if hit_sl else 'take_profit'
                    self._close_position(symbol, price, date, reason)
                    continue

            # ── Generate signal ──────────────────────────────────────
            action, confidence = generate_signal(row)

            if symbol in self.positions:
                # We have a position — check for sell signal
                if action == 'sell':
                    self._close_position(symbol, price, date, 'signal')

            else:
                # No position — check for buy signal
                if action == 'buy':
                    # Enhanced mode: adjust confidence with earnings + news
                    if ENHANCED:
                        earnings_adj = get_earnings_adjustment(symbol, date)
                        news_adj     = get_news_adjustment(symbol, date)
                        confidence   = min(1.0, max(0.0, confidence + earnings_adj + news_adj))
                        if confidence < MIN_CONFIDENCE:
                            continue   # skip trade — sentiment/earnings say no
                    self._open_position(symbol, price, date, confidence)

            # ── Record portfolio value ───────────────────────────────
            position_value = 0
            if symbol in self.positions:
                position_value = self.positions[symbol]['shares'] * price

            self.portfolio_history.append({
                'date':            date,
                'symbol':          symbol,
                'cash':            self.cash,
                'position_value':  position_value,
                'total':           self.cash + position_value,
            })

        # Close any open position at end of period
        if symbol in self.positions:
            last_price = df['close'].iloc[-1]
            last_date  = df.index[-1]
            self._close_position(symbol, last_price, last_date, 'end_of_period')

    def _open_position(self, symbol, price, date, confidence):
        position_value = self.cash * MAX_POSITION_SIZE * confidence
        shares = int(position_value / price)
        if shares < 1:
            return

        cost = shares * price
        if cost > self.cash:
            shares = int(self.cash / price)
            cost   = shares * price

        if shares < 1:
            return

        self.cash -= cost
        self.positions[symbol] = {
            'shares':      shares,
            'entry_price': price,
            'stop_loss':   price * (1 - STOP_LOSS_PCT),
            'take_profit': price * (1 + TAKE_PROFIT_PCT),
            'entry_date':  date,
        }

    def _close_position(self, symbol, price, date, reason):
        if symbol not in self.positions:
            return

        pos     = self.positions[symbol]
        revenue = pos['shares'] * price
        cost    = pos['shares'] * pos['entry_price']
        pnl     = revenue - cost
        pnl_pct = (pnl / cost) * 100
        hold_days = (date - pos['entry_date']).days

        self.cash += revenue
        self.trades.append({
            'symbol':      symbol,
            'entry_date':  pos['entry_date'],
            'exit_date':   date,
            'entry_price': pos['entry_price'],
            'exit_price':  price,
            'shares':      pos['shares'],
            'pnl':         pnl,
            'pnl_pct':     pnl_pct,
            'hold_days':   hold_days,
            'reason':      reason,
        })
        del self.positions[symbol]


# ─────────────────────────────────────────────
# METRICS
# ─────────────────────────────────────────────
def calculate_metrics(trades, initial_capital, final_capital):
    if not trades:
        return {}

    df = pd.DataFrame(trades)

    total_trades  = len(df)
    winning       = df[df['pnl'] > 0]
    losing        = df[df['pnl'] <= 0]
    win_rate      = len(winning) / total_trades * 100

    total_pnl     = df['pnl'].sum()
    total_return  = (final_capital - initial_capital) / initial_capital * 100
    avg_win       = winning['pnl'].mean() if len(winning) else 0
    avg_loss      = losing['pnl'].mean()  if len(losing)  else 0
    avg_hold_days = df['hold_days'].mean()

    # Profit factor
    gross_profit = winning['pnl'].sum() if len(winning) else 0
    gross_loss   = abs(losing['pnl'].sum()) if len(losing) else 1
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')

    # Max drawdown
    cumulative = initial_capital + df['pnl'].cumsum()
    rolling_max = cumulative.cummax()
    drawdown    = (cumulative - rolling_max) / rolling_max * 100
    max_drawdown = drawdown.min()

    # Exit reasons
    reasons = df['reason'].value_counts().to_dict()

    return {
        'total_trades':   total_trades,
        'win_rate':       win_rate,
        'total_pnl':      total_pnl,
        'total_return':   total_return,
        'avg_win':        avg_win,
        'avg_loss':       avg_loss,
        'profit_factor':  profit_factor,
        'max_drawdown':   max_drawdown,
        'avg_hold_days':  avg_hold_days,
        'exit_reasons':   reasons,
    }


# ─────────────────────────────────────────────
# REPORT
# ─────────────────────────────────────────────
def print_report(symbol, trades, metrics, initial_capital, final_capital):
    print(f"\n{'═'*65}")
    print(f"  📊  {symbol}  —  Backtest Results")
    print(f"{'═'*65}")

    if not trades:
        print("  ⚠️  No trades were executed for this symbol.")
        return

    print(f"  💰 Starting Capital : ${initial_capital:>10,.2f}")
    print(f"  💰 Final Capital    : ${final_capital:>10,.2f}")
    print(f"  📈 Total Return     : {metrics['total_return']:>+9.2f}%")
    print(f"  💵 Total P&L        : ${metrics['total_pnl']:>+10,.2f}")
    print(f"  {'─'*55}")
    print(f"  🔢 Total Trades     : {metrics['total_trades']:>5}")
    print(f"  ✅ Win Rate         : {metrics['win_rate']:>8.1f}%")
    print(f"  📊 Profit Factor    : {metrics['profit_factor']:>8.2f}  (>1.5 is good)")
    print(f"  📉 Max Drawdown     : {metrics['max_drawdown']:>8.2f}%")
    print(f"  ⏱️  Avg Hold Days    : {metrics['avg_hold_days']:>8.1f}")
    print(f"  {'─'*55}")
    print(f"  🟢 Avg Win          : ${metrics['avg_win']:>+10,.2f}")
    print(f"  🔴 Avg Loss         : ${metrics['avg_loss']:>+10,.2f}")

    reasons = metrics.get('exit_reasons', {})
    print(f"  {'─'*55}")
    print(f"  📤 Exit Reasons:")
    print(f"     Stop Loss    : {reasons.get('stop_loss', 0)}")
    print(f"     Take Profit  : {reasons.get('take_profit', 0)}")
    print(f"     Signal       : {reasons.get('signal', 0)}")
    print(f"     End of Period: {reasons.get('end_of_period', 0)}")

    # Individual trades
    print(f"\n  📋 All Trades:")
    print(f"  {'Date':<12} {'Entry':>8} {'Exit':>8} {'Shares':>6} {'P&L':>10} {'%':>7} {'Reason':<14}")
    print(f"  {'─'*65}")
    for t in sorted(trades, key=lambda x: x['entry_date']):
        pnl_str = f"${t['pnl']:>+,.2f}"
        pct_str = f"{t['pnl_pct']:>+.1f}%"
        emoji   = "✅" if t['pnl'] > 0 else "🔴"
        print(f"  {str(t['entry_date'])[:10]:<12} "
              f"${t['entry_price']:>7.2f} "
              f"${t['exit_price']:>7.2f} "
              f"{t['shares']:>6} "
              f"{pnl_str:>10} "
              f"{pct_str:>7} "
              f"{emoji} {t['reason']:<12}")


def print_summary(all_results, initial_capital):
    """Print a combined summary across all stocks"""
    print(f"\n{'═'*65}")
    print(f"  📊  PORTFOLIO SUMMARY — ALL STOCKS")
    print(f"{'═'*65}")

    all_trades = []
    for r in all_results:
        all_trades.extend(r['trades'])

    if not all_trades:
        print("  ⚠️  No trades across any stock.")
        return

    df = pd.DataFrame(all_trades)
    total_pnl   = df['pnl'].sum()
    total_return = (total_pnl / initial_capital) * 100
    win_rate    = (df['pnl'] > 0).mean() * 100

    print(f"\n  {'Symbol':<8} {'Trades':>6} {'Win%':>7} {'P&L':>12} {'Return%':>9}")
    print(f"  {'─'*50}")

    for r in sorted(all_results, key=lambda x: x['total_pnl'], reverse=True):
        if not r['trades']:
            print(f"  {r['symbol']:<8} {'—':>6} {'—':>7} {'no trades':>12}")
            continue
        rdf = pd.DataFrame(r['trades'])
        wr  = (rdf['pnl'] > 0).mean() * 100
        ret = (r['total_pnl'] / initial_capital) * 100
        emoji = "✅" if r['total_pnl'] > 0 else "🔴"
        print(f"  {r['symbol']:<8} {len(r['trades']):>6} {wr:>6.1f}% "
              f"  ${r['total_pnl']:>+9,.2f} {ret:>+8.2f}%  {emoji}")

    print(f"  {'─'*50}")
    print(f"  {'TOTAL':<8} {len(all_trades):>6} {win_rate:>6.1f}%   ${total_pnl:>+9,.2f} {total_return:>+8.2f}%")
    print(f"\n  📌 Mode: {'AGGRESSIVE' if AGGRESSIVE else 'CONSERVATIVE'} | Position: {MAX_POSITION_SIZE:.0%} per trade")
    print(f"  📌 Stop Loss: {STOP_LOSS_PCT:.0%} | Take Profit: {TAKE_PROFIT_PCT:.0%} | Min Confidence: {MIN_CONFIDENCE:.0%}")


# ─────────────────────────────────────────────
# CURRENT SIGNALS SCANNER
# ─────────────────────────────────────────────
def run_current_signals(args):
    """Scan all symbols and report what the model signals RIGHT NOW (latest bar)."""
    end_date   = args.end or datetime.now().strftime('%Y-%m-%d')
    # Fetch 600 calendar days (~420 trading days) so SMA-200 has plenty of warmup
    fetch_start = (datetime.now() - timedelta(days=600)).strftime('%Y-%m-%d')

    symbols = ([args.symbol.upper()] if args.symbol
               else STOCK_UNIVERSE + CRYPTO_UNIVERSE)

    print(f"\n{'═'*65}")
    print(f"  🔍  CURRENT SIGNAL SCANNER  —  as of {end_date}")
    print(f"{'═'*65}")
    print(f"  Scanning {len(symbols)} symbols...")

    buys   = []
    holds  = []
    errors = []

    for symbol in symbols:
        try:
            is_crypto = '/' in symbol
            df = fetch_crypto_data(symbol, fetch_start, end_date) if is_crypto \
                 else fetch_stock_data(symbol, fetch_start, end_date)

            if df is None or len(df) < 50:   # will drop NaNs after indicators
                errors.append((symbol, 'not enough data'))
                continue

            df = add_indicators(df)
            # Skip earnings signals in scanner (avoids 429 spam; live bot fetches per-symbol)
            df['earnings_beat_streak'] = 0
            df['days_to_earnings']     = np.nan
            df['pre_earnings_window']  = 0
            df['earnings_surprise_last'] = np.nan

            if df.empty:
                errors.append((symbol, 'empty after indicators'))
                continue

            last_row   = df.iloc[-1]
            last_date  = df.index[-1]
            last_price = last_row['close']

            action, confidence = generate_signal(last_row)

            # Earnings context summary for display
            earn_tag = ''
            streak   = last_row.get('earnings_beat_streak', 0)
            days_to  = last_row.get('days_to_earnings', np.nan)
            if streak >= 3:
                earn_tag = f'  🏆 {int(streak)}-beat streak'
            elif streak == 2:
                earn_tag = f'  ✅ 2-beat streak'
            elif streak <= -2:
                earn_tag = f'  ⚠️  {abs(int(streak))}-miss streak'
            if not np.isnan(float(days_to)) if days_to is not None else False:
                try:
                    if 3 <= int(days_to) <= 14:
                        earn_tag += f'  📅 earnings in {int(days_to)}d'
                except Exception:
                    pass

            entry = {
                'symbol':     symbol,
                'price':      last_price,
                'action':     action,
                'confidence': confidence,
                'date':       str(last_date)[:10],
                'earn_tag':   earn_tag,
                'rsi':        last_row.get('rsi', 0),
                'adx':        last_row.get('adx', 0),
                'above_200':  last_row.get('close', 0) > last_row.get('sma_200', 0),
            }

            if action == 'buy':
                buys.append(entry)
            else:
                holds.append(entry)

        except Exception as e:
            errors.append((symbol, str(e)))

    # ── Print BUY recommendations ─────────────────────────────────────────
    print(f"\n{'═'*65}")
    print(f"  🟢  BUY SIGNALS  ({len(buys)} stocks)")
    print(f"{'═'*65}")

    if not buys:
        print("  No BUY signals at current confidence threshold.")
    else:
        buys.sort(key=lambda x: x['confidence'], reverse=True)
        print(f"  {'Symbol':<8} {'Price':>9} {'Confidence':>11} {'RSI':>6} {'ADX':>6}  Notes")
        print(f"  {'─'*62}")
        for b in buys:
            above = '✅ >200MA' if b['above_200'] else ''
            print(f"  {b['symbol']:<8} ${b['price']:>8,.2f} {b['confidence']:>10.0%} "
                  f"{b['rsi']:>6.1f} {b['adx']:>6.1f}  {above}{b['earn_tag']}")

    # ── Print HOLD (near-miss buys, confidence 40-69%) ───────────────────
    near_miss = [h for h in holds if h['confidence'] >= 0.40 and h['action'] == 'hold']
    if near_miss:
        near_miss.sort(key=lambda x: x['confidence'], reverse=True)
        print(f"\n  🟡  WATCH LIST  (near-miss — confidence 50–69%)")
        print(f"  {'─'*62}")
        print(f"  {'Symbol':<8} {'Price':>9} {'Confidence':>11} {'RSI':>6} {'ADX':>6}  Notes")
        print(f"  {'─'*62}")
        for h in near_miss[:15]:
            above = '✅ >200MA' if h['above_200'] else ''
            print(f"  {h['symbol']:<8} ${h['price']:>8,.2f} {h['confidence']:>10.0%} "
                  f"{h['rsi']:>6.1f} {h['adx']:>6.1f}  {above}{h['earn_tag']}")

    # ── Market context summary ────────────────────────────────────────────
    total_scanned = len(buys) + len(holds)
    above_200_count = sum(1 for e in buys + holds if e['above_200'])
    below_200_count = total_scanned - above_200_count
    print(f"\n  📊  MARKET CONTEXT")
    print(f"  {'─'*40}")
    print(f"  Stocks above 200-day MA : {above_200_count}  (healthy long-term uptrend)")
    print(f"  Stocks below 200-day MA : {below_200_count}  (bear territory — model avoids buying)")
    print(f"  ℹ️   If most stocks are below 200MA, the market is in a broad pullback.")
    print(f"      The conservative model correctly avoids buying into a downtrend.")

    if errors:
        print(f"\n  ⚠️  Skipped {len(errors)} symbols (insufficient data or errors)")

    print(f"\n{'═'*65}\n")


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────
def main():
    global MIN_CONFIDENCE, MAX_POSITION_SIZE, TAKE_PROFIT_PCT, STOP_LOSS_PCT, AGGRESSIVE, ENHANCED

    parser = argparse.ArgumentParser(description='Backtest the trading bot strategy')
    parser.add_argument('--symbol',     type=str,   default=None,           help='Single symbol to backtest')
    parser.add_argument('--start',      type=str,   default='2022-01-01',   help='Start date YYYY-MM-DD')
    parser.add_argument('--end',        type=str,   default=None,           help='End date YYYY-MM-DD')
    parser.add_argument('--confidence', type=float, default=MIN_CONFIDENCE, help='Min confidence threshold')
    parser.add_argument('--aggressive', action='store_true',                help='Aggressive mode: more trades, bigger positions, no filters')
    parser.add_argument('--enhanced',   action='store_true',                help='Enhanced mode: add earnings surprise + news sentiment overlay')
    parser.add_argument('--compare',    action='store_true',                help='Run both base and enhanced and show side-by-side comparison')
    parser.add_argument('--signals',    action='store_true',                help='Show current BUY signals as of latest data — no full backtest')
    args = parser.parse_args()

    # ── Current signals mode ──────────────────────────────────────────────
    if args.signals:
        run_current_signals(args)
        return

    MIN_CONFIDENCE = args.confidence

    if args.aggressive:
        AGGRESSIVE        = True
        MIN_CONFIDENCE    = 0.30
        MAX_POSITION_SIZE = 0.20
        TAKE_PROFIT_PCT   = 0.15
        STOP_LOSS_PCT     = 0.07

    if args.enhanced:
        ENHANCED = True
        if not AV_KEY:
            print("  ⚠️  ALPHA_VANTAGE_KEY not set in .env — enhanced mode disabled")
            ENHANCED = False

    end_date   = args.end or datetime.now().strftime('%Y-%m-%d')
    if args.symbol:
        sym = args.symbol.upper()
        stocks  = [sym] if '/' not in sym else []
        cryptos = [sym] if '/' in sym else []
    else:
        stocks  = STOCK_UNIVERSE
        cryptos = CRYPTO_UNIVERSE

    all_symbols = stocks + cryptos

    print(f"\n{'═'*65}")
    print(f"  🤖  TRADING BOT — BACKTEST ENGINE")
    print(f"{'═'*65}")
    print(f"  Period     : {args.start} → {end_date}")
    print(f"  Capital    : ${TRADING_CAPITAL:,.0f}")
    print(f"  Stocks     : {', '.join(stocks)}")
    print(f"  Crypto     : {', '.join(cryptos)}")
    print(f"  Stop Loss  : {STOP_LOSS_PCT:.0%}")
    print(f"  Take Profit: {TAKE_PROFIT_PCT:.0%}")
    print(f"  Confidence : {MIN_CONFIDENCE:.0%}")
    print(f"{'═'*65}")

    all_results = []

    for symbol in all_symbols:
        print(f"\n  ⏳ Fetching data for {symbol}...")
        try:
            is_crypto = '/' in symbol
            # Fetch 3 months extra so indicators have enough history
            indicator_start = (datetime.strptime(args.start, '%Y-%m-%d') - timedelta(days=90)).strftime('%Y-%m-%d')
            df = fetch_crypto_data(symbol, indicator_start, end_date) if is_crypto \
                 else fetch_stock_data(symbol, indicator_start, end_date)

            if df is None or len(df) < 35:
                print(f"  ⚠️  Not enough data for {symbol}, skipping.")
                continue

            # Add indicators on full history, then trim to requested start date
            df = add_indicators(df)
            df = df[df.index >= args.start]

            if df is None or len(df) < 2:
                print(f"  ⚠️  Not enough data after indicator warmup for {symbol}, skipping.")
                continue

            bt = Backtester(capital=TRADING_CAPITAL)
            bt.run(symbol, df, already_has_indicators=True)

            final_capital = bt.cash
            metrics = calculate_metrics(bt.trades, TRADING_CAPITAL, final_capital)

            print_report(symbol, bt.trades, metrics, TRADING_CAPITAL, final_capital)

            all_results.append({
                'symbol':       symbol,
                'trades':       bt.trades,
                'total_pnl':    metrics.get('total_pnl', 0),
                'total_return': metrics.get('total_return', 0),
                'win_rate':     metrics.get('win_rate', 0),
                'num_trades':   metrics.get('total_trades', 0),
            })

        except Exception as e:
            print(f"  ❌ Error backtesting {symbol}: {e}")
            continue

    if len(all_symbols) > 1:
        print_summary(all_results, TRADING_CAPITAL)

    # Save trades to CSV
    all_trades = []
    for r in all_results:
        all_trades.extend(r['trades'])

    if all_trades:
        os.makedirs('logs', exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename  = f"logs/backtest_{timestamp}.csv"
        pd.DataFrame(all_trades).to_csv(filename, index=False)
        print(f"\n  📁 Full trade log saved to: {filename}")

    print(f"\n{'═'*65}\n")

    # ── COMPARE MODE: run enhanced on top of base and show side-by-side ──
    if args.compare:
        print(f"\n{'═'*65}")
        print(f"  🔬  RUNNING ENHANCED BACKTEST (Earnings + News Sentiment)")
        print(f"{'═'*65}")
        if not AV_KEY:
            print("  ⚠️  ALPHA_VANTAGE_KEY not set — cannot run enhanced mode")
            return

        ENHANCED = True
        _earnings_cache.clear()
        _news_cache.clear()

        # Pre-fetch earnings + news for all stocks (with progress)
        print(f"\n  Pre-fetching earnings & news for {len(stocks)} stocks...")
        print(f"  (Alpha Vantage free tier: ~25 req/day — this may take a few minutes)\n")
        for sym in stocks:
            print(f"  Fetching earnings for {sym}...", end=' ', flush=True)
            e = fetch_earnings(sym)
            print(f"{len(e)} records | news...", end=' ', flush=True)
            n = fetch_news_sentiment(sym)
            print(f"{len(n)} articles")

        # Run enhanced backtest
        enhanced_results = []
        for symbol in all_symbols:
            try:
                is_crypto = '/' in symbol
                indicator_start = (datetime.strptime(args.start, '%Y-%m-%d') - timedelta(days=90)).strftime('%Y-%m-%d')
                df = fetch_crypto_data(symbol, indicator_start, end_date) if is_crypto \
                     else fetch_stock_data(symbol, indicator_start, end_date)
                if df is None or len(df) < 35:
                    continue
                df = add_indicators(df)
                df = df[df.index >= args.start]
                if df is None or len(df) < 2:
                    continue
                bt = Backtester(capital=TRADING_CAPITAL)
                bt.run(symbol, df, already_has_indicators=True)
                final_capital = bt.cash
                metrics = calculate_metrics(bt.trades, TRADING_CAPITAL, final_capital)
                enhanced_results.append({
                    'symbol':       symbol,
                    'trades':       bt.trades,
                    'total_pnl':    metrics.get('total_pnl', 0),
                    'total_return': metrics.get('total_return', 0),
                    'win_rate':     metrics.get('win_rate', 0),
                    'num_trades':   metrics.get('total_trades', 0),
                })
            except Exception as e:
                continue

        # Build comparison table
        base_map     = {r['symbol']: r for r in all_results}
        enhanced_map = {r['symbol']: r for r in enhanced_results}

        base_total     = sum(r['total_pnl'] for r in all_results)
        enhanced_total = sum(r['total_pnl'] for r in enhanced_results)

        print(f"\n{'═'*75}")
        print(f"  📊  BASE vs ENHANCED — SIDE BY SIDE COMPARISON")
        print(f"{'═'*75}")
        print(f"  {'Symbol':<7} │ {'Base Return':>11} {'Base Trades':>12} │ {'Enh Return':>10} {'Enh Trades':>11} │ {'Δ Return':>9}")
        print(f"  {'─'*7}─┼─{'─'*24}─┼─{'─'*22}─┼─{'─'*9}")

        symbols_seen = list(dict.fromkeys(
            [r['symbol'] for r in all_results] + [r['symbol'] for r in enhanced_results]
        ))
        for sym in symbols_seen:
            b = base_map.get(sym)
            e = enhanced_map.get(sym)
            b_ret    = f"{b['total_return']:>+.1f}%"    if b else '  —'
            b_trades = f"{b['num_trades'] if b else 0:>5} trades"  if b else '        —'
            e_ret    = f"{e['total_return']:>+.1f}%"    if e else '  —'
            e_trades = f"{e['num_trades'] if e else 0:>5} trades"  if e else '        —'
            delta    = (e['total_return'] if e else 0) - (b['total_return'] if b else 0)
            d_str    = f"{delta:>+.1f}%"
            arrow    = '↑' if delta > 0.5 else ('↓' if delta < -0.5 else '→')
            print(f"  {sym:<7} │ {b_ret:>11} {b_trades:>12} │ {e_ret:>10} {e_trades:>11} │ {arrow} {d_str}")

        base_ret_total = (base_total / TRADING_CAPITAL) * 100
        enh_ret_total  = (enhanced_total / TRADING_CAPITAL) * 100
        delta_total    = enh_ret_total - base_ret_total
        print(f"  {'─'*7}─┼─{'─'*24}─┼─{'─'*22}─┼─{'─'*9}")
        print(f"  {'TOTAL':<7} │ {base_ret_total:>+10.1f}%{'':>12} │ {enh_ret_total:>+9.1f}%{'':>11} │ {'↑' if delta_total > 0 else '↓'} {delta_total:>+.1f}%")
        print(f"\n  Base    : ${base_total:>+,.2f}  ({base_ret_total:>+.1f}%)")
        print(f"  Enhanced: ${enhanced_total:>+,.2f}  ({enh_ret_total:>+.1f}%)")
        print(f"  Delta   : ${enhanced_total - base_total:>+,.2f}  ({delta_total:>+.1f}%)")
        print(f"\n  Earnings data + news sentiment {'HELPED' if delta_total > 0 else 'HURT'} performance by {abs(delta_total):.1f}%")
        print(f"{'═'*75}\n")


if __name__ == '__main__':
    main()