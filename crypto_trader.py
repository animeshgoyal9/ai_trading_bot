"""
Crypto Trader - BTC & ETH Paper Trading on Alpaca
Runs every 5 minutes, executes paper trades, tracks performance.
"""
import csv
import os
import time
import json
from datetime import datetime, timedelta
from typing import Optional

import alpaca_trade_api as tradeapi
import pandas as pd
from loguru import logger

import config
from mistral_agent import MistralTrader
from feature_engineering import FeatureEngine
from notify import send_trade_alert

# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------
SYMBOLS = ['BTC/USD', 'ETH/USD', 'SOL/USD', 'XRP/USD']
INTERVAL_SECONDS   = 10800     # 3 hours
NOTIONAL_PER_TRADE = 500       # dollars to spend per BUY (adjust freely)
MIN_CONFIDENCE     = 0.50      # only act if Claude >= 50% confident
PERFORMANCE_LOG    = 'logs/crypto_performance.csv'

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def fetch_data(api, alpaca_symbol: str) -> Optional[pd.DataFrame]:
    """Fetch 60d hourly OHLCV from Alpaca crypto bars API."""
    try:
        end   = datetime.utcnow()
        start = end - timedelta(days=60)
        response = api.get_crypto_bars(
            [alpaca_symbol],
            '1Hour',
            start=start.strftime('%Y-%m-%dT%H:%M:%SZ'),
            end=end.strftime('%Y-%m-%dT%H:%M:%SZ'),
        )
        # Build DataFrame from bar objects
        bar_list = list(response)
        if not bar_list:
            return None
        rows = [{'date': b.t, 'open': b.o, 'high': b.h,
                 'low': b.l, 'close': b.c, 'volume': b.v}
                for b in bar_list]
        if not rows:
            return None
        df = pd.DataFrame(rows).set_index('date')
        df.index.name = 'date'
        return df
    except Exception as e:
        logger.error(f'Alpaca crypto bars error for {alpaca_symbol}: {e}')
        return None


def get_current_price(api, alpaca_symbol: str) -> Optional[float]:
    """Get latest crypto price from Alpaca."""
    try:
        # Use get_latest_crypto_trades (plural) — supported in current SDK
        trades = api.get_latest_crypto_trades([alpaca_symbol])
        trade = trades.get(alpaca_symbol)
        if trade:
            return float(trade.price)
    except Exception:
        pass
    # Fallback: use most recent bar close price
    try:
        from datetime import datetime, timedelta
        end   = datetime.utcnow()
        start = end - timedelta(hours=2)
        bars  = list(api.get_crypto_bars(
            [alpaca_symbol], '1Min',
            start=start.strftime('%Y-%m-%dT%H:%M:%SZ'),
            end=end.strftime('%Y-%m-%dT%H:%M:%SZ'),
        ))
        if bars:
            return float(bars[-1].c)
    except Exception as e:
        logger.error(f'Could not get price for {alpaca_symbol}: {e}')
    return None


def get_positions(api, retries: int = 4) -> Optional[dict]:
    """Return open positions keyed by symbol, normalised to BTC/USD format.
    Returns None if all retries fail (caller should skip the cycle, not assume no positions)."""
    for attempt in range(1, retries + 1):
        try:
            positions = {}
            for pos in api.list_positions():
                sym = pos.symbol  # may be BTCUSD or BTC/USD
                if '/' not in sym:
                    for quote in ('USDT', 'USD'):
                        if sym.endswith(quote):
                            sym = sym[:-len(quote)] + '/' + quote
                            break
                positions[sym] = {
                    'qty':             float(pos.qty),
                    'entry_price':     float(pos.avg_entry_price),
                    'current_price':   float(pos.current_price),
                    'market_value':    float(pos.market_value),
                    'unrealized_pl':   float(pos.unrealized_pl),
                    'unrealized_plpc': float(pos.unrealized_plpc),
                }
            return positions
        except Exception as e:
            logger.warning(f'get_positions attempt {attempt}/{retries} failed: {e}')
            if attempt < retries:
                time.sleep(5 * attempt)   # 5s, 10s, 15s backoff
    logger.error('get_positions failed after all retries — skipping cycle to avoid phantom buys')
    return None


def place_buy(api, alpaca_symbol: str, notional: float) -> bool:
    """Buy $notional worth of crypto."""
    try:
        api.submit_order(
            symbol=alpaca_symbol,
            notional=round(notional, 2),
            side='buy',
            type='market',
            time_in_force='gtc',
        )
        logger.info(f'BUY order placed: ${notional:.0f} of {alpaca_symbol}')
        return True
    except Exception as e:
        logger.error(f'BUY failed for {alpaca_symbol}: {e}')
        return False


def place_sell(api, alpaca_symbol: str, qty: float) -> bool:
    """Sell the full position."""
    try:
        api.submit_order(
            symbol=alpaca_symbol,
            qty=qty,
            side='sell',
            type='market',
            time_in_force='gtc',
        )
        logger.info(f'SELL order placed: {qty} {alpaca_symbol}')
        return True
    except Exception as e:
        logger.error(f'SELL failed for {alpaca_symbol}: {e}')
        return False


# ---------------------------------------------------------------------------
# Performance logging
# ---------------------------------------------------------------------------

def log_trade(symbol: str, side: str, price: float, qty: float,
              confidence: float, reasoning: str):
    os.makedirs('logs', exist_ok=True)
    file_exists = os.path.exists(PERFORMANCE_LOG)
    with open(PERFORMANCE_LOG, 'a', newline='') as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(['timestamp', 'symbol', 'side', 'price', 'qty',
                             'notional', 'confidence', 'reasoning'])
        writer.writerow([
            datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            symbol, side, f'{price:.4f}', f'{qty:.6f}',
            f'{price * qty:.2f}', f'{confidence:.2%}',
            reasoning[:200],
        ])


def print_performance(api):
    """Show account equity and a summary of logged trades."""
    try:
        acct = api.get_account()
        equity   = float(acct.equity)
        cash     = float(acct.cash)
        pl_today = float(acct.equity) - float(acct.last_equity)
        print(f'\n  Account  |  Equity: ${equity:,.2f}  |  Cash: ${cash:,.2f}'
              f'  |  P&L today: ${pl_today:+,.2f}')
    except Exception as e:
        print(f'\n  (Could not fetch account info: {e})')

    if not os.path.exists(PERFORMANCE_LOG):
        print('  No trades executed yet.')
        return

    try:
        df = pd.read_csv(PERFORMANCE_LOG)
        buys  = df[df['side'] == 'buy']
        sells = df[df['side'] == 'sell']
        print(f'  Trades logged  |  Buys: {len(buys)}  |  Sells: {len(sells)}')
        print(f'  Log: {PERFORMANCE_LOG}')
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------

def run():
    # Connect to Alpaca
    api = tradeapi.REST(
        config.ALPACA_API_KEY,
        config.ALPACA_SECRET_KEY,
        config.ALPACA_BASE_URL,
        api_version='v2',
    )
    acct = api.get_account()
    print(f'\nConnected to Alpaca ({acct.status}) — paper trading')
    print(f'Starting equity: ${float(acct.equity):,.2f}')

    claude       = MistralTrader()
    feature_eng  = FeatureEngine(use_sentiment=False)

    run_number = 0
    while True:
        run_number += 1
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print()
        print('=' * 70)
        print(f'  CRYPTO TRADER  |  Run #{run_number}  |  {now}')
        print('=' * 70)

        positions = get_positions(api)
        if positions is None:
            print('  Skipping cycle — could not fetch positions safely.')
            continue

        for alpaca_sym in SYMBOLS:
            name = alpaca_sym.replace('/USD', '')
            print(f'\n[{name}]')

            # --- Data ---
            df = fetch_data(api, alpaca_sym)
            if df is None or len(df) < 30:
                print('  Skipping — not enough data.')
                continue

            try:
                df = feature_eng.add_technical_indicators(df)
            except Exception as e:
                print(f'  Skipping — indicator error: {e}')
                continue

            current_price = get_current_price(api, alpaca_sym)
            if current_price is None:
                current_price = float(df['close'].iloc[-1])

            latest = df.iloc[-1].to_dict()
            latest['current_price'] = current_price

            has_position = alpaca_sym in positions
            position     = positions.get(alpaca_sym)

            if has_position:
                pnl     = position['unrealized_pl']
                pnl_pct = position['unrealized_plpc'] * 100
                print(f'  Position  |  {position["qty"]:.6f} units @ ${position["entry_price"]:,.2f}'
                      f'  |  P&L: ${pnl:+,.2f} ({pnl_pct:+.1f}%)')
            else:
                print(f'  No open position')

            print(f'  Price: ${current_price:,.2f}')

            # --- Claude decision ---
            print('  Asking Claude...')
            try:
                decision = claude.analyze_and_decide(
                    symbol=alpaca_sym,
                    technical_data=latest,
                    market_context={'market_trend': 'Crypto — 24/7 market'},
                    current_position=position,
                )
            except Exception as e:
                print(f'  Claude error: {e}')
                continue

            action     = decision['action'].lower()
            confidence = decision['confidence']
            risk       = decision['risk_level']
            reasoning  = decision['reasoning']

            icon = {'buy': '🟢 BUY', 'sell': '🔴 SELL', 'hold': '🟡 HOLD'}.get(action, action.upper())
            print(f'  Decision  |  {icon}  |  Confidence: {confidence:.0%}  |  Risk: {risk}')
            print(f'  Reasoning : {reasoning[:250]}{"..." if len(reasoning) > 250 else ""}')

            # --- Execute ---
            if confidence < MIN_CONFIDENCE:
                print(f'  Skipping — confidence {confidence:.0%} below threshold {MIN_CONFIDENCE:.0%}')
                continue

            if action == 'buy' and not has_position:
                ok = place_buy(api, alpaca_sym, NOTIONAL_PER_TRADE)
                if ok:
                    qty = NOTIONAL_PER_TRADE / current_price
                    log_trade(alpaca_sym, 'buy', current_price, qty, confidence, reasoning)
                    print(f'  Executed BUY  ~${NOTIONAL_PER_TRADE:.0f} worth')
                    send_trade_alert(alpaca_sym, 'buy', current_price, confidence,
                                     reasoning, notional=NOTIONAL_PER_TRADE)

            elif action == 'sell' and has_position:
                ok = place_sell(api, alpaca_sym, position['qty'])
                if ok:
                    log_trade(alpaca_sym, 'sell', current_price, position['qty'], confidence, reasoning)
                    print(f'  Executed SELL  {position["qty"]:.6f} units')
                    send_trade_alert(alpaca_sym, 'sell', current_price, confidence,
                                     reasoning, qty=position['qty'])

            else:
                if action == 'buy' and has_position:
                    print(f'  Holding — already have a position')
                elif action == 'sell' and not has_position:
                    print(f'  No position to sell')

        # --- Performance summary ---
        print_performance(api)

        next_run = datetime.fromtimestamp(time.time() + INTERVAL_SECONDS).strftime('%H:%M:%S')
        print(f'\n  Next run at {next_run} — Ctrl+C to stop')
        print('=' * 70)

        # Wall-clock sleep: wake every 60s and check if interval has elapsed.
        # This survives macOS lid-close / system sleep (time.sleep freezes on sleep).
        wake_at = time.time() + INTERVAL_SECONDS
        try:
            while time.time() < wake_at:
                time.sleep(60)
        except KeyboardInterrupt:
            print('\nStopped.')
            break


if __name__ == '__main__':
    run()
