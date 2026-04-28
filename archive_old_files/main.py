"""
Main entry point for the AI Trading Bot
"""
import sys
import argparse
from loguru import logger
from utils import setup_logging
import config


def main():
    """Main CLI for the trading bot"""
    setup_logging()

    parser = argparse.ArgumentParser(
        description='AI Trading Bot - Automated stock trading with machine learning'
    )

    parser.add_argument(
        'command',
        choices=['train', 'backtest', 'trade', 'status'],
        help='Command to execute'
    )

    parser.add_argument(
        '--symbol',
        type=str,
        default='AAPL',
        help='Stock symbol (default: AAPL)'
    )

    parser.add_argument(
        '--symbols',
        type=str,
        nargs='+',
        help='Multiple stock symbols'
    )

    args = parser.parse_args()

    logger.info("="*50)
    logger.info("AI TRADING BOT")
    logger.info("="*50)

    if args.command == 'train':
        from train_model import train_model

        symbols = args.symbols if args.symbols else [args.symbol]

        for symbol in symbols:
            logger.info(f"\nTraining model for {symbol}...")
            train_model(symbol, save_model=True)

    elif args.command == 'backtest':
        from train_model import train_model

        logger.info(f"Running backtest for {args.symbol}...")
        train_model(args.symbol, save_model=False)

    elif args.command == 'trade':
        from run_paper_trading import main as run_trading
        run_trading()

    elif args.command == 'status':
        from paper_trading_bot import PaperTradingBot
        from ml_model import TradingModel
        from feature_engineering import FeatureEngine

        if not config.ALPACA_API_KEY:
            logger.error("Alpaca API credentials not configured")
            return

        model = TradingModel()
        feature_engine = FeatureEngine()
        bot = PaperTradingBot(model, feature_engine)

        account = bot.get_account_info()
        positions = bot.get_current_positions()

        logger.info("\n=== ACCOUNT STATUS ===")
        logger.info(f"Portfolio Value: ${account['portfolio_value']:,.2f}")
        logger.info(f"Cash: ${account['cash']:,.2f}")
        logger.info(f"Buying Power: ${account['buying_power']:,.2f}")

        if positions:
            logger.info("\n=== CURRENT POSITIONS ===")
            for symbol, pos in positions.items():
                logger.info(f"{symbol}:")
                logger.info(f"  Shares: {pos['shares']}")
                logger.info(f"  Entry Price: ${pos['entry_price']:.2f}")
                logger.info(f"  Current Price: ${pos['current_price']:.2f}")
                logger.info(f"  P&L: ${pos['unrealized_pl']:.2f} ({pos['unrealized_plpc']:.2%})")
        else:
            logger.info("\nNo open positions")


if __name__ == "__main__":
    main()
