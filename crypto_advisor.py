"""
Crypto Advisor - BTC & ETH Buy/Sell Recommendations
Runs every 5 minutes, never executes trades — advisory only.
"""
import time
import yfinance as yf
import pandas as pd
from datetime import datetime
from loguru import logger

from claude_agent import ClaudeTrader
from feature_engineering import FeatureEngine

SYMBOLS = {
    'BTC-USD': 'Bitcoin',
    'ETH-USD': 'Ethereum',
}

INTERVAL_SECONDS = 300  # 5 minutes


def fetch_crypto_data(symbol, period='60d', interval='1h'):
    """Fetch crypto OHLCV data from yfinance."""
    ticker = yf.Ticker(symbol)
    df = ticker.history(period=period, interval=interval)
    if df.empty:
        return None
    df.columns = df.columns.str.lower()
    df.index.name = 'date'
    return df


def analyze_crypto():
    claude = ClaudeTrader()
    feature_engine = FeatureEngine(use_sentiment=False)

    run = 0
    while True:
        run += 1
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print()
        print('=' * 70)
        print(f'  CRYPTO ADVISOR  |  Run #{run}  |  {now}')
        print('=' * 70)

        for symbol, name in SYMBOLS.items():
            print(f'\n[{name} / {symbol}]')

            # Fetch data
            df = fetch_crypto_data(symbol)
            if df is None or len(df) < 30:
                print('  ERROR: Not enough data — skipping.')
                continue

            # Calculate indicators
            try:
                df = feature_engine.add_technical_indicators(df)
            except Exception as e:
                print(f'  ERROR computing indicators: {e}')
                continue

            latest = df.iloc[-1].to_dict()
            current_price = latest.get('close', 0)
            latest['current_price'] = current_price

            print(f'  Price : ${current_price:,.2f}')
            if 'rsi' in latest:
                rsi = latest['rsi']
                rsi_tag = ' (OVERSOLD)' if rsi < 30 else ' (OVERBOUGHT)' if rsi > 70 else ''
                print(f'  RSI   : {rsi:.1f}{rsi_tag}')
            if 'macd' in latest and 'macd_signal' in latest:
                direction = 'Bullish' if latest['macd'] > latest['macd_signal'] else 'Bearish'
                print(f'  MACD  : {direction}')

            # Ask Claude
            print('  Asking Claude...')
            try:
                decision = claude.analyze_and_decide(
                    symbol=symbol,
                    technical_data=latest,
                    market_context={'market_trend': 'Crypto — 24/7 market'},
                )
            except Exception as e:
                print(f'  ERROR from Claude: {e}')
                continue

            action = decision['action'].upper()
            confidence = decision['confidence']
            risk = decision['risk_level']
            reasoning = decision['reasoning']

            action_icon = {'BUY': '🟢 BUY', 'SELL': '🔴 SELL', 'HOLD': '🟡 HOLD'}.get(action, action)

            print()
            print(f'  Recommendation : {action_icon}')
            print(f'  Confidence     : {confidence:.0%}')
            print(f'  Risk Level     : {risk}')
            print(f'  Reasoning      : {reasoning[:300]}{"..." if len(reasoning) > 300 else ""}')

        next_run = datetime.fromtimestamp(time.time() + INTERVAL_SECONDS).strftime('%H:%M:%S')
        print()
        print(f'  Next check at {next_run} (every {INTERVAL_SECONDS // 60} min) — Ctrl+C to stop')
        print('=' * 70)

        try:
            time.sleep(INTERVAL_SECONDS)
        except KeyboardInterrupt:
            print('\nStopped.')
            break


if __name__ == '__main__':
    analyze_crypto()
