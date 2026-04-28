"""
Run Paper Trading Bot
Starts the live paper trading bot
"""
import sys
from loguru import logger
from data_collector import DataCollector
from feature_engineering import FeatureEngine
from ml_model import TradingModel
from paper_trading_bot import PaperTradingBot
import config
from utils import setup_logging
import glob


def load_latest_model(model_dir='models'):
    """Load the most recently trained model"""
    model_files = glob.glob(f"{model_dir}/*.joblib")

    if not model_files:
        logger.error("No trained models found. Please run train_model.py first.")
        return None

    latest_model = sorted(model_files)[-1]
    logger.info(f"Loading model: {latest_model}")

    model = TradingModel(model_type=config.MODEL_TYPE)
    model.load_model(latest_model)

    return model


def main():
    """Main function to run paper trading bot"""
    setup_logging()

    logger.info("="*50)
    logger.info("AI TRADING BOT - PAPER TRADING")
    logger.info("="*50)

    # Check API credentials
    if not config.ALPACA_API_KEY or not config.ALPACA_SECRET_KEY:
        logger.error("Alpaca API credentials not configured!")
        logger.error("Please set ALPACA_API_KEY and ALPACA_SECRET_KEY in .env file")
        logger.info("\nGet free paper trading account at: https://alpaca.markets/")
        return

    # Load trained model
    logger.info("Loading trained model...")
    model = load_latest_model()

    if model is None:
        logger.error("Failed to load model. Run train_model.py first.")
        return

    # Initialize feature engine
    feature_engine = FeatureEngine()

    # Initialize trading bot
    logger.info("Initializing paper trading bot...")
    bot = PaperTradingBot(model, feature_engine)

    # Get account info
    account = bot.get_account_info()
    logger.info(f"\nAccount Info:")
    logger.info(f"  Portfolio Value: ${account['portfolio_value']:,.2f}")
    logger.info(f"  Cash: ${account['cash']:,.2f}")
    logger.info(f"  Buying Power: ${account['buying_power']:,.2f}")

    # Get current positions
    positions = bot.get_current_positions()
    if positions:
        logger.info(f"\nCurrent Positions:")
        for symbol, pos in positions.items():
            logger.info(f"  {symbol}: {pos['shares']} shares @ ${pos['entry_price']:.2f} | P&L: ${pos['unrealized_pl']:.2f}")
    else:
        logger.info("\nNo current positions")

    # Start trading
    logger.info(f"\nStarting paper trading for {len(config.STOCK_UNIVERSE)} stocks...")
    logger.info("Press Ctrl+C to stop\n")

    try:
        bot.run_trading_loop(
            symbols=config.STOCK_UNIVERSE,
            check_interval=60  # Check every minute
        )
    except KeyboardInterrupt:
        logger.info("\nShutting down trading bot...")
        bot.cancel_all_orders()
        logger.info("Trading bot stopped")


if __name__ == "__main__":
    main()
