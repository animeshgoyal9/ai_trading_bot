"""
Paper Trading Bot
Executes live paper trades using Alpaca API
"""
import alpaca_trade_api as tradeapi
from datetime import datetime, time
import pytz
from loguru import logger
import time as time_module
import config
from risk_management import RiskManager


class PaperTradingBot:
    """Live paper trading bot using Alpaca API"""

    def __init__(self, model, feature_engine):
        """
        Initialize paper trading bot

        Args:
            model: Trained ML model
            feature_engine: FeatureEngine instance
        """
        self.model = model
        self.feature_engine = feature_engine
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

    def is_market_open(self):
        """Check if market is currently open"""
        try:
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

    def get_latest_bars(self, symbols, timeframe='1Day', limit=100):
        """
        Get latest price bars for symbols

        Args:
            symbols: List of stock symbols
            timeframe: Bar timeframe
            limit: Number of bars to fetch

        Returns:
            Dict of DataFrames {symbol: df}
        """
        try:
            barset = self.api.get_bars(symbols, timeframe, limit=limit)
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

    def place_order(self, symbol, qty, side='buy', order_type='market'):
        """
        Place an order

        Args:
            symbol: Stock symbol
            qty: Number of shares
            side: 'buy' or 'sell'
            order_type: 'market' or 'limit'

        Returns:
            Order object if successful, None otherwise
        """
        try:
            order = self.api.submit_order(
                symbol=symbol,
                qty=qty,
                side=side,
                type=order_type,
                time_in_force='day'
            )

            logger.info(f"Order placed: {side.upper()} {qty} {symbol} @ {order_type}")
            return order
        except Exception as e:
            logger.error(f"Error placing order: {e}")
            return None

    def place_bracket_order(self, symbol, qty, entry_price):
        """
        Place bracket order with stop loss and take profit

        Args:
            symbol: Stock symbol
            qty: Number of shares
            entry_price: Entry price for calculation
        """
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

    def make_predictions(self, symbol, df):
        """
        Make trading predictions for a symbol

        Args:
            symbol: Stock symbol
            df: DataFrame with OHLCV data

        Returns:
            Tuple (prediction, confidence)
        """
        try:
            # Add technical indicators
            df_features = self.feature_engine.add_technical_indicators(df)

            # Add sentiment features if enabled
            if self.feature_engine.use_sentiment:
                df_features = self.feature_engine.add_sentiment_features(df_features, symbol)

            # Get feature columns
            feature_cols = self.feature_engine.select_features(df_features)

            # Get latest features
            X = df_features[feature_cols].iloc[[-1]]

            # Make prediction
            prediction = self.model.predict(X)[0]
            confidence = self.model.predict_proba(X)[0][1]

            logger.debug(f"{symbol}: Prediction={prediction}, Confidence={confidence:.2f}")

            return prediction, confidence
        except Exception as e:
            logger.error(f"Error making prediction for {symbol}: {e}")
            return 0, 0.0

    def run_trading_loop(self, symbols=None, check_interval=60):
        """
        Main trading loop

        Args:
            symbols: List of symbols to trade (default: config.STOCK_UNIVERSE)
            check_interval: Seconds between checks
        """
        if symbols is None:
            symbols = config.STOCK_UNIVERSE

        logger.info(f"Starting paper trading bot for {len(symbols)} stocks")
        logger.info(f"Check interval: {check_interval} seconds")

        while True:
            try:
                # Check if market is open
                if not self.is_market_open():
                    logger.info("Market is closed. Waiting...")
                    time_module.sleep(300)  # Wait 5 minutes
                    continue

                # Get account info
                account = self.get_account_info()
                logger.info(f"Portfolio Value: ${account['portfolio_value']:,.2f}")

                # Get current positions
                current_positions = self.get_current_positions()

                # Check each symbol
                for symbol in symbols:
                    try:
                        # Get latest data
                        bars = self.get_latest_bars([symbol], limit=100)
                        if symbol not in bars:
                            continue

                        df = bars[symbol]
                        current_price = df['close'].iloc[-1]

                        # Make prediction
                        prediction, confidence = self.make_predictions(symbol, df)

                        # Check if we have a position
                        if symbol in current_positions:
                            position = current_positions[symbol]

                            # Check if we should exit
                            should_exit, reason = self.risk_manager.should_exit_position(
                                position, current_price
                            )

                            if should_exit or (prediction == 0 and confidence > config.MIN_CONFIDENCE):
                                # Sell position
                                self.place_order(symbol, position['shares'], side='sell')
                                logger.info(f"SELL signal for {symbol}: {reason or 'model_signal'}")

                        else:
                            # Check if we should buy
                            if prediction == 1 and confidence >= config.MIN_CONFIDENCE:
                                # Calculate position size
                                shares = self.risk_manager.calculate_position_size(
                                    current_price, confidence
                                )

                                if shares > 0:
                                    # Place bracket order
                                    self.place_bracket_order(symbol, shares, current_price)
                                    logger.info(f"BUY signal for {symbol}: {shares} shares @ ${current_price:.2f}")

                    except Exception as e:
                        logger.error(f"Error processing {symbol}: {e}")
                        continue

                # Wait before next check
                logger.info(f"Waiting {check_interval} seconds...")
                time_module.sleep(check_interval)

            except KeyboardInterrupt:
                logger.info("Trading bot stopped by user")
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
