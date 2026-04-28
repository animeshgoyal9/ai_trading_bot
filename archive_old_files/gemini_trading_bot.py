"""
Gemini-Powered Trading Bot
Uses Google's Gemini AI to make intelligent trading decisions
"""
import alpaca_trade_api as tradeapi
from datetime import datetime, timedelta
import pytz
from loguru import logger
import time as time_module
import config
from risk_management import RiskManager
from gemini_agent import GeminiTrader
from data_collector import DataCollector
from feature_engineering import FeatureEngine
from crypto_news_fetcher import CryptoNewsFetcher


class GeminiTradingBot:
    """Trading bot powered by Google Gemini AI"""

    def __init__(self):
        """Initialize Gemini-powered trading bot"""

        # Initialize Gemini agent
        logger.info("Initializing Gemini AI Trading Agent...")
        self.gemini_trader = GeminiTrader()

        # Initialize data collector and feature engine
        self.data_collector = DataCollector()
        self.feature_engine = FeatureEngine(use_sentiment=False)  # Gemini handles reasoning
        self.risk_manager = RiskManager(config.TRADING_CAPITAL)

        # Initialize news fetcher for Gemini
        self.news_fetcher = CryptoNewsFetcher()
        logger.info("News integration enabled for Gemini AI")

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

    def is_market_open(self):
        """Check if market is currently open"""
        try:
            # Crypto markets are ALWAYS open (24/7/365)
            if config.TRADING_MODE == 'crypto':
                return True

            # Stock market hours check
            clock = self.api.get_clock()

            # If extended hours enabled, check if within extended hours (4 AM - 8 PM ET)
            if config.ENABLE_EXTENDED_HOURS:
                # Extended hours: 4:00 AM - 8:00 PM ET
                # Regular: 9:30 AM - 4:00 PM ET
                # Just check if market is open OR in extended hours
                if clock.is_open:
                    return True

                # Check if we're in pre-market (4 AM - 9:30 AM) or after-hours (4 PM - 8 PM)
                import pytz
                from datetime import time

                et_tz = pytz.timezone('America/New_York')
                now_et = datetime.now(et_tz)
                current_time = now_et.time()

                # Pre-market: 4:00 AM - 9:30 AM ET
                # After-hours: 4:00 PM - 8:00 PM ET
                pre_market_start = time(4, 0)
                pre_market_end = time(9, 30)
                after_hours_start = time(16, 0)
                after_hours_end = time(20, 0)

                in_extended = (
                    (current_time >= pre_market_start and current_time < pre_market_end) or
                    (current_time >= after_hours_start and current_time <= after_hours_end)
                )

                if in_extended:
                    # Also check if it's a trading day
                    return clock.next_open.date() == now_et.date() or clock.next_close.date() == now_et.date()

                return False
            else:
                # Only trade during regular hours
                return clock.is_open

        except Exception as e:
            logger.error(f"Error checking market status: {e}")
            # Default to True for crypto, False for stocks
            return config.TRADING_MODE == 'crypto'

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

    def get_latest_bars(self, symbols, timeframe='1Day', limit=100):
        """Get latest price bars for symbols"""
        try:
            from alpaca_trade_api.rest import TimeFrame
            from datetime import datetime, timedelta

            # Calculate date range
            end = datetime.now()
            start = end - timedelta(days=limit * 2)  # Request more days to ensure we get enough data

            # Format dates as RFC3339 (with timezone)
            start_str = start.strftime('%Y-%m-%dT%H:%M:%SZ')
            end_str = end.strftime('%Y-%m-%dT%H:%M:%SZ')

            # For crypto, use different API
            if config.TRADING_MODE == 'crypto':
                # Convert timeframe string to TimeFrame object
                if timeframe == '1Day' or timeframe == '1D':
                    tf = TimeFrame.Day
                elif timeframe == '1Hour' or timeframe == '1H':
                    tf = TimeFrame.Hour
                elif timeframe == '15Min':
                    tf = TimeFrame.Minute * 15
                else:
                    tf = TimeFrame.Day  # Default

                logger.info(f"Requesting crypto data from {start.date()} to {end.date()}")

                barset = self.api.get_crypto_bars(
                    symbols,
                    tf,
                    start=start_str,
                    end=end_str
                )
            else:
                # For stocks, use regular get_bars with date range
                logger.info(f"Requesting stock data from {start.date()} to {end.date()}")

                barset = self.api.get_bars(
                    symbols,
                    timeframe,
                    start=start_str,
                    end=end_str,
                    limit=limit
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

    def analyze_with_gemini(self, symbol, df, current_position=None):
        """
        Get Gemini's analysis and trading decision

        Args:
            symbol: Stock symbol
            df: DataFrame with OHLCV data
            current_position: Dict with position info (if we own the stock)

        Returns:
            Gemini's decision dict
        """
        try:
            # Calculate technical indicators
            df_features = self.feature_engine.add_technical_indicators(df)

            # Get latest row as dict
            latest = df_features.iloc[-1].to_dict()
            latest['current_price'] = latest['close']

            # Get market context
            market_context = self._get_market_context()

            # Fetch recent news for this symbol
            logger.info(f"Fetching recent news for {symbol}...")
            news_articles = self.news_fetcher.get_crypto_news(symbol, hours=48, max_articles=5)
            news_context = self.news_fetcher.format_news_for_gemini(news_articles)

            # Ask Gemini to analyze
            logger.info(f"Asking Gemini to analyze {symbol}...")
            decision = self.gemini_trader.analyze_and_decide(
                symbol=symbol,
                technical_data=latest,
                market_context=market_context,
                news_context=news_context,
                current_position=current_position
            )

            return decision

        except Exception as e:
            logger.error(f"Error analyzing with Gemini: {e}")
            return {
                'action': 'hold',
                'confidence': 0.0,
                'reasoning': f'Error: {str(e)}',
                'risk_level': 'high'
            }

    def _get_market_context(self):
        """Get overall market context for Gemini"""
        try:
            import yfinance as yf

            # Get VIX
            vix = yf.Ticker('^VIX')
            vix_data = vix.history(period='1d')
            vix_value = vix_data['Close'].iloc[-1] if not vix_data.empty else 20

            # Get SPY for market trend
            spy = yf.Ticker('SPY')
            spy_data = spy.history(period='5d')
            spy_change = spy_data['Close'].pct_change().iloc[-1] if not spy_data.empty else 0

            market_trend = "Bullish" if spy_change > 0.01 else "Bearish" if spy_change < -0.01 else "Neutral"

            return {
                'vix': vix_value,
                'market_trend': market_trend,
                'spy_change': spy_change * 100
            }

        except Exception as e:
            logger.warning(f"Error getting market context: {e}")
            return {}

    def place_order(self, symbol, qty, side='buy', order_type='market'):
        """Place an order"""
        try:
            # Crypto uses 'gtc' (good till cancelled), stocks use 'day'
            time_in_force = 'gtc' if config.TRADING_MODE == 'crypto' else 'day'

            # Build order parameters
            order_params = {
                'symbol': symbol,
                'qty': qty,
                'side': side,
                'type': order_type,
                'time_in_force': time_in_force
            }

            # For stocks with extended hours enabled, add extended_hours parameter
            if config.TRADING_MODE == 'stocks' and config.ENABLE_EXTENDED_HOURS:
                order_params['extended_hours'] = True

            order = self.api.submit_order(**order_params)

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

            # Crypto uses 'gtc', stocks use 'day'
            time_in_force = 'gtc' if config.TRADING_MODE == 'crypto' else 'day'

            # Build order parameters
            order_params = {
                'symbol': symbol,
                'qty': qty,
                'side': 'buy',
                'type': 'market',
                'time_in_force': time_in_force,
                'order_class': 'bracket',
                'stop_loss': {'stop_price': stop_loss},
                'take_profit': {'limit_price': take_profit}
            }

            # For stocks with extended hours enabled, add extended_hours parameter
            if config.TRADING_MODE == 'stocks' and config.ENABLE_EXTENDED_HOURS:
                order_params['extended_hours'] = True

            # Try bracket order first (might not work for crypto or extended hours)
            try:
                order = self.api.submit_order(**order_params)

                logger.info(f"Bracket order placed: BUY {qty} {symbol}")
                logger.info(f"  Stop Loss: ${stop_loss:.2f}, Take Profit: ${take_profit:.2f}")
                return order

            except Exception:
                # Bracket orders not supported (common for crypto or extended hours)
                # Place market order instead and log stop/target levels
                logger.warning(f"Bracket orders not supported for {symbol}, placing market order")

                # Remove bracket-specific params
                simple_order_params = {
                    'symbol': symbol,
                    'qty': qty,
                    'side': 'buy',
                    'type': 'market',
                    'time_in_force': time_in_force
                }

                if config.TRADING_MODE == 'stocks' and config.ENABLE_EXTENDED_HOURS:
                    simple_order_params['extended_hours'] = True

                order = self.api.submit_order(**simple_order_params)

                logger.info(f"Market order placed: BUY {qty} {symbol}")
                logger.info(f"  Manual Stop Loss: ${stop_loss:.2f}, Manual Take Profit: ${take_profit:.2f}")
                logger.info(f"  (Monitor position manually - bracket orders not available)")
                return order

        except Exception as e:
            logger.error(f"Error placing order: {e}")
            return None

    def run_trading_loop(self, symbols=None, check_interval=300):
        """
        Main trading loop with Gemini AI

        Args:
            symbols: List of symbols to trade (default: config.TRADING_UNIVERSE)
            check_interval: Seconds between checks (default: 300 = 5 minutes)
        """
        if symbols is None:
            symbols = config.TRADING_UNIVERSE

        logger.info(f"Starting Gemini AI trading bot for {len(symbols)} stocks")
        logger.info(f"Check interval: {check_interval} seconds ({check_interval/60:.1f} minutes)")
        logger.info("Gemini will analyze each opportunity and explain its reasoning")

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

                # Check each symbol
                for symbol in symbols:
                    try:
                        logger.info(f"\n--- Analyzing {symbol} ---")

                        # Get latest data
                        # Both crypto and stocks use daily data (Alpaca paper trading has limited crypto history)
                        bars = self.get_latest_bars([symbol], timeframe='1Day', limit=100)

                        if symbol not in bars:
                            logger.warning(f"No data available for {symbol}")
                            continue

                        df = bars[symbol]

                        logger.info(f"Retrieved {len(df)} bars of data")

                        # Skip if not enough data for indicators (lower threshold)
                        if len(df) < 30:
                            logger.warning(f"Not enough data for {symbol} (only {len(df)} bars), need at least 30...")
                            continue

                        current_price = df['close'].iloc[-1]

                        logger.info(f"Current price: ${current_price:.2f}")

                        # Check if we have a position
                        if symbol in current_positions:
                            position = current_positions[symbol]

                            logger.info(f"Current position: {position['shares']} shares @ ${position['entry_price']:.2f}")
                            logger.info(f"P&L: ${position['unrealized_pl']:.2f} ({position['unrealized_plpc']*100:.1f}%)")

                            # Ask Gemini if we should sell or hold
                            logger.info("Asking Gemini whether to SELL or HOLD...")
                            decision = self.analyze_with_gemini(symbol, df, current_position=position)

                            logger.info(f"\n🤖 Gemini's Decision:")
                            logger.info(f"   Action: {decision['action'].upper()}")
                            logger.info(f"   Confidence: {decision['confidence']:.0%}")
                            logger.info(f"   Risk Level: {decision['risk_level']}")
                            logger.info(f"   Reasoning: {decision['reasoning']}")

                            # If Gemini says SELL with high confidence, sell the position
                            if (decision['action'] == 'sell' and
                                decision['confidence'] >= config.GEMINI_MIN_CONFIDENCE):
                                self.place_order(symbol, position['shares'], side='sell')
                                logger.info(f"✅ SELL {position['shares']} shares of {symbol} @ ${current_price:.2f}")
                                logger.info(f"   Gemini's confidence: {decision['confidence']:.0%}")
                            else:
                                logger.info(f"⏸️  HOLD {symbol} - Keeping position")

                            # Also check risk manager's automatic stops
                            should_exit, reason = self.risk_manager.should_exit_position(
                                position, current_price
                            )
                            if should_exit and decision['action'] != 'sell':
                                # Emergency exit (stop-loss/take-profit hit)
                                self.place_order(symbol, position['shares'], side='sell')
                                logger.info(f"🚨 EMERGENCY SELL {symbol}: {reason}")

                        else:
                            # Ask Gemini if we should buy
                            logger.info("Asking Gemini whether to BUY or HOLD...")
                            decision = self.analyze_with_gemini(symbol, df)

                            logger.info(f"\n🤖 Gemini's Decision:")
                            logger.info(f"   Action: {decision['action'].upper()}")
                            logger.info(f"   Confidence: {decision['confidence']:.0%}")
                            logger.info(f"   Risk Level: {decision['risk_level']}")
                            logger.info(f"   Reasoning: {decision['reasoning']}")

                            # Trade if Gemini recommends BUY with high confidence
                            if (decision['action'] == 'buy' and
                                decision['confidence'] >= config.GEMINI_MIN_CONFIDENCE):

                                # Calculate position size
                                shares = self.risk_manager.calculate_position_size(
                                    current_price, decision['confidence']
                                )

                                if shares > 0:
                                    # Place bracket order
                                    self.place_bracket_order(symbol, shares, current_price)
                                    logger.info(f"✅ BUY {shares} shares of {symbol} @ ${current_price:.2f}")
                                    logger.info(f"   Gemini's confidence: {decision['confidence']:.0%}")
                            else:
                                logger.info(f"⏸️  HOLD {symbol} - Not trading")

                        logger.info("")  # Empty line for readability

                    except Exception as e:
                        logger.error(f"Error processing {symbol}: {e}")
                        continue

                # Wait before next check
                logger.info(f"\nWaiting {check_interval} seconds until next check...")
                logger.info(f"Next check at: {(datetime.now() + timedelta(seconds=check_interval)).strftime('%H:%M:%S')}")
                time_module.sleep(check_interval)

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
