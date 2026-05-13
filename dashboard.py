"""
AI Trading Bot — Comprehensive Stock Dashboard
Run: streamlit run dashboard.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import yfinance as yf
from datetime import datetime, timedelta
import requests
import warnings
import logging
import json
warnings.filterwarnings("ignore")
logging.getLogger("yfinance").setLevel(logging.CRITICAL)
logging.getLogger("peewee").setLevel(logging.CRITICAL)

from dotenv import load_dotenv
load_dotenv()
import config

# Mistral agent — imported lazily so dashboard loads even if key is missing
try:
    from mistral_agent import MistralTrader, get_earnings_context
    _MISTRAL_AVAILABLE = True
except Exception:
    _MISTRAL_AVAILABLE = False

from ta.momentum import RSIIndicator, StochasticOscillator
from ta.trend import MACD as MACDIndicator, ADXIndicator, SMAIndicator, EMAIndicator
from ta.volatility import BollingerBands, AverageTrueRange
from ta.volume import OnBalanceVolumeIndicator

# ════════════════════════════════════════════════════════════════════════════════
# PAGE CONFIG
# ════════════════════════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="AI Trading Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ════════════════════════════════════════════════════════════════════════════════
# CSS
# ════════════════════════════════════════════════════════════════════════════════
st.markdown("""
<style>
  /* ── Layout ── */
  .block-container { padding-top: 1rem; padding-bottom: 1rem; }
  .main { background-color: #0d1117; }

  /* ── Tabs ── */
  .stTabs [data-baseweb="tab-list"] {
      gap: 6px; background: #161b22; border-radius: 8px; padding: 4px 6px;
      border: 1px solid #30363d;
  }
  .stTabs [data-baseweb="tab"] {
      background: transparent; border-radius: 6px; padding: 8px 22px;
      color: #8b949e; font-weight: 500; font-size: 14px;
  }
  .stTabs [aria-selected="true"] {
      background: #1f6feb !important; color: #ffffff !important;
  }

  /* ── Cards ── */
  .metric-card {
      background: #161b22; border: 1px solid #30363d; border-radius: 10px;
      padding: 16px 20px; text-align: center;
  }
  .metric-label { color: #8b949e; font-size: 11px; text-transform: uppercase; letter-spacing: .08em; margin-bottom: 4px; }
  .metric-value { color: #e6edf3; font-size: 26px; font-weight: 700; }
  .metric-sub { font-size: 13px; margin-top: 2px; }

  /* ── Signal badges ── */
  .sig { display:inline-block; padding:2px 10px; border-radius:4px; font-weight:700; font-size:12px; white-space:nowrap; }
  .sig-STRONG_BUY  { background:#0d2b1e; color:#3fb950; border:1px solid #238636; }
  .sig-BUY         { background:#122720; color:#56d364; }
  .sig-HOLD        { background:#21262d; color:#8b949e; }
  .sig-SELL        { background:#2d1018; color:#f85149; }
  .sig-STRONG_SELL { background:#200d10; color:#ff7b72; border:1px solid #da3633; }

  /* ── MACD direction ── */
  .bull { color: #3fb950; font-weight: 700; }
  .bear { color: #f85149; font-weight: 700; }

  /* ── Category pills ── */
  .cat { display:inline-block; padding:1px 8px; border-radius:12px; font-size:11px; font-weight:500; }

  /* ── News card ── */
  .news-card {
      background:#161b22; border:1px solid #30363d; border-radius:8px;
      padding:14px 16px; margin:6px 0;
  }
  .news-title { color:#e6edf3; font-weight:600; font-size:14px; }
  .news-meta  { color:#8b949e; font-size:11px; margin-top:3px; }
  .news-summary { color:#c9d1d9; font-size:13px; margin-top:6px; }
  .pos-green { color:#3fb950; font-weight:600; }
  .pos-red   { color:#f85149; font-weight:600; }

  /* ── Section header ── */
  .sec-header {
      color:#e6edf3; font-size:18px; font-weight:700; margin:16px 0 10px;
      border-bottom:1px solid #30363d; padding-bottom:8px;
  }

  /* ── Stat table ── */
  .stat-row { display:flex; justify-content:space-between; padding:6px 0; border-bottom:1px solid #21262d; }
  .stat-label { color:#8b949e; font-size:13px; }
  .stat-value { color:#e6edf3; font-size:13px; font-weight:500; }
</style>
""", unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════════════════════
# CONSTANTS
# ════════════════════════════════════════════════════════════════════════════════
CATEGORIES = {
    # Photonics
    "LITE":"Photonics","LASR":"Photonics","COHR":"Photonics","AAOI":"Photonics",
    "LPTH":"Photonics","LWLG":"Photonics","FN":"Photonics",
    # Semiconductors
    "ALAB":"Semiconductors","ANET":"Semiconductors","NVDA":"Semiconductors",
    "TSM":"Semiconductors","AVGO":"Semiconductors","MU":"Semiconductors",
    "AMD":"Semiconductors","INTC":"Semiconductors","TXN":"Semiconductors",
    "MRVL":"Semiconductors","CRDO":"Semiconductors","AMKR":"Semiconductors",
    "PLAB":"Semiconductors","AXTI":"Semiconductors","AOSL":"Semiconductors",
    "AEHR":"Semiconductors","POET":"Semiconductors","SKYT":"Semiconductors","CAMT":"Semiconductors",
    # AI/Data Infra
    "VRT":"AI/Data Infra","PLTR":"AI/Data Infra","APP":"AI/Data Infra",
    "NBIS":"AI/Data Infra","CRWV":"AI/Data Infra","DELL":"AI/Data Infra",
    "ORCL":"AI/Data Infra","HPE":"AI/Data Infra","GLW":"AI/Data Infra",
    "CIEN":"AI/Data Infra","APH":"AI/Data Infra",
    # Quantum
    "IONQ":"Quantum","QBTS":"Quantum","ARQQ":"Quantum",
    # Robotics/Space
    "SERV":"Robotics/Space","RCAT":"Robotics/Space","BKSY":"Robotics/Space",
    "ASTS":"Robotics/Space","RKLB":"Robotics/Space","OUST":"Robotics/Space","VWAV":"Robotics/Space",
    # Energy
    "BE":"Energy/Power",
    # Uranium
    "CCJ":"Uranium/Nuclear","UUUU":"Uranium/Nuclear","NXE":"Uranium/Nuclear",
    "UEC":"Uranium/Nuclear","LEU":"Uranium/Nuclear",
    # Storage
    "SNDK":"Storage","STX":"Storage","WDC":"Storage",
    # Metals
    "AG":"Metals/Commodities","GLD":"Metals/Commodities","COPX":"Metals/Commodities",
    "MP":"Metals/Commodities","TMC":"Metals/Commodities","WCP":"Metals/Commodities",
    # Crypto Mining
    "APLD":"Crypto Mining","CORZ":"Crypto Mining","CIFR":"Crypto Mining",
    "WULF":"Crypto Mining","IREN":"Crypto Mining","CRML":"Crypto Mining",
    # Defense/Small Cap
    "USAR":"Defense/Small Cap","WWR":"Defense/Small Cap","ONDS":"Defense/Small Cap",
    "OKLL":"Defense/Small Cap","NUAI":"Defense/Small Cap","BBAI":"Defense/Small Cap",
    "RXRX":"Defense/Small Cap","LAES":"Defense/Small Cap",
    # Infrastructure
    "STRL":"Infrastructure","EME":"Infrastructure","ETN":"Infrastructure",
    "PWR":"Infrastructure","JBL":"Infrastructure",
    # ETFs / Large Cap
    "QQQ":"ETF","SPY":"ETF","AAPL":"Large Cap",
}

CAT_COLORS = {
    "Photonics":"#7c3aed","Semiconductors":"#2563eb","AI/Data Infra":"#059669",
    "Quantum":"#db2777","Robotics/Space":"#d97706","Energy/Power":"#dc2626",
    "Uranium/Nuclear":"#65a30d","Storage":"#0891b2","Metals/Commodities":"#92400e",
    "Crypto Mining":"#f59e0b","Defense/Small Cap":"#6b7280","Infrastructure":"#1d4ed8",
    "ETF":"#374151","Large Cap":"#111827",
}

PERIOD_OPTS = {"1 Month":"1mo","3 Months":"3mo","6 Months":"6mo","1 Year":"1y","2 Years":"2y"}

AV_KEY = os.getenv("ALPHA_VANTAGE_KEY", "")

# ════════════════════════════════════════════════════════════════════════════════
# ALPACA
# ════════════════════════════════════════════════════════════════════════════════
@st.cache_data(ttl=60, show_spinner=False)
def get_alpaca_account():
    try:
        import alpaca_trade_api as tradeapi
        api = tradeapi.REST(config.ALPACA_API_KEY, config.ALPACA_SECRET_KEY,
                            config.ALPACA_BASE_URL, api_version="v2")
        acct = api.get_account()
        return {
            "equity": float(acct.equity),
            "cash": float(acct.cash),
            "buying_power": float(acct.buying_power),
            "portfolio_value": float(acct.portfolio_value),
            "daytrade_count": int(acct.daytrade_count),
        }
    except Exception:
        return None


@st.cache_data(ttl=60, show_spinner=False)
def get_alpaca_positions():
    try:
        import alpaca_trade_api as tradeapi
        api = tradeapi.REST(config.ALPACA_API_KEY, config.ALPACA_SECRET_KEY,
                            config.ALPACA_BASE_URL, api_version="v2")
        positions = api.list_positions()
        return {
            p.symbol: {
                "shares": float(p.qty),
                "entry_price": float(p.avg_entry_price),
                "current_price": float(p.current_price),
                "market_value": float(p.market_value),
                "unrealized_pl": float(p.unrealized_pl),
                "unrealized_plpc": float(p.unrealized_plpc) * 100,
            }
            for p in positions
        }
    except Exception:
        return {}


@st.cache_data(ttl=60, show_spinner=False)
def get_market_status():
    try:
        import alpaca_trade_api as tradeapi
        api = tradeapi.REST(config.ALPACA_API_KEY, config.ALPACA_SECRET_KEY,
                            config.ALPACA_BASE_URL, api_version="v2")
        clock = api.get_clock()
        return clock.is_open
    except Exception:
        return None


# ════════════════════════════════════════════════════════════════════════════════
# DATA FETCHING
# ════════════════════════════════════════════════════════════════════════════════
import time as _time

_PERIOD_DAYS = {"1mo":35,"3mo":100,"6mo":190,"1y":375,"2y":750}


def _alpaca_api():
    import alpaca_trade_api as tradeapi
    return tradeapi.REST(config.ALPACA_API_KEY, config.ALPACA_SECRET_KEY,
                         config.ALPACA_BASE_URL, api_version="v2")


def _fetch_alpaca_batch(symbols: list, lookback_days: int) -> dict:
    """Fetch daily OHLCV bars from Alpaca for a list of US-stock symbols."""
    try:
        from datetime import timezone
        api = _alpaca_api()
        end   = datetime.now(timezone.utc)
        start = end - timedelta(days=lookback_days + 10)

        barset = api.get_bars(
            symbols,
            "1Day",
            start=start.strftime("%Y-%m-%dT%H:%M:%SZ"),
            end=end.strftime("%Y-%m-%dT%H:%M:%SZ"),
            feed="iex",
        )

        # Group bars by symbol
        by_sym: dict = {}
        for bar in barset:
            s = bar.S
            by_sym.setdefault(s, []).append({
                "date":   bar.t,
                "open":   bar.o,
                "high":   bar.h,
                "low":    bar.l,
                "close":  bar.c,
                "volume": bar.v,
            })

        result = {}
        for sym, rows in by_sym.items():
            df = pd.DataFrame(rows).set_index("date")
            df.index = pd.to_datetime(df.index, utc=True).tz_convert(None)
            df = df.sort_index().dropna(subset=["close"])
            if len(df) >= 30:
                result[sym] = df
        return result
    except Exception:
        return {}


def _fetch_yf_batch(symbols: list, period: str) -> dict:
    """Download OHLCV from yfinance in small sub-batches to reduce 429s."""
    BATCH = 15
    DELAY = 2.0
    result = {}
    batches = [symbols[i:i+BATCH] for i in range(0, len(symbols), BATCH)]

    for batch in batches:
        for attempt in range(2):
            try:
                raw = yf.download(batch, period=period, progress=False,
                                  auto_adjust=True, threads=False)
                if raw.empty:
                    raise ValueError("empty")
                # Extract per-symbol DataFrames
                if isinstance(raw.columns, pd.MultiIndex):
                    for sym in batch:
                        try:
                            df = raw.xs(sym, level=1, axis=1).copy()
                            df.columns = [c.lower() for c in df.columns]
                            df = df.dropna(subset=["close"])
                            if len(df) >= 30:
                                result[sym] = df
                        except Exception:
                            pass
                else:
                    df = raw.copy()
                    df.columns = [c.lower() for c in df.columns]
                    df = df.dropna(subset=["close"])
                    if len(df) >= 30 and batch:
                        result[batch[0]] = df
                break
            except Exception:
                if attempt == 0:
                    _time.sleep(3)
        if batch != batches[-1]:
            _time.sleep(DELAY)
    return result


@st.cache_data(ttl=300, show_spinner=False)
def fetch_batch_ohlcv(symbols: tuple, period: str = "6mo") -> dict:
    """
    Fetch daily OHLCV bars.
    Primary:  Alpaca (reliable, no rate limits, covers all US stocks)
    Fallback: yfinance (for any tickers Alpaca doesn't carry)
    """
    lookback = _PERIOD_DAYS.get(period, 375)
    us_syms   = [s for s in symbols if "/" not in s]  # skip crypto symbols

    # ── Primary: Alpaca
    result = _fetch_alpaca_batch(us_syms, lookback)

    # ── Fallback: yfinance for any tickers Alpaca missed
    missing = [s for s in us_syms if s not in result]
    if missing:
        yf_data = _fetch_yf_batch(missing, period)
        result.update(yf_data)

    return result


@st.cache_data(ttl=600, show_spinner=False)
def fetch_fundamentals(symbol: str) -> dict:
    """Fetch fundamental data from yfinance ticker.info with retry on 429."""
    import logging
    logging.getLogger("yfinance").setLevel(logging.CRITICAL)
    for attempt in range(3):
        try:
            t = yf.Ticker(symbol)
            i = t.info
            if not i or i.get("regularMarketPrice") is None and i.get("currentPrice") is None and i.get("marketCap") is None:
                raise ValueError("Empty info response")
            break
        except Exception as e:
            if attempt < 2:
                _time.sleep(2 ** attempt)
            else:
                return {"name": symbol}
    try:
        i = t.info
        return {
            "name": i.get("longName") or i.get("shortName", symbol),
            "sector": i.get("sector", "—"),
            "industry": i.get("industry", "—"),
            "market_cap": i.get("marketCap"),
            "pe_trailing": i.get("trailingPE"),
            "pe_forward": i.get("forwardPE"),
            "eps_ttm": i.get("trailingEps"),
            "beta": i.get("beta"),
            "dividend_yield": i.get("dividendYield"),
            "52w_high": i.get("fiftyTwoWeekHigh"),
            "52w_low": i.get("fiftyTwoWeekLow"),
            "avg_volume": i.get("averageVolume"),
            "shares_outstanding": i.get("sharesOutstanding"),
            "book_value": i.get("bookValue"),
            "price_to_book": i.get("priceToBook"),
            "debt_to_equity": i.get("debtToEquity"),
            "current_ratio": i.get("currentRatio"),
            "quick_ratio": i.get("quickRatio"),
            "profit_margin": i.get("profitMargins"),
            "operating_margin": i.get("operatingMargins"),
            "roe": i.get("returnOnEquity"),
            "roa": i.get("returnOnAssets"),
            "revenue": i.get("totalRevenue"),
            "revenue_growth": i.get("revenueGrowth"),
            "earnings_growth": i.get("earningsGrowth"),
            "free_cash_flow": i.get("freeCashflow"),
            "description": i.get("longBusinessSummary", ""),
            "website": i.get("website", ""),
            "employees": i.get("fullTimeEmployees"),
            "country": i.get("country", ""),
            "exchange": i.get("exchange", ""),
            "analyst_target": i.get("targetMeanPrice"),
            "analyst_recommendation": i.get("recommendationKey", "").lower(),
            "analyst_count": i.get("numberOfAnalystOpinions"),
            "short_ratio": i.get("shortRatio"),
            "float_shares": i.get("floatShares"),
        }
    except Exception:
        return {"name": symbol}


@st.cache_data(ttl=1800, show_spinner=False)
def fetch_news_av(symbol: str, limit: int = 8) -> list:
    """Fetch news + sentiment from Alpha Vantage."""
    if not AV_KEY:
        return []
    try:
        url = (
            f"https://www.alphavantage.co/query"
            f"?function=NEWS_SENTIMENT&tickers={symbol}"
            f"&limit={limit}&apikey={AV_KEY}"
        )
        r = requests.get(url, timeout=8)
        data = r.json()
        articles = []
        for item in data.get("feed", [])[:limit]:
            ts = item.get("time_published", "")
            dt_str = ""
            if ts:
                try:
                    dt_str = datetime.strptime(ts, "%Y%m%dT%H%M%S").strftime("%b %d, %Y %H:%M")
                except Exception:
                    dt_str = ts
            ticker_score = None
            for ts_item in item.get("ticker_sentiment", []):
                if ts_item.get("ticker") == symbol:
                    ticker_score = float(ts_item.get("ticker_sentiment_score", 0))
                    break
            articles.append({
                "title": item.get("title", ""),
                "url": item.get("url", ""),
                "source": item.get("source", ""),
                "published": dt_str,
                "summary": item.get("summary", ""),
                "sentiment_score": item.get("overall_sentiment_score"),
                "sentiment_label": item.get("overall_sentiment_label", ""),
                "ticker_score": ticker_score,
            })
        return articles
    except Exception:
        return []


@st.cache_data(ttl=900, show_spinner=False)
def fetch_news_yf(symbol: str, limit: int = 6) -> list:
    """Fetch news from yfinance as fallback."""
    try:
        t = yf.Ticker(symbol)
        news = t.news or []
        results = []
        for n in news[:limit]:
            results.append({
                "title": n.get("title", ""),
                "url": n.get("link", ""),
                "source": n.get("publisher", ""),
                "published": datetime.fromtimestamp(n.get("providerPublishTime", 0)).strftime("%b %d, %Y")
                if n.get("providerPublishTime") else "",
                "summary": "",
                "sentiment_score": None,
                "sentiment_label": "",
                "ticker_score": None,
            })
        return results
    except Exception:
        return []


# ════════════════════════════════════════════════════════════════════════════════
# TECHNICAL ANALYSIS
# ════════════════════════════════════════════════════════════════════════════════
def compute_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Add all technical indicators to an OHLCV DataFrame."""
    df = df.copy()
    if len(df) < 30:
        return df
    close = df["close"]
    high  = df["high"]
    low   = df["low"]
    vol   = df["volume"]

    # ── Trend
    df["sma20"]  = SMAIndicator(close, window=20).sma_indicator()
    df["sma50"]  = SMAIndicator(close, window=50).sma_indicator()
    df["sma200"] = SMAIndicator(close, window=200).sma_indicator()
    df["ema12"]  = EMAIndicator(close, window=12).ema_indicator()
    df["ema26"]  = EMAIndicator(close, window=26).ema_indicator()

    macd = MACDIndicator(close, window_fast=12, window_slow=26, window_sign=9)
    df["macd"]        = macd.macd()
    df["macd_signal"] = macd.macd_signal()
    df["macd_hist"]   = macd.macd_diff()

    adx = ADXIndicator(high, low, close, window=14)
    df["adx"]  = adx.adx()
    df["dmp"]  = adx.adx_pos()
    df["dmn"]  = adx.adx_neg()

    # ── Momentum
    df["rsi"] = RSIIndicator(close, window=14).rsi()
    stoch = StochasticOscillator(high, low, close, window=14, smooth_window=3)
    df["stoch_k"] = stoch.stoch()
    df["stoch_d"] = stoch.stoch_signal()
    df["roc10"]   = close.pct_change(10) * 100

    # ── Volatility
    bb = BollingerBands(close, window=20, window_dev=2)
    df["bb_upper"]  = bb.bollinger_hband()
    df["bb_middle"] = bb.bollinger_mavg()
    df["bb_lower"]  = bb.bollinger_lband()
    df["bb_width"]  = (df["bb_upper"] - df["bb_lower"]) / df["bb_middle"]
    df["bb_pos"]    = (close - df["bb_lower"]) / (df["bb_upper"] - df["bb_lower"] + 1e-9)
    df["atr"]       = AverageTrueRange(high, low, close, window=14).average_true_range()
    df["volatility"] = close.pct_change().rolling(20).std() * np.sqrt(252)

    # ── Volume
    df["obv"]        = OnBalanceVolumeIndicator(close, vol).on_balance_volume()
    df["vol_sma20"]  = vol.rolling(20).mean()
    df["vol_ratio"]  = vol / df["vol_sma20"].replace(0, np.nan)

    return df


def compute_signal(row: pd.Series) -> tuple:
    """
    Returns (signal_str, score, confidence) for a stock row with indicators.
    Score > 0 = bullish, < 0 = bearish.
    """
    score = 0.0

    rsi = row.get("rsi", 50)
    if pd.notna(rsi):
        if rsi < 30:   score += 2.5
        elif rsi < 40: score += 1.0
        elif rsi > 70: score -= 2.5
        elif rsi > 60: score -= 1.0

    macd = row.get("macd", 0)
    macd_sig = row.get("macd_signal", 0)
    macd_hist = row.get("macd_hist", 0)
    if pd.notna(macd) and pd.notna(macd_sig):
        if macd > macd_sig:   score += 1.0
        else:                 score -= 1.0
        if pd.notna(macd_hist):
            if macd_hist > 0:  score += 0.5
            else:              score -= 0.5

    close = row.get("close", 0)
    sma50  = row.get("sma50", np.nan)
    sma200 = row.get("sma200", np.nan)
    if pd.notna(sma50)  and close > 0: score += 1.0 if close > sma50  else -1.0
    if pd.notna(sma200) and close > 0: score += 1.0 if close > sma200 else -1.0
    if pd.notna(sma50) and pd.notna(sma200):
        score += 0.5 if sma50 > sma200 else -0.5  # golden/death cross

    bb_pos = row.get("bb_pos", 0.5)
    if pd.notna(bb_pos):
        if bb_pos < 0.15:   score += 1.5
        elif bb_pos < 0.30: score += 0.5
        elif bb_pos > 0.85: score -= 1.5
        elif bb_pos > 0.70: score -= 0.5

    adx = row.get("adx", 0)
    strength = abs(score)
    if pd.notna(adx) and adx > 25:
        strength *= 1.2

    if score >= 3.5:    sig = "STRONG BUY"
    elif score >= 1.5:  sig = "BUY"
    elif score <= -3.5: sig = "STRONG SELL"
    elif score <= -1.5: sig = "SELL"
    else:               sig = "HOLD"

    max_possible = 8.5
    confidence = min(abs(score) / max_possible, 1.0)
    return sig, round(score, 2), round(confidence, 2)


# ════════════════════════════════════════════════════════════════════════════════
# HELPERS
# ════════════════════════════════════════════════════════════════════════════════
def fmt_large(n):
    if n is None or (isinstance(n, float) and np.isnan(n)):
        return "—"
    if abs(n) >= 1e12: return f"${n/1e12:.2f}T"
    if abs(n) >= 1e9:  return f"${n/1e9:.2f}B"
    if abs(n) >= 1e6:  return f"${n/1e6:.2f}M"
    return f"${n:,.0f}"

def fmt_pct(v, decimals=2):
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return "—"
    return f"{v*100:.{decimals}f}%"

def fmt_val(v, fmt=".2f", prefix=""):
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return "—"
    return f"{prefix}{v:{fmt}}"

def pct_color(v):
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return "#8b949e"
    return "#3fb950" if v >= 0 else "#f85149"

def signal_badge(sig: str) -> str:
    key = sig.replace(" ", "_")
    return f'<span class="sig sig-{key}">{sig}</span>'

def cat_badge(cat: str) -> str:
    color = CAT_COLORS.get(cat, "#374151")
    return (
        f'<span class="cat" style="background:{color}22;color:{color};'
        f'border:1px solid {color}55">{cat}</span>'
    )

def sentiment_color(score):
    if score is None: return "#8b949e"
    if score > 0.1:   return "#3fb950"
    if score < -0.1:  return "#f85149"
    return "#e6edf3"

def build_overview_df(ohlcv_data: dict, positions: dict) -> pd.DataFrame:
    """Build the summary DataFrame for Tab 1."""
    rows = []
    for sym in config.STOCK_UNIVERSE:
        df = ohlcv_data.get(sym)
        if df is None or len(df) < 30:
            rows.append({
                "Symbol": sym, "Category": CATEGORIES.get(sym, "—"),
                "Price": None, "1D %": None, "1W %": None, "1M %": None,
                "RSI": None, "MACD": None, "BB Pos": None, "ADX": None,
                "Vol/Avg": None, "52W Pos": None, "Signal": "—", "Score": 0,
                "Confidence": 0, "Held": sym in positions,
                "P&L %": positions.get(sym, {}).get("unrealized_plpc"),
            })
            continue

        df = compute_indicators(df)
        last = df.iloc[-1]
        close = float(last["close"])
        prev  = float(df["close"].iloc[-2]) if len(df) > 1 else close
        prev5 = float(df["close"].iloc[-6]) if len(df) > 5 else close
        prev20= float(df["close"].iloc[-21]) if len(df) > 20 else close

        w52hi = float(df["close"].tail(252).max())
        w52lo = float(df["close"].tail(252).min())
        w52pos = (close - w52lo) / (w52hi - w52lo + 1e-9) * 100 if w52hi > w52lo else 50

        sig, score, conf = compute_signal(last)

        pos = positions.get(sym, {})
        rows.append({
            "Symbol": sym,
            "Category": CATEGORIES.get(sym, "—"),
            "Price": close,
            "1D %": (close - prev) / prev * 100 if prev else None,
            "1W %": (close - prev5) / prev5 * 100 if prev5 else None,
            "1M %": (close - prev20) / prev20 * 100 if prev20 else None,
            "RSI": round(float(last["rsi"]), 1) if pd.notna(last.get("rsi")) else None,
            "MACD": "↑ Bull" if (pd.notna(last.get("macd")) and pd.notna(last.get("macd_signal"))
                                  and last["macd"] > last["macd_signal"]) else "↓ Bear",
            "BB Pos": round(float(last["bb_pos"]) * 100, 1) if pd.notna(last.get("bb_pos")) else None,
            "ADX": round(float(last["adx"]), 1) if pd.notna(last.get("adx")) else None,
            "Vol/Avg": round(float(last["vol_ratio"]), 2) if pd.notna(last.get("vol_ratio")) else None,
            "52W Pos": round(w52pos, 1),
            "Signal": sig,
            "Score": score,
            "Confidence": conf,
            "Held": sym in positions,
            "P&L %": pos.get("unrealized_plpc"),
        })
    return pd.DataFrame(rows)


# ════════════════════════════════════════════════════════════════════════════════
# MISTRAL AI INTEGRATION
# ════════════════════════════════════════════════════════════════════════════════

def _tech_data_for_mistral(df: pd.DataFrame) -> dict:
    """Extract the tech_data dict that MistralTrader._build_prompt expects."""
    last = df.iloc[-1]
    def _f(col):
        v = last.get(col)
        return float(v) if v is not None and pd.notna(v) else None
    return {
        "current_price": _f("close"),
        "close":         _f("close"),
        "rsi":           _f("rsi"),
        "macd":          _f("macd"),
        "macd_diff":     _f("macd_hist"),
        "sma_fast":      _f("sma20"),
        "sma_slow":      _f("sma50"),
        "sma_50":        _f("sma50"),
        "sma_60":        None,
        "sma_200":       _f("sma200"),
        "adx":           _f("adx"),
        "volume_ratio":  _f("vol_ratio"),
        "bb_position":   _f("bb_pos"),
        "atr":           _f("atr"),
    }


def _run_mistral(symbol: str, tech_data: dict, position) -> dict:
    """Call MistralTrader for one symbol. Returns decision dict."""
    if not _MISTRAL_AVAILABLE:
        return {"action": "hold", "confidence": 0.0,
                "reasoning": "mistralai package not installed.", "risk_level": "unknown"}
    try:
        trader = MistralTrader()
        return trader.analyze_and_decide(symbol, tech_data, current_position=position)
    except Exception as e:
        return {"action": "hold", "confidence": 0.0,
                "reasoning": str(e), "risk_level": "high"}


_AI_ACTION_ICON = {
    "buy":  "🤖 BUY",
    "sell": "🤖 SELL",
    "hold": "🤖 HOLD",
}
_AI_ACTION_COLOR = {
    "buy":  "#3fb950",
    "sell": "#f85149",
    "hold": "#8b949e",
}


def _ai_result_card(symbol: str, result: dict, show_full: bool = False):
    """Render a Mistral result as an HTML card."""
    action   = result.get("action", "hold").lower()
    conf     = result.get("confidence", 0.0)
    risk     = result.get("risk_level", "—")
    reason   = result.get("reasoning", "")
    factors  = result.get("key_factors", [])
    def _to_float(v):
        try:
            return float(v) if v is not None else None
        except (ValueError, TypeError):
            return None

    sl    = _to_float(result.get("stop_loss_recommendation"))
    tp    = _to_float(result.get("take_profit_recommendation"))
    entry = _to_float(result.get("entry_price_recommendation"))

    color    = _AI_ACTION_COLOR.get(action, "#8b949e")
    border   = f"2px solid {color}"
    conf_pct = f"{conf*100:.0f}%"

    factors_html = ""
    if factors:
        pills = "".join(
            f'<span style="background:{color}22;color:{color};border:1px solid {color}44;'
            f'border-radius:4px;padding:1px 7px;font-size:11px;margin:2px 3px 2px 0;display:inline-block">'
            f'{f}</span>' for f in factors
        )
        factors_html = f'<div style="margin-top:8px">{pills}</div>'

    prices_html = ""
    if any([sl, tp, entry]):
        parts = []
        if entry: parts.append(f'Entry: <b>${entry:.2f}</b>')
        if sl:    parts.append(f'Stop Loss: <b style="color:#f85149">${sl:.2f}</b>')
        if tp:    parts.append(f'Take Profit: <b style="color:#3fb950">${tp:.2f}</b>')
        prices_html = (
            f'<div style="margin-top:8px;font-size:12px;color:#8b949e;display:flex;gap:16px">'
            + " · ".join(parts) + "</div>"
        )

    max_reason = len(reason) if show_full else 200
    reason_trunc = reason[:max_reason] + ("…" if len(reason) > max_reason and not show_full else "")

    st.markdown(
        f'<div style="background:#161b22;border:{border};border-radius:10px;padding:14px 16px;margin:6px 0">'
        f'<div style="display:flex;justify-content:space-between;align-items:center">'
        f'<span style="font-size:16px;font-weight:700;color:#e6edf3">{symbol}</span>'
        f'<span style="display:flex;gap:10px;align-items:center">'
        f'<span style="color:{color};font-weight:700;font-size:15px">{_AI_ACTION_ICON.get(action,"🤖 "+action.upper())}</span>'
        f'<span style="color:#8b949e;font-size:12px">Conf: <b style="color:#e6edf3">{conf_pct}</b></span>'
        f'<span style="color:#8b949e;font-size:12px">Risk: <b style="color:#e6edf3">{risk.capitalize()}</b></span>'
        f'</span></div>'
        + factors_html
        + f'<div style="color:#c9d1d9;font-size:13px;margin-top:8px;line-height:1.5">{reason_trunc}</div>'
        + prices_html
        + '</div>',
        unsafe_allow_html=True,
    )


# ════════════════════════════════════════════════════════════════════════════════
# CANDLESTICK CHART
# ════════════════════════════════════════════════════════════════════════════════
PLOTLY_LAYOUT = dict(
    template="plotly_dark",
    paper_bgcolor="#0d1117",
    plot_bgcolor="#0d1117",
    font=dict(family="monospace", color="#8b949e", size=12),
    margin=dict(l=0, r=0, t=30, b=0),
    xaxis=dict(gridcolor="#21262d", showgrid=True, zeroline=False),
    yaxis=dict(gridcolor="#21262d", showgrid=True, zeroline=False),
)


def make_price_chart(df: pd.DataFrame, symbol: str, show_bb=True, show_sma=True) -> go.Figure:
    """Candlestick + BB + SMAs + Volume + RSI + MACD."""
    fig = make_subplots(
        rows=4, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.02,
        row_heights=[0.55, 0.15, 0.15, 0.15],
        subplot_titles=(f"{symbol} Price", "Volume", "RSI (14)", "MACD"),
    )

    # ── Candlestick
    fig.add_trace(go.Candlestick(
        x=df.index, open=df["open"], high=df["high"],
        low=df["low"], close=df["close"],
        name="Price",
        increasing_line_color="#3fb950", decreasing_line_color="#f85149",
        increasing_fillcolor="rgba(63,185,80,0.25)",
        decreasing_fillcolor="rgba(248,81,73,0.25)",
    ), row=1, col=1)

    if show_bb and "bb_upper" in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df["bb_upper"],
            line=dict(color="#f59e0b", width=1, dash="dot"), name="BB Upper", showlegend=False), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df["bb_lower"],
            line=dict(color="#f59e0b", width=1, dash="dot"), name="BB Lower",
            fill="tonexty", fillcolor="rgba(245,158,11,0.07)", showlegend=False), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df["bb_middle"],
            line=dict(color="rgba(245,158,11,0.4)", width=1), name="BB Mid", showlegend=False), row=1, col=1)

    if show_sma:
        for col, color, label in [("sma20","#60a5fa","SMA20"),("sma50","#a78bfa","SMA50"),("sma200","#fb923c","SMA200")]:
            if col in df.columns:
                fig.add_trace(go.Scatter(x=df.index, y=df[col],
                    line=dict(color=color, width=1.2), name=label), row=1, col=1)

    # ── Volume
    colors = ["#3fb950" if c >= o else "#f85149"
              for c, o in zip(df["close"], df["open"])]
    fig.add_trace(go.Bar(x=df.index, y=df["volume"], marker_color=colors,
                         name="Volume", showlegend=False), row=2, col=1)
    if "vol_sma20" in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df["vol_sma20"],
            line=dict(color="#f59e0b", width=1.2), name="Vol SMA20", showlegend=False), row=2, col=1)

    # ── RSI
    if "rsi" in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df["rsi"],
            line=dict(color="#60a5fa", width=1.5), name="RSI", showlegend=False), row=3, col=1)
        for level, color in [(70, "#f85149"), (30, "#3fb950"), (50, "#8b949e")]:
            fig.add_hline(y=level, line_dash="dot", line_color=color, opacity=0.5, row=3, col=1)
        fig.update_yaxes(range=[0, 100], row=3, col=1)

    # ── MACD
    if "macd" in df.columns:
        hist_colors = ["#3fb950" if v >= 0 else "#f85149" for v in df["macd_hist"].fillna(0)]
        fig.add_trace(go.Bar(x=df.index, y=df["macd_hist"],
            marker_color=hist_colors, name="MACD Hist", showlegend=False), row=4, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df["macd"],
            line=dict(color="#60a5fa", width=1.5), name="MACD", showlegend=False), row=4, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df["macd_signal"],
            line=dict(color="#f59e0b", width=1.5), name="Signal", showlegend=False), row=4, col=1)
        fig.add_hline(y=0, line_color="#8b949e", opacity=0.4, row=4, col=1)

    fig.update_layout(
        **PLOTLY_LAYOUT,
        height=720, xaxis_rangeslider_visible=False,
        legend=dict(orientation="h", yanchor="bottom", y=1.01, xanchor="right", x=1,
                    bgcolor="#0d1117", bordercolor="#30363d"),
        hovermode="x unified",
    )
    fig.update_xaxes(showspikes=True, spikecolor="#8b949e", spikethickness=1)
    fig.update_yaxes(showspikes=True, spikecolor="#8b949e", spikethickness=1)
    for i in range(1, 5):
        fig.update_xaxes(showgrid=True, gridcolor="#21262d", row=i, col=1)
        fig.update_yaxes(showgrid=True, gridcolor="#21262d", row=i, col=1)
    return fig


def make_stoch_adx_chart(df: pd.DataFrame) -> go.Figure:
    """Stochastic + ADX chart."""
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.04,
                        subplot_titles=("Stochastic (14,3)", "ADX / DMI (14)"))

    if "stoch_k" in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df["stoch_k"],
            line=dict(color="#a78bfa", width=1.5), name="%K"), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df["stoch_d"],
            line=dict(color="#f59e0b", width=1.5), name="%D"), row=1, col=1)
        fig.add_hline(y=80, line_dash="dot", line_color="#f85149", opacity=0.5, row=1, col=1)
        fig.add_hline(y=20, line_dash="dot", line_color="#3fb950", opacity=0.5, row=1, col=1)
        fig.update_yaxes(range=[0, 100], row=1, col=1)

    if "adx" in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df["adx"],
            line=dict(color="#60a5fa", width=2), name="ADX"), row=2, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df["dmp"],
            line=dict(color="#3fb950", width=1.2), name="+DI"), row=2, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df["dmn"],
            line=dict(color="#f85149", width=1.2), name="-DI"), row=2, col=1)
        fig.add_hline(y=25, line_dash="dot", line_color="#f59e0b", opacity=0.5, row=2, col=1)

    fig.update_layout(**PLOTLY_LAYOUT, height=340, hovermode="x unified",
                      legend=dict(orientation="h", yanchor="bottom", y=1.01, xanchor="right", x=1,
                                  bgcolor="#0d1117"))
    for i in range(1, 3):
        fig.update_xaxes(showgrid=True, gridcolor="#21262d", row=i, col=1)
        fig.update_yaxes(showgrid=True, gridcolor="#21262d", row=i, col=1)
    return fig


def make_bb_volatility_chart(df: pd.DataFrame) -> go.Figure:
    """Bollinger Band width + ATR + Volatility."""
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.04,
                        subplot_titles=("Bollinger Band Width (20,2)", "ATR (14) & Annualised Volatility"))

    if "bb_width" in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df["bb_width"] * 100,
            line=dict(color="#a78bfa", width=1.5), name="BB Width %", fill="tozeroy",
            fillcolor="rgba(167,139,250,0.13)"), row=1, col=1)

    if "atr" in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df["atr"],
            line=dict(color="#f59e0b", width=1.5), name="ATR"), row=2, col=1)
    if "volatility" in df.columns:
        fig2y = df["volatility"] * 100
        fig.add_trace(go.Scatter(x=df.index, y=fig2y,
            line=dict(color="#60a5fa", width=1.5), name="HV 20d %"), row=2, col=1)

    fig.update_layout(**PLOTLY_LAYOUT, height=320, hovermode="x unified",
                      legend=dict(orientation="h", bgcolor="#0d1117"))
    for i in range(1, 3):
        fig.update_xaxes(showgrid=True, gridcolor="#21262d", row=i, col=1)
        fig.update_yaxes(showgrid=True, gridcolor="#21262d", row=i, col=1)
    return fig


def make_sector_chart(overview_df: pd.DataFrame) -> go.Figure:
    """Bar chart of signal distribution by category."""
    df = overview_df[overview_df["Signal"] != "—"].copy()
    cats = df.groupby(["Category","Signal"]).size().reset_index(name="count")

    sig_order = ["STRONG BUY","BUY","HOLD","SELL","STRONG SELL"]
    sig_colors = {"STRONG BUY":"#10b981","BUY":"#3fb950","HOLD":"#8b949e","SELL":"#f85149","STRONG SELL":"#ef4444"}

    fig = go.Figure()
    for sig in sig_order:
        sub = cats[cats["Signal"] == sig]
        fig.add_trace(go.Bar(
            x=sub["Category"], y=sub["count"],
            name=sig, marker_color=sig_colors[sig],
        ))
    fig.update_layout(**PLOTLY_LAYOUT, height=300, barmode="stack",
                      legend=dict(orientation="h", bgcolor="#0d1117"),
                      title=dict(text="Signal Distribution by Sector", font=dict(color="#e6edf3")))
    return fig


def make_returns_scatter(overview_df: pd.DataFrame) -> go.Figure:
    """Scatter: 1M return vs RSI coloured by signal."""
    df = overview_df.dropna(subset=["1M %","RSI","Signal"])
    sig_colors = {"STRONG BUY":"#10b981","BUY":"#3fb950","HOLD":"#8b949e",
                  "SELL":"#f85149","STRONG SELL":"#ef4444","—":"#374151"}
    colors = [sig_colors.get(s,"#8b949e") for s in df["Signal"]]
    fig = go.Figure(go.Scatter(
        x=df["RSI"], y=df["1M %"],
        mode="markers+text",
        text=df["Symbol"], textposition="top center", textfont=dict(size=9, color="#8b949e"),
        marker=dict(size=8, color=colors, line=dict(width=0.5, color="#30363d")),
        hovertemplate="<b>%{text}</b><br>RSI: %{x:.1f}<br>1M: %{y:.1f}%<extra></extra>",
    ))
    fig.add_vline(x=30, line_dash="dot", line_color="#3fb950", opacity=0.4)
    fig.add_vline(x=70, line_dash="dot", line_color="#f85149", opacity=0.4)
    fig.add_hline(y=0,  line_dash="dot", line_color="#8b949e", opacity=0.4)
    fig.update_layout(**PLOTLY_LAYOUT, height=360,
                      xaxis_title="RSI (14)", yaxis_title="1-Month Return (%)",
                      title=dict(text="RSI vs 1-Month Return", font=dict(color="#e6edf3")))
    return fig


# ════════════════════════════════════════════════════════════════════════════════
# TAB 1  —  PORTFOLIO OVERVIEW
# ════════════════════════════════════════════════════════════════════════════════
def tab_overview(ohlcv_data: dict, positions: dict, account: dict, market_open):
    # ── Header metrics
    total = len(config.STOCK_UNIVERSE)
    n_pos = len(positions)

    acct_val = f"${account['portfolio_value']:,.0f}" if account else "—"
    cash_val = f"${account['cash']:,.0f}" if account else "—"
    bp_val   = f"${account['buying_power']:,.0f}" if account else "—"

    overview_df = build_overview_df(ohlcv_data, positions)
    n_buy  = (overview_df["Signal"].isin(["BUY","STRONG BUY"])).sum()
    n_sell = (overview_df["Signal"].isin(["SELL","STRONG SELL"])).sum()
    n_hold = (overview_df["Signal"] == "HOLD").sum()

    market_str = "🟢 OPEN" if market_open else ("🔴 CLOSED" if market_open is not None else "⚪ Unknown")
    c1,c2,c3,c4,c5,c6 = st.columns(6)
    for col, label, val, sub in [
        (c1, "Market", market_str, datetime.now().strftime("%H:%M ET")),
        (c2, "Portfolio Value", acct_val, f"Cash: {cash_val}"),
        (c3, "Buying Power", bp_val, ""),
        (c4, "Open Positions", str(n_pos), f"of {total} stocks"),
        (c5, "BUY Signals", str(n_buy), f"+ {n_sell} SELL · {n_hold} HOLD"),
        (c6, "Stocks Tracked", str(total), "In STOCK_UNIVERSE"),
    ]:
        col.markdown(
            f'<div class="metric-card"><div class="metric-label">{label}</div>'
            f'<div class="metric-value">{val}</div>'
            f'<div class="metric-sub" style="color:#8b949e">{sub}</div></div>',
            unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Current positions banner
    if positions:
        st.markdown('<div class="sec-header">Current Positions</div>', unsafe_allow_html=True)
        pcols = st.columns(min(len(positions), 5))
        for i, (sym, pos) in enumerate(positions.items()):
            c = pcols[i % len(pcols)]
            pl = pos["unrealized_pl"]
            plp = pos["unrealized_plpc"]
            clr = "#3fb950" if pl >= 0 else "#f85149"
            c.markdown(
                f'<div class="metric-card">'
                f'<div style="font-size:18px;font-weight:700;color:#e6edf3">{sym}</div>'
                f'<div style="color:#8b949e;font-size:12px">{pos["shares"]:.0f} shares @ ${pos["entry_price"]:.2f}</div>'
                f'<div style="font-size:20px;font-weight:700;color:{clr};margin-top:4px">'
                f'{"+" if pl >= 0 else ""}{plp:.2f}%</div>'
                f'<div style="color:{clr};font-size:13px">{"+" if pl >= 0 else ""}${pl:,.2f}</div>'
                f'</div>', unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)

    # ── Filters
    st.markdown('<div class="sec-header">All Stocks</div>', unsafe_allow_html=True)
    f1, f2, f3, f4 = st.columns([2, 2, 2, 1])
    with f1:
        sig_filter = st.multiselect(
            "Signal", ["STRONG BUY","BUY","HOLD","SELL","STRONG SELL","—"],
            default=[], key="sig_filter", label_visibility="collapsed",
            placeholder="Filter by signal…")
    with f2:
        all_cats = sorted(set(CATEGORIES.values()))
        cat_filter = st.multiselect(
            "Category", all_cats, default=[], key="cat_filter",
            label_visibility="collapsed", placeholder="Filter by category…")
    with f3:
        search = st.text_input("Search", placeholder="Search symbol or name…",
                               label_visibility="collapsed", key="search")
    with f4:
        held_only = st.checkbox("Held only", value=False)

    dfl = overview_df.copy()
    if sig_filter:  dfl = dfl[dfl["Signal"].isin(sig_filter)]
    if cat_filter:  dfl = dfl[dfl["Category"].isin(cat_filter)]
    if held_only:   dfl = dfl[dfl["Held"]]
    if search:      dfl = dfl[dfl["Symbol"].str.contains(search.upper())]

    # ── Sort
    s1, s2 = st.columns([3, 1])
    with s1:
        sort_col = st.selectbox(
            "Sort by", ["Signal (Bullish First)","Symbol","1D %","1W %","1M %","RSI","ADX","Vol/Avg"],
            key="sort_col", label_visibility="collapsed")
    with s2:
        sort_asc = st.toggle("Ascending", value=False, key="sort_asc")

    if sort_col == "Signal (Bullish First)":
        sig_order = {"STRONG BUY":0,"BUY":1,"HOLD":2,"SELL":3,"STRONG SELL":4,"—":5}
        dfl["_sort"] = dfl["Signal"].map(sig_order).fillna(5)
        dfl = dfl.sort_values("_sort", ascending=sort_asc).drop(columns=["_sort"])
    else:
        col_map = {"Symbol":"Symbol","1D %":"1D %","1W %":"1W %","1M %":"1M %",
                   "RSI":"RSI","ADX":"ADX","Vol/Avg":"Vol/Avg"}
        sc = col_map.get(sort_col, "Symbol")
        dfl = dfl.sort_values(sc, ascending=sort_asc, na_position="last")

    # ── Build clean display DataFrame for st.dataframe
    _SIG_ICON = {
        "STRONG BUY":  "🔥 STRONG BUY",
        "BUY":         "✅ BUY",
        "HOLD":        "⏸  HOLD",
        "SELL":        "🔴 SELL",
        "STRONG SELL": "🆘 STRONG SELL",
        "—":           "—",
    }
    _MACD_ICON = {"↑ Bull": "↑ Bullish", "↓ Bear": "↓ Bearish"}
    _AI_ICON   = {"buy": "🤖 BUY", "sell": "🤖 SELL", "hold": "🤖 HOLD"}

    def _safe(v, default=None):
        if v is None: return default
        if isinstance(v, float) and np.isnan(v): return default
        return v

    ai_results = st.session_state.get("ai_results", {})

    tbl_rows = []
    for _, row in dfl.iterrows():
        sym = row["Symbol"]
        pos = positions.get(sym, {})
        held_str = (
            f'{pos["shares"]:.0f} sh  {"+" if pos["unrealized_plpc"]>=0 else ""}{pos["unrealized_plpc"]:.1f}%'
            if sym in positions else ""
        )
        ai = ai_results.get(sym, {})
        ai_action = _AI_ICON.get(ai.get("action",""), "") if ai else ""
        ai_conf   = round(ai.get("confidence", 0) * 100) if ai else None

        tbl_rows.append({
            "Signal":    _SIG_ICON.get(row["Signal"], row["Signal"]),
            "AI Signal": ai_action,
            "AI Conf %": ai_conf,
            "Symbol":    sym,
            "Category":  row["Category"],
            "Price":     _safe(row["Price"]),
            "1D %":      _safe(row["1D %"]),
            "1W %":      _safe(row["1W %"]),
            "1M %":      _safe(row["1M %"]),
            "RSI":       _safe(row["RSI"]),
            "MACD":      _MACD_ICON.get(row.get("MACD",""), row.get("MACD","")),
            "BB %":      _safe(row["BB Pos"]),
            "ADX":       _safe(row["ADX"]),
            "Vol/Avg":   _safe(row["Vol/Avg"]),
            "52W %":     _safe(row["52W Pos"]),
            "Position":  held_str,
        })

    if tbl_rows:
        tbl_df = pd.DataFrame(tbl_rows)

        # Colour-map % change columns via pandas Styler
        def _clr_pct(val):
            if val is None or not isinstance(val, (int, float)) or np.isnan(val):
                return ""
            return "color: #3fb950" if val >= 0 else "color: #f85149"

        def _clr_rsi(val):
            if val is None or not isinstance(val, (int, float)) or np.isnan(val):
                return ""
            if val > 70: return "color: #f85149; font-weight: bold"
            if val < 30: return "color: #3fb950; font-weight: bold"
            return "color: #e6edf3"

        styler = (
            tbl_df.style
            .applymap(_clr_pct, subset=["1D %", "1W %", "1M %"])
            .applymap(_clr_rsi, subset=["RSI"])
            .format({
                "Price":   lambda v: f"${v:.2f}" if v is not None and not np.isnan(v) else "—",
                "1D %":    lambda v: f"+{v:.2f}%" if (v is not None and not np.isnan(v) and v >= 0) else (f"{v:.2f}%" if v is not None and not np.isnan(v) else "—"),
                "1W %":    lambda v: f"+{v:.2f}%" if (v is not None and not np.isnan(v) and v >= 0) else (f"{v:.2f}%" if v is not None and not np.isnan(v) else "—"),
                "1M %":    lambda v: f"+{v:.2f}%" if (v is not None and not np.isnan(v) and v >= 0) else (f"{v:.2f}%" if v is not None and not np.isnan(v) else "—"),
                "RSI":     lambda v: f"{v:.0f}" if v is not None and not np.isnan(v) else "—",
                "BB %":    lambda v: f"{v:.0f}%" if v is not None and not np.isnan(v) else "—",
                "ADX":     lambda v: f"{v:.0f}" if v is not None and not np.isnan(v) else "—",
                "Vol/Avg": lambda v: f"{v:.1f}×" if v is not None and not np.isnan(v) else "—",
                "52W %":   lambda v: f"{v:.0f}%" if v is not None and not np.isnan(v) else "—",
            }, na_rep="—")
        )

        st.dataframe(
            styler,
            column_config={
                "Signal":    st.column_config.TextColumn("Tech Signal", width=155),
                "AI Signal": st.column_config.TextColumn("AI Signal",   width=105),
                "AI Conf %": st.column_config.ProgressColumn(
                                 "AI Conf", min_value=0, max_value=100,
                                 format="%d%%", width=90),
                "Symbol":    st.column_config.TextColumn("Symbol",      width=72),
                "Category":  st.column_config.TextColumn("Category",    width=140),
                "Price":     st.column_config.TextColumn("Price",       width=88),
                "1D %":      st.column_config.TextColumn("1D %",        width=78),
                "1W %":      st.column_config.TextColumn("1W %",        width=78),
                "1M %":      st.column_config.TextColumn("1M %",        width=78),
                "RSI":       st.column_config.ProgressColumn(
                                 "RSI (14)", min_value=0, max_value=100,
                                 format="%.0f", width=110),
                "MACD":      st.column_config.TextColumn("MACD",        width=100),
                "BB %":      st.column_config.ProgressColumn(
                                 "BB Band %", min_value=0, max_value=100,
                                 format="%.0f%%", width=110),
                "ADX":       st.column_config.NumberColumn("ADX",       width=60, format="%.0f"),
                "Vol/Avg":   st.column_config.TextColumn("Vol/Avg",     width=78),
                "52W %":     st.column_config.ProgressColumn(
                                 "52W Pos", min_value=0, max_value=100,
                                 format="%.0f%%", width=100),
                "Position":  st.column_config.TextColumn("Position",    width=130),
            },
            use_container_width=True,
            height=640,
            hide_index=True,
        )
    else:
        st.info("No stocks match the current filters.")

    # ── Mistral AI Scan ─────────────────────────────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<div class="sec-header">🤖 Mistral AI Analysis</div>', unsafe_allow_html=True)

    if not _MISTRAL_AVAILABLE:
        st.warning("mistralai package not installed. Run: `pip install mistralai`")
    else:
        ai_results = st.session_state.get("ai_results", {})

        c_scope, c_btn, c_clear = st.columns([3, 2, 1])
        with c_scope:
            scope = st.radio(
                "Scope", ["✅ BUY signals only", "🔥 STRONG BUY only", "All filtered stocks"],
                horizontal=True, key="ai_scope", label_visibility="collapsed")
        with c_btn:
            if scope == "✅ BUY signals only":
                candidates = dfl[dfl["Signal"].isin(["BUY", "STRONG BUY"])]["Symbol"].tolist()
            elif scope == "🔥 STRONG BUY only":
                candidates = dfl[dfl["Signal"] == "STRONG BUY"]["Symbol"].tolist()
            else:
                candidates = dfl["Symbol"].tolist()
            already_done = sum(1 for s in candidates if s in ai_results)
            btn_label = (
                f"🤖 Run on {len(candidates)} stocks"
                if already_done == 0
                else f"🤖 Re-run {len(candidates)} stocks ({already_done} cached)"
            )
            run_ai = st.button(btn_label, type="primary", key="run_ai_scan",
                               disabled=len(candidates) == 0)
        with c_clear:
            if st.button("🗑️ Clear AI", key="clear_ai"):
                st.session_state["ai_results"] = {}
                st.rerun()

        if run_ai and candidates:
            prog   = st.progress(0.0)
            status = st.empty()
            for i, sym in enumerate(candidates):
                status.markdown(
                    f'<div style="color:#8b949e;font-size:13px">Analyzing '
                    f'<b style="color:#e6edf3">{sym}</b> ({i+1}/{len(candidates)})…</div>',
                    unsafe_allow_html=True)
                df_sym = ohlcv_data.get(sym)
                if df_sym is not None and len(df_sym) >= 30:
                    df_ind = compute_indicators(df_sym)
                    tech   = _tech_data_for_mistral(df_ind)
                    pos    = positions.get(sym)
                    result = _run_mistral(sym, tech, pos)
                    st.session_state.setdefault("ai_results", {})[sym] = result
                prog.progress((i + 1) / len(candidates))
            prog.empty()
            status.empty()
            st.rerun()

        # Display cached results
        ai_results = st.session_state.get("ai_results", {})
        if ai_results:
            # Summary counters
            buys  = sum(1 for r in ai_results.values() if r.get("action") == "buy")
            sells = sum(1 for r in ai_results.values() if r.get("action") == "sell")
            holds = sum(1 for r in ai_results.values() if r.get("action") == "hold")
            st.markdown(
                f'<div style="display:flex;gap:16px;margin:8px 0 14px">'
                f'<span style="color:#3fb950;font-weight:700">🤖 BUY: {buys}</span>'
                f'<span style="color:#f85149;font-weight:700">🤖 SELL: {sells}</span>'
                f'<span style="color:#8b949e;font-weight:700">🤖 HOLD: {holds}</span>'
                f'<span style="color:#8b949e;font-size:12px;margin-left:8px">'
                f'{len(ai_results)} stocks analyzed</span></div>',
                unsafe_allow_html=True)

            # Sort: buys first, then sells, then holds
            _order = {"buy": 0, "sell": 1, "hold": 2}
            sorted_results = sorted(
                ai_results.items(),
                key=lambda kv: (_order.get(kv[1].get("action","hold"), 2),
                                -kv[1].get("confidence", 0)))

            # Show in 2-column grid
            left_col, right_col = st.columns(2)
            for idx, (sym, result) in enumerate(sorted_results):
                with (left_col if idx % 2 == 0 else right_col):
                    _ai_result_card(sym, result, show_full=False)
        else:
            st.markdown(
                '<div style="color:#8b949e;font-size:14px;padding:12px 0">'
                'Click <b>Run</b> above to get Mistral AI recommendations. '
                'Results are shown here and added as a column to the table above.</div>',
                unsafe_allow_html=True)

    # ── Charts
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<div class="sec-header">Analytics</div>', unsafe_allow_html=True)
    ch1, ch2 = st.columns(2)
    with ch1:
        st.plotly_chart(make_sector_chart(overview_df), use_container_width=True)
    with ch2:
        st.plotly_chart(make_returns_scatter(overview_df), use_container_width=True)


# ════════════════════════════════════════════════════════════════════════════════
# TAB 2  —  DEEP DIVE
# ════════════════════════════════════════════════════════════════════════════════
def tab_deep_dive(ohlcv_data: dict, positions: dict):
    c_sel, c_per, _, c_ref = st.columns([3, 2, 3, 1])
    with c_sel:
        symbol = st.selectbox(
            "Stock", config.STOCK_UNIVERSE,
            format_func=lambda s: f"{s}  —  {CATEGORIES.get(s,'')}", key="dd_sym")
    with c_per:
        period_label = st.selectbox("Period", list(PERIOD_OPTS.keys()), index=2, key="dd_period")
    with c_ref:
        st.markdown("<br>", unsafe_allow_html=True)
        refresh = st.button("🔄", key="dd_refresh", help="Clear cache & refresh")
    if refresh:
        st.cache_data.clear()
        st.rerun()

    period = PERIOD_OPTS[period_label]

    # ── Fetch data
    with st.spinner(f"Loading {symbol}…"):
        single_data = fetch_batch_ohlcv((symbol,), period=period)
        df_raw = single_data.get(symbol)
        fundamentals = fetch_fundamentals(symbol)

    if df_raw is None or len(df_raw) < 30:
        st.error(f"Not enough data for {symbol}. It may be delisted or the ticker may be incorrect.")
        return

    df = compute_indicators(df_raw)
    last = df.iloc[-1]
    close = float(last["close"])
    prev  = float(df["close"].iloc[-2]) if len(df) > 1 else close
    chg1d = (close - prev) / prev * 100
    chg_color = "#3fb950" if chg1d >= 0 else "#f85149"
    sig, score, conf = compute_signal(last)

    # ── Stock header
    cat = CATEGORIES.get(symbol, "—")
    cat_color = CAT_COLORS.get(cat, "#374151")
    fname = fundamentals.get("name", symbol)

    st.markdown(
        f'<div style="display:flex;align-items:center;gap:12px;margin-bottom:12px;">'
        f'<span style="font-size:32px;font-weight:800;color:#e6edf3">{symbol}</span>'
        f'<span class="cat" style="background:{cat_color}22;color:{cat_color};border:1px solid {cat_color}55;font-size:13px">{cat}</span>'
        f'<span style="color:#8b949e;font-size:15px">{fname}</span>'
        f'</div>',
        unsafe_allow_html=True)

    # ── Key stats
    w52hi  = fundamentals.get("52w_high") or float(df["close"].tail(252).max())
    w52lo  = fundamentals.get("52w_low")  or float(df["close"].tail(252).min())
    mktcap = fundamentals.get("market_cap")
    pe     = fundamentals.get("pe_trailing")
    pe_fwd = fundamentals.get("pe_forward")
    avg_vol= fundamentals.get("avg_volume") or float(df["vol_sma20"].iloc[-1]) if "vol_sma20" in df.columns else None

    vol_ratio = float(last.get("vol_ratio", 1)) if pd.notna(last.get("vol_ratio")) else None

    stat_cards = [
        ("Price",         f'<span style="font-size:28px;font-weight:700;color:#e6edf3">${close:.2f}</span>'
                          f'<span style="color:{chg_color};font-size:16px;margin-left:8px">{"+" if chg1d>=0 else ""}{chg1d:.2f}%</span>'),
        ("Market Cap",    fmt_large(mktcap)),
        ("P/E (TTM)",     f"{pe:.1f}" if pe else "—"),
        ("P/E (Fwd)",     f"{pe_fwd:.1f}" if pe_fwd else "—"),
        ("Volume",        f'{int(last["volume"]):,}<br><span style="color:#8b949e;font-size:11px">Avg: {int(avg_vol):,}</span>' if avg_vol else f'{int(last["volume"]):,}'),
        ("Vol/Avg",       f'<span style="color:{"#f59e0b" if vol_ratio and vol_ratio > 2 else "#e6edf3"}">{vol_ratio:.1f}x</span>' if vol_ratio else "—"),
        ("Signal",        signal_badge(sig) + f'<br><span style="color:#8b949e;font-size:11px">Score {score:+.1f} · {conf:.0%} conf</span>'),
        ("AI Analyst",    (fundamentals.get("analyst_recommendation") or "—").upper()
                          + (f'<br><span style="color:#8b949e;font-size:11px">Target: ${fundamentals["analyst_target"]:.2f} · {fundamentals["analyst_count"]} analysts</span>'
                             if fundamentals.get("analyst_target") and fundamentals.get("analyst_count") else "")),
    ]

    cols = st.columns(len(stat_cards))
    for col, (label, val) in zip(cols, stat_cards):
        col.markdown(
            f'<div class="metric-card"><div class="metric-label">{label}</div>'
            f'<div class="metric-value" style="font-size:18px">{val}</div></div>',
            unsafe_allow_html=True)

    # ── 52-week range bar
    if w52hi and w52lo and w52hi > w52lo:
        w52pos = (close - w52lo) / (w52hi - w52lo) * 100
        st.markdown(
            f'<div style="background:#161b22;border:1px solid #30363d;border-radius:8px;'
            f'padding:12px 16px;margin:10px 0">'
            f'<div style="display:flex;justify-content:space-between;margin-bottom:6px;">'
            f'<span style="color:#8b949e;font-size:12px">52-WEEK LOW  ${w52lo:.2f}</span>'
            f'<span style="color:#8b949e;font-size:12px">52-WEEK HIGH  ${w52hi:.2f}</span>'
            f'</div>'
            f'<div style="background:#21262d;border-radius:4px;height:6px;position:relative;">'
            f'<div style="background:linear-gradient(90deg,#1f6feb,#3fb950);'
            f'border-radius:4px;height:6px;width:{w52pos:.1f}%"></div>'
            f'<div style="position:absolute;top:-3px;left:{w52pos:.1f}%;'
            f'width:12px;height:12px;background:#e6edf3;border-radius:50%;margin-left:-6px"></div>'
            f'</div>'
            f'<div style="text-align:center;color:#e6edf3;font-size:12px;margin-top:6px">'
            f'Current ${close:.2f} · {w52pos:.1f}% of 52-week range</div>'
            f'</div>',
            unsafe_allow_html=True)

    # ── Position info
    if symbol in positions:
        pos = positions[symbol]
        pl_c = "#3fb950" if pos["unrealized_pl"] >= 0 else "#f85149"
        st.markdown(
            f'<div style="background:#0d2b1e;border:1px solid #238636;border-radius:8px;'
            f'padding:12px 16px;margin:8px 0;display:flex;gap:32px;align-items:center">'
            f'<span style="color:#3fb950;font-size:14px;font-weight:700">📌 HOLDING {pos["shares"]:.0f} shares</span>'
            f'<span style="color:#8b949e">Entry: <b style="color:#e6edf3">${pos["entry_price"]:.2f}</b></span>'
            f'<span style="color:#8b949e">Current: <b style="color:#e6edf3">${pos["current_price"]:.2f}</b></span>'
            f'<span style="color:#8b949e">Market Value: <b style="color:#e6edf3">${pos["market_value"]:,.0f}</b></span>'
            f'<span style="color:{pl_c};font-weight:700">P&L: {"+" if pos["unrealized_pl"]>=0 else ""}${pos["unrealized_pl"]:,.2f} '
            f'({"+" if pos["unrealized_plpc"]>=0 else ""}{pos["unrealized_plpc"]:.2f}%)</span>'
            f'</div>',
            unsafe_allow_html=True)

    # ── Chart options
    opt1, opt2, opt3 = st.columns([1,1,3])
    show_bb  = opt1.checkbox("Bollinger Bands", value=True, key="show_bb")
    show_sma = opt2.checkbox("Moving Averages", value=True, key="show_sma")

    # ── Main chart
    st.plotly_chart(make_price_chart(df, symbol, show_bb, show_sma), use_container_width=True)

    # ── Secondary charts
    sc1, sc2 = st.columns(2)
    with sc1:
        st.plotly_chart(make_stoch_adx_chart(df), use_container_width=True)
    with sc2:
        st.plotly_chart(make_bb_volatility_chart(df), use_container_width=True)

    # ── Technical indicators table
    st.markdown('<div class="sec-header">Technical Indicator Summary</div>', unsafe_allow_html=True)
    ti1, ti2, ti3 = st.columns(3)

    def stat_row(label, value):
        return (f'<div class="stat-row">'
                f'<span class="stat-label">{label}</span>'
                f'<span class="stat-value">{value}</span></div>')

    rsi_val = last.get("rsi", np.nan)
    rsi_label = ("Overbought" if rsi_val > 70 else "Oversold" if rsi_val < 30 else "Neutral") if pd.notna(rsi_val) else "—"
    rsi_clr = "#f85149" if (pd.notna(rsi_val) and rsi_val > 70) else ("#3fb950" if (pd.notna(rsi_val) and rsi_val < 30) else "#e6edf3")

    with ti1:
        st.markdown(
            f'<div style="background:#161b22;border:1px solid #30363d;border-radius:8px;padding:14px;">'
            + stat_row("RSI (14)", f'<span style="color:{rsi_clr}">{rsi_val:.1f} — {rsi_label}</span>' if pd.notna(rsi_val) else "—")
            + stat_row("Stoch %K", f'{last.get("stoch_k",np.nan):.1f}' if pd.notna(last.get("stoch_k")) else "—")
            + stat_row("Stoch %D", f'{last.get("stoch_d",np.nan):.1f}' if pd.notna(last.get("stoch_d")) else "—")
            + stat_row("ROC (10d)", f'{last.get("roc10",np.nan):.2f}%' if pd.notna(last.get("roc10")) else "—")
            + "</div>", unsafe_allow_html=True)

    with ti2:
        macd_v = last.get("macd", np.nan)
        msig_v = last.get("macd_signal", np.nan)
        macd_trend_str = "Bullish ↑" if (pd.notna(macd_v) and pd.notna(msig_v) and macd_v > msig_v) else "Bearish ↓"
        macd_clr = "#3fb950" if "Bull" in macd_trend_str else "#f85149"
        st.markdown(
            f'<div style="background:#161b22;border:1px solid #30363d;border-radius:8px;padding:14px;">'
            + stat_row("MACD", f'<span style="color:{macd_clr}">{macd_trend_str}</span>')
            + stat_row("MACD Value", f'{macd_v:.4f}' if pd.notna(macd_v) else "—")
            + stat_row("MACD Signal", f'{msig_v:.4f}' if pd.notna(msig_v) else "—")
            + stat_row("MACD Hist", f'{last.get("macd_hist",np.nan):.4f}' if pd.notna(last.get("macd_hist")) else "—")
            + stat_row("ADX (14)", f'{last.get("adx",np.nan):.1f} — {"Strong" if (pd.notna(last.get("adx")) and last["adx"]>25) else "Weak"} Trend' if pd.notna(last.get("adx")) else "—")
            + "</div>", unsafe_allow_html=True)

    with ti3:
        bb_pos_v  = last.get("bb_pos", np.nan)
        bb_label  = "Near Upper" if (pd.notna(bb_pos_v) and bb_pos_v > 0.8) else ("Near Lower" if (pd.notna(bb_pos_v) and bb_pos_v < 0.2) else "Middle")
        sma50_v   = last.get("sma50", np.nan)
        sma200_v  = last.get("sma200", np.nan)
        cross_str = "Golden Cross ↑" if (pd.notna(sma50_v) and pd.notna(sma200_v) and sma50_v > sma200_v) else "Death Cross ↓"
        cross_clr = "#3fb950" if "Golden" in cross_str else "#f85149"
        st.markdown(
            f'<div style="background:#161b22;border:1px solid #30363d;border-radius:8px;padding:14px;">'
            + stat_row("BB Position", f'{bb_pos_v*100:.1f}% — {bb_label}' if pd.notna(bb_pos_v) else "—")
            + stat_row("BB Width", f'{last.get("bb_width",np.nan)*100:.2f}%' if pd.notna(last.get("bb_width")) else "—")
            + stat_row("ATR (14)", f'${last.get("atr",np.nan):.3f}' if pd.notna(last.get("atr")) else "—")
            + stat_row("Hist Volatility 20d", f'{last.get("volatility",np.nan)*100:.1f}%' if pd.notna(last.get("volatility")) else "—")
            + stat_row("SMA50/200 Cross", f'<span style="color:{cross_clr}">{cross_str}</span>')
            + "</div>", unsafe_allow_html=True)

    # ── Fundamentals
    st.markdown('<div class="sec-header">Fundamentals</div>', unsafe_allow_html=True)
    fn1, fn2, fn3 = st.columns(3)

    def sect(title, *rows):
        inner = "".join(stat_row(l,v) for l, v in rows)
        return (f'<div style="background:#161b22;border:1px solid #30363d;border-radius:8px;padding:14px;">'
                f'<div style="color:#8b949e;font-size:11px;text-transform:uppercase;'
                f'letter-spacing:.08em;margin-bottom:8px">{title}</div>'
                + inner + "</div>")

    with fn1:
        st.markdown(sect("Valuation",
            ("Market Cap",    fmt_large(fundamentals.get("market_cap"))),
            ("P/E Trailing",  fmt_val(fundamentals.get("pe_trailing"), ".1f")),
            ("P/E Forward",   fmt_val(fundamentals.get("pe_forward"), ".1f")),
            ("EPS (TTM)",     fmt_val(fundamentals.get("eps_ttm"), ".2f", "$")),
            ("Price/Book",    fmt_val(fundamentals.get("price_to_book"), ".2f")),
            ("Price/Sales",   "—"),
            ("Beta",          fmt_val(fundamentals.get("beta"), ".2f")),
            ("Div Yield",     fmt_pct(fundamentals.get("dividend_yield"))),
        ), unsafe_allow_html=True)

    with fn2:
        st.markdown(sect("Financials",
            ("Revenue (TTM)",   fmt_large(fundamentals.get("revenue"))),
            ("Rev Growth (YoY)",fmt_pct(fundamentals.get("revenue_growth"))),
            ("EPS Growth",      fmt_pct(fundamentals.get("earnings_growth"))),
            ("Free Cash Flow",  fmt_large(fundamentals.get("free_cash_flow"))),
            ("Profit Margin",   fmt_pct(fundamentals.get("profit_margin"))),
            ("Operating Margin",fmt_pct(fundamentals.get("operating_margin"))),
            ("Return on Equity",fmt_pct(fundamentals.get("roe"))),
            ("Return on Assets",fmt_pct(fundamentals.get("roa"))),
        ), unsafe_allow_html=True)

    with fn3:
        st.markdown(sect("Balance Sheet & Risk",
            ("Debt/Equity",     fmt_val(fundamentals.get("debt_to_equity"), ".2f")),
            ("Current Ratio",   fmt_val(fundamentals.get("current_ratio"), ".2f")),
            ("Quick Ratio",     fmt_val(fundamentals.get("quick_ratio"), ".2f")),
            ("Shares Outstanding", fmt_large(fundamentals.get("shares_outstanding"))),
            ("Float",           fmt_large(fundamentals.get("float_shares"))),
            ("Short Ratio",     fmt_val(fundamentals.get("short_ratio"), ".1f")),
            ("Book Value/Share",fmt_val(fundamentals.get("book_value"), ".2f", "$")),
            ("Employees",       f'{fundamentals.get("employees"):,}' if fundamentals.get("employees") else "—"),
        ), unsafe_allow_html=True)

    # ── Mistral AI Analysis
    st.markdown('<div class="sec-header">🤖 Mistral AI Analysis</div>', unsafe_allow_html=True)

    if not _MISTRAL_AVAILABLE:
        st.warning("mistralai package not installed.")
    else:
        ai_key = f"ai_{symbol}"
        cached = st.session_state.get("ai_results", {}).get(symbol)

        c1, c2 = st.columns([2, 6])
        with c1:
            run_btn = st.button("🤖 Ask Mistral", key=f"ask_{symbol}", type="primary")
        with c2:
            if cached:
                ts = st.session_state.get(f"ai_ts_{symbol}", "")
                st.markdown(
                    f'<div style="color:#8b949e;font-size:12px;padding-top:8px">'
                    f'Last run: {ts}</div>',
                    unsafe_allow_html=True)

        if run_btn:
            with st.spinner(f"Asking Mistral to analyze {symbol}…"):
                tech   = _tech_data_for_mistral(df)
                pos    = positions.get(symbol)
                result = _run_mistral(symbol, tech, pos)
                st.session_state.setdefault("ai_results", {})[symbol] = result
                st.session_state[f"ai_ts_{symbol}"] = datetime.now().strftime("%H:%M:%S")
                cached = result

        if cached:
            _ai_result_card(symbol, cached, show_full=True)

            # Extra detail expander
            with st.expander("Full reasoning", expanded=False):
                st.markdown(
                    f'<div style="color:#c9d1d9;font-size:14px;line-height:1.7">'
                    f'{cached.get("reasoning","")}</div>',
                    unsafe_allow_html=True)
        else:
            st.markdown(
                '<div style="color:#8b949e;font-size:14px;padding:8px 0">'
                'Click <b>Ask Mistral</b> to get an AI recommendation with '
                'entry price, stop loss, take profit, and reasoning.</div>',
                unsafe_allow_html=True)

    # ── Company description
    desc = fundamentals.get("description", "")
    if desc:
        st.markdown('<div class="sec-header">About</div>', unsafe_allow_html=True)
        with st.expander("Read full description", expanded=False):
            st.markdown(
                f'<div style="color:#c9d1d9;font-size:14px;line-height:1.7">{desc}</div>',
                unsafe_allow_html=True)

    # ── News
    st.markdown('<div class="sec-header">Latest News</div>', unsafe_allow_html=True)
    with st.spinner("Fetching news…"):
        news_av = fetch_news_av(symbol)
        news_yf = fetch_news_yf(symbol) if not news_av else []
    news = news_av or news_yf

    if news:
        source_label = "Alpha Vantage" if news_av else "Yahoo Finance"
        st.caption(f"Source: {source_label} · {len(news)} articles")
        for article in news:
            sent_score = article.get("ticker_score") or article.get("sentiment_score")
            sent_label = article.get("sentiment_label", "")
            if sent_score is not None:
                sc = float(sent_score)
                sent_clr = "#3fb950" if sc > 0.1 else ("#f85149" if sc < -0.1 else "#8b949e")
                sent_str = f'<span style="color:{sent_clr};font-weight:600">{sent_label or f"{sc:+.2f}"}</span>'
            else:
                sent_str = ""

            summary = article.get("summary", "")
            summary_html = f'<div class="news-summary">{summary[:280]}{"…" if len(summary) > 280 else ""}</div>' if summary else ""
            url = article.get("url","#")

            st.markdown(
                f'<div class="news-card">'
                f'<div style="display:flex;justify-content:space-between;align-items:flex-start">'
                f'<a href="{url}" target="_blank" style="color:#58a6ff;font-weight:600;font-size:14px;'
                f'text-decoration:none;flex:1;padding-right:12px">{article["title"]}</a>'
                f'{sent_str}'
                f'</div>'
                f'<div class="news-meta">{article.get("source","")} · {article.get("published","")}</div>'
                + summary_html +
                f'</div>',
                unsafe_allow_html=True)
    else:
        st.info("No news available for this stock.")


# ════════════════════════════════════════════════════════════════════════════════
# MAIN
# ════════════════════════════════════════════════════════════════════════════════
def main():
    # ── Header
    h1, h2 = st.columns([8, 1])
    with h1:
        st.markdown(
            '<h1 style="margin:0;color:#e6edf3;font-size:28px;font-weight:800">'
            '📈 AI Trading Dashboard</h1>'
            f'<div style="color:#8b949e;font-size:13px;margin-top:2px">'
            f'Last updated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")} · '
            f'{len(config.STOCK_UNIVERSE)} stocks tracked</div>',
            unsafe_allow_html=True)
    with h2:
        if st.button("🔄 Refresh All", key="refresh_all"):
            st.cache_data.clear()
            st.rerun()

    st.markdown("<hr style='border-color:#30363d;margin:12px 0'>", unsafe_allow_html=True)

    # ── Session state init
    if "ai_results" not in st.session_state:
        st.session_state["ai_results"] = {}

    # ── Load shared data once
    with st.spinner("Fetching market data for all stocks…"):
        all_syms = tuple(config.STOCK_UNIVERSE)
        ohlcv_data = fetch_batch_ohlcv(all_syms, period="1y")

    account   = get_alpaca_account()
    positions = get_alpaca_positions()
    market_open = get_market_status()

    # ── Tabs
    tab1, tab2 = st.tabs(["  Portfolio Overview  ", "  Deep Dive  "])
    with tab1:
        tab_overview(ohlcv_data, positions, account, market_open)
    with tab2:
        tab_deep_dive(ohlcv_data, positions)


if __name__ == "__main__":
    import streamlit.runtime
    if streamlit.runtime.exists():
        # Already inside Streamlit — just run the app
        main()
    else:
        # Called via `python dashboard.py` — launch Streamlit automatically
        import subprocess, sys
        sys.exit(subprocess.run([
            sys.executable, "-m", "streamlit", "run", __file__,
            "--server.port", "8502",
            "--browser.gatherUsageStats", "false",
        ]).returncode)
