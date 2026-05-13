"""
Claude-Powered Trading Bot
Uses Claude AI agent to make intelligent trading decisions
"""
import alpaca_trade_api as tradeapi
from datetime import datetime, timedelta
import pytz
import numpy as np
import pandas as pd
from loguru import logger
import time as time_module
import config
from risk_management import RiskManager
from mistral_agent import MistralTrader
from data_collector import DataCollector
from feature_engineering import FeatureEngine
from notify import send_trade_alert


class ClaudeTradingBot:
    """Trading bot powered by Claude AI agent"""

    def __init__(self):
        """Initialize Claude-powered trading bot"""

        # Initialize Claude agent
        logger.info("Initializing Claude AI Trading Agent...")
        self.claude_trader = MistralTrader()

        # Initialize data collector and feature engine
        self.data_collector = DataCollector()
        self.feature_engine = FeatureEngine(use_sentiment=False)  # Claude handles reasoning
        self.risk_manager = RiskManager(config.TRADING_CAPITAL)

        # Initialize Alpaca API
        try:
            self.api = tradeapi.REST(
                config.ALPACA_API_KEY,
                config.ALPACA_SECRET_KEY,
                config.ALPACA_BASE_URL,
                api_version='v2'
            )
            account = self.api.get_account()
            logger.info(f"Connected to Alpaca. Account status: {account.status}")
            logger.info(f"Buying power: ${float(account.buying_power):,.2f}")
        except Exception as e:
            logger.error(f"Failed to connect to Alpaca: {e}")
            raise

        self.positions = {}
        self.orders = {}
        self.recently_sold = {}   # {symbol: datetime} — cooldown after selling

    def is_market_open(self):
        """Check if market is open for trading (regular or extended hours)."""
        try:
            if config.ENABLE_EXTENDED_HOURS:
                # Extended hours: pre-market 4 AM – 9:30 AM ET, after-hours 4 PM – 8 PM ET
                et = pytz.timezone('America/New_York')
                now = datetime.now(et)
                t = now.hour * 60 + now.minute  # minutes since midnight ET
                # Pre-market: 4:00 AM (240) – 9:30 AM (570)
                # Regular:    9:30 AM (570) – 4:00 PM (960)
                # After-hours: 4:00 PM (960) – 8:00 PM (1200)
                if 240 <= t < 1200 and now.weekday() < 5:  # Mon–Fri only
                    return True
            clock = self.api.get_clock()
            return clock.is_open
        except Exception as e:
            logger.error(f"Error checking market status: {e}")
            return False

    def get_account_info(self):
        """Get current account information"""
        try:
            account = self.api.get_account()
            return {
                'equity': float(account.equity),
                'cash': float(account.cash),
                'buying_power': float(account.buying_power),
                'portfolio_value': float(account.portfolio_value)
            }
        except Exception as e:
            logger.error(f"Error getting account info: {e}")
            return None

    def get_current_positions(self):
        """Get current open positions"""
        try:
            positions = self.api.list_positions()
            position_dict = {}

            for pos in positions:
                position_dict[pos.symbol] = {
                    'shares': int(pos.qty),
                    'entry_price': float(pos.avg_entry_price),
                    'current_price': float(pos.current_price),
                    'market_value': float(pos.market_value),
                    'unrealized_pl': float(pos.unrealized_pl),
                    'unrealized_plpc': float(pos.unrealized_plpc)
                }

            return position_dict
        except Exception as e:
            logger.error(f"Error getting positions: {e}")
            return {}

    def get_current_price(self, symbol):
        """Get current real-time price for a symbol"""
        try:
            trade = self.api.get_latest_trade(symbol)
            return float(trade.price)
        except Exception as e:
            logger.error(f"Error getting current price for {symbol}: {e}")
            return None

    def get_latest_bars(self, symbols, timeframe='1Day', limit=100):
        """Get latest price bars for symbols"""
        try:
            from datetime import datetime, timedelta

            # Fetch 450 calendar days (~310 trading days) — enough for SMA-200 warmup
            # Do NOT pass limit to Alpaca; rely on start/end dates so we always get
            # the most recent bars, not the oldest ones.
            end = datetime.now()
            start = end - timedelta(days=450)

            start_str = start.strftime('%Y-%m-%dT%H:%M:%SZ')
            end_str = end.strftime('%Y-%m-%dT%H:%M:%SZ')

            logger.info(f"Requesting stock data from {start.date()} to {end.date()}")

            barset = self.api.get_bars(
                symbols,
                timeframe,
                start=start_str,
                end=end_str,
            )
            bars_dict = {}

            for symbol in symbols:
                symbol_bars = [bar for bar in barset if bar.S == symbol]
                if symbol_bars:
                    import pandas as pd
                    df = pd.DataFrame([{
                        'date': bar.t,
                        'open': bar.o,
                        'high': bar.h,
                        'low': bar.l,
                        'close': bar.c,
                        'volume': bar.v
                    } for bar in symbol_bars])
                    df.set_index('date', inplace=True)
                    bars_dict[symbol] = df

            return bars_dict
        except Exception as e:
            logger.error(f"Error getting bars: {e}")
            return {}

    def analyze_with_claude(self, symbol, df, current_position=None):
        """
        Get Claude's analysis and trading decision

        Args:
            symbol: Stock symbol
            df: DataFrame with OHLCV data (may already have indicators)
            current_position: Optional dict with current position info

        Returns:
            Claude's decision dict
        """
        try:
            # Only calculate indicators if not already done (avoid double calculation)
            if 'rsi' not in df.columns:
                df = self.feature_engine.add_technical_indicators(df)

            # Get latest row as dict
            latest = df.iloc[-1].to_dict()
            latest['current_price'] = latest['close']

            # Get market context
            market_context = self._get_market_context()

            # Ask Claude to analyze
            logger.info(f"Asking Claude to analyze {symbol}...")
            decision = self.claude_trader.analyze_and_decide(
                symbol=symbol,
                technical_data=latest,
                market_context=market_context,
                current_position=current_position
            )

            return decision

        except Exception as e:
            logger.error(f"Error analyzing with Claude: {e}")
            return {
                'action': 'hold',
                'confidence': 0.0,
                'reasoning': f'Error: {str(e)}',
                'risk_level': 'high'
            }

    def _get_market_context(self):
        """Get overall market context for Claude using Alpaca (avoids yfinance rate limits)"""
        try:
            from datetime import timedelta

            # Get SPY data from Alpaca for market trend
            end = datetime.now()
            start = end - timedelta(days=10)
            start_str = start.strftime('%Y-%m-%dT%H:%M:%SZ')
            end_str = end.strftime('%Y-%m-%dT%H:%M:%SZ')

            spy_bars = self.api.get_bars('SPY', '1Day', start=start_str, end=end_str, limit=5)
            spy_data = list(spy_bars)

            if len(spy_data) >= 2:
                spy_change = (spy_data[-1].c - spy_data[-2].c) / spy_data[-2].c
                market_trend = "Bullish" if spy_change > 0.01 else "Bearish" if spy_change < -0.01 else "Neutral"
            else:
                spy_change = 0
                market_trend = "Neutral"

            return {
                'market_trend': market_trend,
                'spy_change': spy_change * 100
            }

        except Exception as e:
            logger.warning(f"Error getting market context: {e}")
            return {}

    def is_extended_hours(self):
        """True if we are outside regular session (4 AM–9:30 AM or 4 PM–8 PM ET)."""
        try:
            clock = self.api.get_clock()
            if clock.is_open:
                return False  # regular session
        except Exception:
            pass
        if config.ENABLE_EXTENDED_HOURS:
            et = pytz.timezone('America/New_York')
            now = datetime.now(et)
            t = now.hour * 60 + now.minute
            if now.weekday() < 5 and (240 <= t < 570 or 960 <= t < 1200):
                return True
        return False

    def place_order(self, symbol, qty, side='buy', order_type='market'):
        """Place an order. Uses limit orders during extended hours (Alpaca requirement)."""
        try:
            if self.is_extended_hours():
                # Extended hours requires limit orders
                bars = self.api.get_bars(symbol, '1Min', limit=1).df
                last_price = float(bars['close'].iloc[-1]) if not bars.empty else None
                if last_price is None:
                    logger.warning(f"Cannot get price for {symbol} — skipping extended hours order")
                    return None
                # Use a slightly aggressive limit to improve fill probability
                limit_price = round(last_price * 1.002 if side == 'buy' else last_price * 0.998, 2)
                order = self.api.submit_order(
                    symbol=symbol,
                    qty=qty,
                    side=side,
                    type='limit',
                    limit_price=limit_price,
                    time_in_force='day',
                    extended_hours=True,
                )
                logger.info(f"Extended hours order: {side.upper()} {qty} {symbol} @ limit ${limit_price}")
            else:
                order = self.api.submit_order(
                    symbol=symbol,
                    qty=qty,
                    side=side,
                    type=order_type,
                    time_in_force='day',
                )
                logger.info(f"Order placed: {side.upper()} {qty} {symbol} @ {order_type}")
            return order
        except Exception as e:
            logger.error(f"Error placing order: {e}")
            return None

    def place_bracket_order(self, symbol, qty, entry_price):
        """Place bracket order with stop loss and take profit"""
        try:
            stop_loss = self.risk_manager.calculate_stop_loss(entry_price)
            take_profit = self.risk_manager.calculate_take_profit(entry_price)

            order = self.api.submit_order(
                symbol=symbol,
                qty=qty,
                side='buy',
                type='market',
                time_in_force='day',
                order_class='bracket',
                stop_loss={'stop_price': stop_loss},
                take_profit={'limit_price': take_profit}
            )

            logger.info(f"Bracket order placed: BUY {qty} {symbol}")
            logger.info(f"  Stop Loss: ${stop_loss:.2f}, Take Profit: ${take_profit:.2f}")
            return order
        except Exception as e:
            logger.error(f"Error placing bracket order: {e}")
            return None

    def prefilter_stocks(self, universe, top_n=15):
        """
        Fast technical pre-filter: score every stock in universe and return top_n candidates.
        No AI calls — pure indicator math. Runs in ~10-20 seconds for 100 stocks.

        Scoring criteria (each adds points):
          +3  RSI < 35  (oversold — strong buy setup)
          +2  RSI 35-45 (mildly oversold)
          +2  Volume ratio > 1.5x average (unusual activity)
          +1  Volume ratio > 1.2x average
          +2  Price above fast SMA (uptrend)
          +1  MACD histogram positive (bullish momentum)
          +1  ADX > 25 (trending, not ranging)
          -2  RSI > 75 (overbought — avoid chasing)
        """
        from datetime import datetime, timedelta
        scores = {}
        end = datetime.utcnow()
        start = end - timedelta(days=40)

        # Fetch all bars in one batch request (much faster than one-by-one)
        try:
            all_bars = self.api.get_bars(
                universe,
                '1Day',
                start=start.strftime('%Y-%m-%dT%H:%M:%SZ'),
                end=end.strftime('%Y-%m-%dT%H:%M:%SZ'),
                adjustment='raw',
            ).df
        except Exception as e:
            logger.error(f"Pre-filter batch fetch failed: {e}")
            return universe[:top_n]

        if all_bars.empty:
            return universe[:top_n]

        # Alpaca returns multi-index (symbol, timestamp) when multiple symbols
        if isinstance(all_bars.index, pd.MultiIndex):
            symbols_in_data = all_bars.index.get_level_values('symbol').unique()
        else:
            symbols_in_data = universe[:1]

        for sym in symbols_in_data:
            try:
                if isinstance(all_bars.index, pd.MultiIndex):
                    df = all_bars.xs(sym, level='symbol').copy()
                else:
                    df = all_bars.copy()

                if len(df) < 20:
                    continue

                closes = df['close'].values
                volumes = df['volume'].values
                score = 0

                # RSI (14)
                delta = np.diff(closes)
                gains = np.where(delta > 0, delta, 0)
                losses = np.where(delta < 0, -delta, 0)
                avg_gain = np.mean(gains[-14:]) if len(gains) >= 14 else np.mean(gains)
                avg_loss = np.mean(losses[-14:]) if len(losses) >= 14 else np.mean(losses)
                rsi = 100 - (100 / (1 + avg_gain / avg_loss)) if avg_loss > 0 else 100

                if rsi < 35:
                    score += 3
                elif rsi < 45:
                    score += 2
                elif rsi > 75:
                    score -= 2

                # Volume ratio (current vs 20-day avg)
                avg_vol = np.mean(volumes[-20:]) if len(volumes) >= 20 else np.mean(volumes)
                vol_ratio = volumes[-1] / avg_vol if avg_vol > 0 else 1
                if vol_ratio > 1.5:
                    score += 2
                elif vol_ratio > 1.2:
                    score += 1

                # Trend: price vs 20-day SMA
                sma20 = np.mean(closes[-20:]) if len(closes) >= 20 else closes[-1]
                if closes[-1] > sma20:
                    score += 2

                # MACD histogram sign (12/26 EMA diff)
                def ema(arr, n):
                    k = 2 / (n + 1)
                    e = arr[0]
                    for v in arr[1:]:
                        e = v * k + e * (1 - k)
                    return e
                if len(closes) >= 26:
                    macd = ema(closes, 12) - ema(closes, 26)
                    if macd > 0:
                        score += 1

                # ADX proxy: compare recent range to average range
                if len(df) >= 15 and 'high' in df.columns and 'low' in df.columns:
                    ranges = (df['high'] - df['low']).values
                    recent_range = np.mean(ranges[-5:])
                    avg_range = np.mean(ranges[-15:])
                    if avg_range > 0 and recent_range / avg_range > 1.1:
                        score += 1

                scores[sym] = score

            except Exception:
                continue

        if not scores:
            return universe[:top_n]

        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        top = [sym for sym, _ in ranked[:top_n]]
        score_str = ', '.join(f"{s}({sc})" for s, sc in ranked[:top_n])
        logger.info(f"Pre-filter selected {len(top)}/{len(scores)} stocks: {score_str}")
        return top

    def run_trading_loop(self, symbols=None, check_interval=300):
        """
        Main trading loop with Claude AI

        Args:
            symbols: List of symbols to trade (default: config.STOCK_UNIVERSE)
            check_interval: Seconds between checks (default: 300 = 5 minutes)
        """
        if symbols is None:
            symbols = config.NASDAQ_100

        use_prefilter = len(symbols) > 20

        logger.info(f"Starting trading bot — universe: {len(symbols)} stocks")
        if use_prefilter:
            logger.info(f"Pre-filter ON: will select top {config.PREFILTER_TOP_N} candidates each cycle")
        logger.info(f"Check interval: {check_interval} seconds ({check_interval/60:.1f} minutes)")

        while True:
            try:
                # Check if market is open
                if not self.is_market_open():
                    logger.info("Market is closed. Waiting...")
                    time_module.sleep(300)  # Wait 5 minutes
                    continue

                # Get account info
                account = self.get_account_info()
                logger.info(f"\n{'='*60}")
                logger.info(f"Portfolio Value: ${account['portfolio_value']:,.2f}")
                logger.info(f"{'='*60}\n")

                # Get current positions
                current_positions = self.get_current_positions()

                # Pre-filter: scan full universe, pick best setups, then run AI on those
                if use_prefilter:
                    logger.info(f"Scanning {len(symbols)} stocks for best setups...")
                    # Always include stocks we already hold so we can manage them
                    held = list(current_positions.keys())
                    candidates = self.prefilter_stocks(symbols, top_n=config.PREFILTER_TOP_N)
                    # Merge held positions (must manage them) + new candidates
                    active_symbols = list(dict.fromkeys(held + candidates))
                    logger.info(f"Running AI on {len(active_symbols)} stocks "
                                f"({len(held)} held + {len(candidates)} new candidates)")
                else:
                    active_symbols = symbols

                # Check each symbol
                for symbol in active_symbols:
                    try:
                        logger.info(f"\n--- Analyzing {symbol} ---")

                        # Get latest data
                        bars = self.get_latest_bars([symbol], limit=300)
                        if symbol not in bars:
                            continue

                        df = bars[symbol]
                        current_price = df['close'].iloc[-1]

                        logger.info(f"Current price: ${current_price:.2f}")

                        # Check if we have a position
                        if symbol in current_positions:
                            position = current_positions[symbol]

                            logger.info(f"Current position: {position['shares']} shares @ ${position['entry_price']:.2f}")
                            logger.info(f"P&L: ${position['unrealized_pl']:.2f} ({position['unrealized_plpc']*100:.1f}%)")

                            # Ask Claude if we should sell or hold
                            logger.info("Asking Claude for sell analysis...")
                            decision = self.analyze_with_claude(symbol, df, current_position=position)

                            logger.info(f"\n🤖 Claude's Decision:")
                            logger.info(f"   Action: {decision['action'].upper()}")
                            logger.info(f"   Confidence: {decision['confidence']:.0%}")
                            logger.info(f"   Risk Level: {decision['risk_level']}")
                            logger.info(f"   Reasoning: {decision['reasoning']}")

                            # Sell if Claude recommends with sufficient confidence
                            if (decision['action'] == 'sell' and
                                decision['confidence'] >= config.CLAUDE_MIN_CONFIDENCE):

                                # Sell position
                                self.place_order(symbol, position['shares'], side='sell')
                                self.recently_sold[symbol] = datetime.now()  # start cooldown
                                logger.info(f"✅ SELL {position['shares']} shares of {symbol} @ ${current_price:.2f}")
                                logger.info(f"   Claude's confidence: {decision['confidence']:.0%}")
                                send_trade_alert(symbol, 'sell', current_price,
                                                 decision['confidence'], decision['reasoning'],
                                                 qty=position['shares'])
                            else:
                                logger.info(f"⏸️  HOLD {symbol} position")

                            # Also check risk manager as a safety override
                            should_exit, reason = self.risk_manager.should_exit_position(
                                position, current_price
                            )
                            if should_exit and decision['action'] != 'sell':
                                logger.warning(f"⚠️  Risk Manager Override: {reason}")
                                self.recently_sold[symbol] = datetime.now()  # start cooldown
                                self.place_order(symbol, position['shares'], side='sell')
                                logger.info(f"✅ SELL {symbol} (Risk Management Override)")
                                send_trade_alert(symbol, 'sell', current_price, 1.0,
                                                 f'Risk manager override: {reason}',
                                                 qty=position['shares'])


                        else:
                            # Check cooldown — skip if sold within last 24 hours
                            cooldown_hours = 24
                            if symbol in self.recently_sold:
                                hours_since_sell = (datetime.now() - self.recently_sold[symbol]).total_seconds() / 3600
                                if hours_since_sell < cooldown_hours:
                                    logger.info(f"⏳ {symbol} in cooldown ({hours_since_sell:.1f}h / {cooldown_hours}h since last sell) — skipping")
                                    continue
                                else:
                                    del self.recently_sold[symbol]  # cooldown expired

                            # Ask Claude if we should buy
                            logger.info("Asking Claude for analysis...")
                            decision = self.analyze_with_claude(symbol, df)

                            logger.info(f"\n🤖 Claude's Decision:")
                            logger.info(f"   Action: {decision['action'].upper()}")
                            logger.info(f"   Confidence: {decision['confidence']:.0%}")
                            logger.info(f"   Risk Level: {decision['risk_level']}")
                            logger.info(f"   Reasoning: {decision['reasoning']}")

                            # Trade if Claude recommends BUY with high confidence
                            if (decision['action'] == 'buy' and
                                decision['confidence'] >= config.CLAUDE_MIN_CONFIDENCE):

                                # Calculate position size
                                shares = self.risk_manager.calculate_position_size(
                                    current_price, decision['confidence']
                                )

                                if shares > 0:
                                    # Try bracket order first, fall back to plain market order
                                    order = self.place_bracket_order(symbol, shares, current_price)
                                    if order is None:
                                        # Bracket failed — place simple market order
                                        logger.warning(f"Bracket order failed for {symbol}, placing plain market order")
                                        try:
                                            order = self.api.submit_order(
                                                symbol=symbol,
                                                qty=shares,
                                                side='buy',
                                                type='market',
                                                time_in_force='day',
                                            )
                                        except Exception as e:
                                            logger.error(f"Plain market order also failed for {symbol}: {e}")
                                            order = None
                                    if order is not None:
                                        logger.info(f"✅ BUY {shares} shares of {symbol} @ ${current_price:.2f}")
                                        logger.info(f"   Claude's confidence: {decision['confidence']:.0%}")
                                        send_trade_alert(symbol, 'buy', current_price,
                                                         decision['confidence'], decision['reasoning'],
                                                         qty=shares)
                                    else:
                                        logger.error(f"❌ BUY FAILED for {symbol} — order not placed")
                            else:
                                logger.info(f"⏸️  HOLD {symbol} - Not trading")

                        logger.info("")  # Empty line for readability

                    except Exception as e:
                        logger.error(f"Error processing {symbol}: {e}")
                        continue

                # Wall-clock sleep so macOS lid-close doesn't freeze the timer
                wake_at = time_module.time() + check_interval
                next_str = datetime.fromtimestamp(wake_at).strftime('%H:%M:%S')
                logger.info(f"\nNext run at {next_str} — sleeping...")
                while time_module.time() < wake_at:
                    time_module.sleep(60)

            except KeyboardInterrupt:
                logger.info("\nTrading bot stopped by user")
                break
            except Exception as e:
                logger.error(f"Error in trading loop: {e}")
                time_module.sleep(60)

    def close_all_positions(self):
        """Close all open positions"""
        try:
            self.api.close_all_positions()
            logger.info("All positions closed")
        except Exception as e:
            logger.error(f"Error closing positions: {e}")

    def cancel_all_orders(self):
        """Cancel all pending orders"""
        try:
            self.api.cancel_all_orders()
            logger.info("All orders cancelled")
        except Exception as e:
            logger.error(f"Error cancelling orders: {e}")


from datetime import timedelta  # Add this import at top if not there
