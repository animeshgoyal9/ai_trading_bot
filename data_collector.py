"""
Data Collection Module
Fetches historical and real-time stock data
"""
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from loguru import logger
import config


class DataCollector:
    """Collects stock market data using yfinance"""

    def __init__(self):
        self.symbols = config.STOCK_UNIVERSE

    def fetch_historical_data(self, symbol, start_date=None, end_date=None, interval='1d'):
        """
        Fetch historical stock data

        Args:
            symbol: Stock ticker symbol
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            interval: Data interval (1d, 1h, 15m, etc.)

        Returns:
            DataFrame with OHLCV data
        """
        try:
            if start_date is None:
                start_date = config.DATA_START_DATE
            if end_date is None:
                end_date = datetime.now().strftime('%Y-%m-%d')

            logger.info(f"Fetching historical data for {symbol} from {start_date} to {end_date}")

            ticker = yf.Ticker(symbol)
            df = ticker.history(start=start_date, end=end_date, interval=interval)

            if df.empty:
                logger.warning(f"No data fetched for {symbol}")
                return None

            # Clean column names
            df.columns = df.columns.str.lower()
            df.index.name = 'date'

            logger.info(f"Fetched {len(df)} records for {symbol}")
            return df

        except Exception as e:
            logger.error(f"Error fetching data for {symbol}: {e}")
            return None

    def fetch_multiple_stocks(self, symbols=None, start_date=None, end_date=None):
        """
        Fetch historical data for multiple stocks

        Returns:
            Dictionary of DataFrames {symbol: df}
        """
        if symbols is None:
            symbols = self.symbols

        data_dict = {}
        for symbol in symbols:
            df = self.fetch_historical_data(symbol, start_date, end_date)
            if df is not None:
                data_dict[symbol] = df

        logger.info(f"Fetched data for {len(data_dict)} stocks")
        return data_dict

    def fetch_latest_price(self, symbol):
        """
        Fetch the latest price for a symbol

        Returns:
            Dict with latest price info
        """
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info

            return {
                'symbol': symbol,
                'price': info.get('currentPrice', info.get('regularMarketPrice')),
                'change': info.get('regularMarketChangePercent', 0),
                'volume': info.get('volume'),
                'timestamp': datetime.now()
            }
        except Exception as e:
            logger.error(f"Error fetching latest price for {symbol}: {e}")
            return None

    def get_stock_info(self, symbol):
        """Get detailed stock information"""
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info

            return {
                'symbol': symbol,
                'name': info.get('longName', ''),
                'sector': info.get('sector', ''),
                'industry': info.get('industry', ''),
                'market_cap': info.get('marketCap', 0),
                'avg_volume': info.get('averageVolume', 0),
                'pe_ratio': info.get('trailingPE', 0),
                'beta': info.get('beta', 1.0),
            }
        except Exception as e:
            logger.error(f"Error fetching info for {symbol}: {e}")
            return None

    def save_data(self, df, symbol, filepath='data'):
        """Save DataFrame to CSV"""
        import os
        os.makedirs(filepath, exist_ok=True)
        filename = f"{filepath}/{symbol}_{datetime.now().strftime('%Y%m%d')}.csv"
        df.to_csv(filename)
        logger.info(f"Saved data to {filename}")

    def load_data(self, symbol, filepath='data'):
        """Load DataFrame from CSV"""
        import glob
        files = glob.glob(f"{filepath}/{symbol}_*.csv")
        if files:
            latest_file = sorted(files)[-1]
            df = pd.read_csv(latest_file, index_col=0, parse_dates=True)
            logger.info(f"Loaded data from {latest_file}")
            return df
        return None
