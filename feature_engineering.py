"""
Feature Engineering Module
Generates technical indicators and features for ML model
"""
import pandas as pd
import numpy as np
from ta.trend import SMAIndicator, EMAIndicator, MACD, ADXIndicator
from ta.momentum import RSIIndicator, StochasticOscillator
from ta.volatility import BollingerBands, AverageTrueRange
from ta.volume import OnBalanceVolumeIndicator, VolumeWeightedAveragePrice
from loguru import logger
import config


class FeatureEngine:
    """Creates technical indicators and features for trading"""

    def __init__(self, use_sentiment=None):
        self.indicators_config = config.INDICATORS
        self.use_sentiment = use_sentiment if use_sentiment is not None else config.USE_SENTIMENT

        if self.use_sentiment:
            from sentiment_analysis import SentimentAnalyzer
            self.sentiment_analyzer = SentimentAnalyzer()
            logger.info("Sentiment analysis enabled")
        else:
            self.sentiment_analyzer = None
            logger.info("Sentiment analysis disabled")

    def add_technical_indicators(self, df):
        """
        Add all technical indicators to DataFrame

        Args:
            df: DataFrame with OHLCV data

        Returns:
            DataFrame with added indicator columns
        """
        df = df.copy()

        try:
            # Check if we have enough data
            min_rows_needed = 30  # Minimum for most indicators (lowered for crypto)
            if len(df) < min_rows_needed:
                logger.warning(f"Not enough data ({len(df)} rows) for indicators. Need at least {min_rows_needed}.")
                # Return basic features only
                df['returns'] = df['close'].pct_change()
                df = df.dropna()
                return df

            # Price-based features
            df = self._add_price_features(df)

            # Trend indicators
            df = self._add_trend_indicators(df)

            # Momentum indicators
            df = self._add_momentum_indicators(df)

            # Volatility indicators
            df = self._add_volatility_indicators(df)

            # Volume indicators
            df = self._add_volume_indicators(df)

            # Time-based features
            df = self._add_time_features(df)

            logger.info(f"Added technical indicators. Total features: {len(df.columns)}")

            # Drop NaN values
            df = df.dropna()

            # Check if we still have data after dropping NaN
            if len(df) == 0:
                logger.warning("All rows were NaN after adding indicators")
                df_copy = df.copy()
                df_copy['returns'] = df_copy['close'].pct_change()
                df_copy = df_copy.dropna()
                return df_copy

            return df

        except Exception as e:
            logger.error(f"Error adding technical indicators: {e}")
            # Return data with basic feature as fallback
            df_copy = df.copy()
            df_copy['returns'] = df_copy['close'].pct_change()
            df_copy = df_copy.dropna()
            return df_copy

    def _add_price_features(self, df):
        """Add price-based features"""
        # Returns
        df['returns'] = df['close'].pct_change()
        df['log_returns'] = np.log(df['close'] / df['close'].shift(1))

        # Price momentum
        df['momentum_1'] = df['close'] - df['close'].shift(1)
        df['momentum_5'] = df['close'] - df['close'].shift(5)
        df['momentum_10'] = df['close'] - df['close'].shift(10)

        # High-Low spread
        df['hl_spread'] = (df['high'] - df['low']) / df['close']

        # Open-Close spread
        df['oc_spread'] = (df['close'] - df['open']) / df['open']

        return df

    def _add_trend_indicators(self, df):
        """Add trend indicators"""
        # Simple Moving Averages
        sma_fast = SMAIndicator(df['close'], window=self.indicators_config['sma_fast'])
        sma_slow = SMAIndicator(df['close'], window=self.indicators_config['sma_slow'])
        df['sma_fast'] = sma_fast.sma_indicator()
        df['sma_slow'] = sma_slow.sma_indicator()
        df['sma_diff'] = df['sma_fast'] - df['sma_slow']

        # Long-term Moving Averages (50, 60, 200-day)
        df['sma_50']  = SMAIndicator(df['close'], window=50).sma_indicator()
        df['sma_60']  = SMAIndicator(df['close'], window=60).sma_indicator()
        df['sma_200'] = SMAIndicator(df['close'], window=200).sma_indicator()
        # Above/below MA flags
        df['above_200ma'] = (df['close'] > df['sma_200']).astype(float)
        df['above_50ma']  = (df['close'] > df['sma_50']).astype(float)
        # Golden cross regime: 50-day above 200-day
        df['golden_cross'] = (df['sma_50'] > df['sma_200']).astype(float)

        # Exponential Moving Averages
        ema_fast = EMAIndicator(df['close'], window=self.indicators_config['ema_fast'])
        ema_slow = EMAIndicator(df['close'], window=self.indicators_config['ema_slow'])
        df['ema_fast'] = ema_fast.ema_indicator()
        df['ema_slow'] = ema_slow.ema_indicator()
        df['ema_diff'] = df['ema_fast'] - df['ema_slow']

        # MACD
        macd = MACD(
            df['close'],
            window_fast=self.indicators_config['macd_fast'],
            window_slow=self.indicators_config['macd_slow'],
            window_sign=self.indicators_config['macd_signal']
        )
        df['macd'] = macd.macd()
        df['macd_signal'] = macd.macd_signal()
        df['macd_diff'] = macd.macd_diff()

        # ADX (Trend Strength)
        adx = ADXIndicator(df['high'], df['low'], df['close'], window=self.indicators_config['adx_period'])
        df['adx'] = adx.adx()

        return df

    def _add_momentum_indicators(self, df):
        """Add momentum indicators"""
        # RSI
        rsi = RSIIndicator(df['close'], window=self.indicators_config['rsi_period'])
        df['rsi'] = rsi.rsi()

        # Stochastic Oscillator
        stoch = StochasticOscillator(df['high'], df['low'], df['close'])
        df['stoch'] = stoch.stoch()
        df['stoch_signal'] = stoch.stoch_signal()

        # Rate of Change
        df['roc'] = ((df['close'] - df['close'].shift(10)) / df['close'].shift(10)) * 100

        return df

    def _add_volatility_indicators(self, df):
        """Add volatility indicators"""
        # Bollinger Bands
        bb = BollingerBands(
            df['close'],
            window=self.indicators_config['bb_period'],
            window_dev=self.indicators_config['bb_std']
        )
        df['bb_upper'] = bb.bollinger_hband()
        df['bb_middle'] = bb.bollinger_mavg()
        df['bb_lower'] = bb.bollinger_lband()
        df['bb_width'] = (df['bb_upper'] - df['bb_lower']) / df['bb_middle']
        df['bb_position'] = (df['close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'])

        # Average True Range
        atr = AverageTrueRange(df['high'], df['low'], df['close'], window=self.indicators_config['atr_period'])
        df['atr'] = atr.average_true_range()

        # Historical Volatility
        df['volatility'] = df['returns'].rolling(window=20).std() * np.sqrt(252)

        return df

    def _add_volume_indicators(self, df):
        """Add volume indicators"""
        # On-Balance Volume
        obv = OnBalanceVolumeIndicator(df['close'], df['volume'])
        df['obv'] = obv.on_balance_volume()

        # Volume Rate of Change
        df['volume_roc'] = df['volume'].pct_change(periods=5)

        # Volume Moving Average
        df['volume_sma'] = df['volume'].rolling(window=20).mean()
        df['volume_ratio'] = df['volume'] / df['volume_sma']

        return df

    def _add_time_features(self, df):
        """Add time-based features"""
        df['day_of_week'] = df.index.dayofweek
        df['month'] = df.index.month
        df['quarter'] = df.index.quarter

        return df

    def add_sentiment_features(self, df, symbol):
        """
        Add sentiment analysis features

        Args:
            df: DataFrame with technical features
            symbol: Stock ticker symbol

        Returns:
            DataFrame with sentiment features added
        """
        if not self.use_sentiment or self.sentiment_analyzer is None:
            logger.debug("Sentiment analysis disabled, skipping")
            return df

        try:
            logger.info(f"Adding sentiment features for {symbol}")

            # Get comprehensive sentiment data
            sentiment_data = self.sentiment_analyzer.get_comprehensive_sentiment(symbol)

            # Add sentiment features as columns (broadcast to all rows)
            for key, value in sentiment_data.items():
                df[f'sentiment_{key}'] = value

            logger.info(f"Added {len(sentiment_data)} sentiment features")

        except Exception as e:
            logger.error(f"Error adding sentiment features: {e}")
            # Add default neutral sentiment if error occurs
            df['sentiment_composite_sentiment'] = 0
            df['sentiment_overall_sentiment'] = 0
            df['sentiment_news_volume'] = 0

        return df

    def create_target(self, df, horizon=1, threshold=0.01):
        """
        Create target variable for prediction

        Args:
            df: DataFrame with features
            horizon: Days ahead to predict
            threshold: Minimum return threshold for buy signal

        Returns:
            DataFrame with target column
        """
        df = df.copy()

        # Future returns
        df['future_return'] = df['close'].shift(-horizon) / df['close'] - 1

        # Binary classification: 1 = buy, 0 = hold/sell
        df['target'] = (df['future_return'] > threshold).astype(int)

        # Multi-class classification: 2 = strong buy, 1 = buy, 0 = hold, -1 = sell
        df['target_multi'] = pd.cut(
            df['future_return'],
            bins=[-np.inf, -threshold, 0, threshold, np.inf],
            labels=[-1, 0, 1, 2]
        ).astype(float)

        return df

    def select_features(self, df):
        """
        Select relevant features for modeling

        Returns:
            List of feature column names
        """
        # Exclude non-feature columns
        exclude_cols = ['open', 'high', 'low', 'close', 'volume',
                       'future_return', 'target', 'target_multi']

        feature_cols = [col for col in df.columns if col not in exclude_cols]

        return feature_cols
