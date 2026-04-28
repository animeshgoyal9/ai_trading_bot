"""
Run Claude AI Trading Bot
Starts paper trading with Claude AI making decisions
"""
from loguru import logger
from claude_trading_bot import ClaudeTradingBot
import config
from utils import setup_logging


def main():
    """Main function to run Claude AI trading bot"""
    setup_logging()

    logger.info("="*60)
    logger.info("🤖 CLAUDE AI TRADING BOT")
    logger.info("="*60)

    # Check API credentials
    if not config.ANTHROPIC_API_KEY:
        logger.error("ANTHROPIC_API_KEY not configured!")
        logger.error("Get your free API key at: https://console.anthropic.com")
        logger.error("Add it to your .env file as: ANTHROPIC_API_KEY=your_key")
        return

    if not config.ALPACA_API_KEY or not config.ALPACA_SECRET_KEY:
        logger.error("Alpaca API credentials not configured!")
        logger.error("Get free paper trading account at: https://alpaca.markets/")
        return

    logger.info(f"\nClaude Model: {config.CLAUDE_MODEL}")
    logger.info(f"Min Confidence: {config.CLAUDE_MIN_CONFIDENCE:.0%}")
    logger.info(f"Trading Capital: ${config.TRADING_CAPITAL:,.0f}")
    logger.info(f"Stocks to Trade: {len(config.STOCK_UNIVERSE)}")

    # Initialize Claude trading bot
    logger.info("\nInitializing Claude AI Trading Bot...")
    bot = ClaudeTradingBot()

    # Get account info
    account = bot.get_account_info()
    logger.info(f"\n📊 Account Info:")
    logger.info(f"   Portfolio Value: ${account['portfolio_value']:,.2f}")
    logger.info(f"   Cash: ${account['cash']:,.2f}")
    logger.info(f"   Buying Power: ${account['buying_power']:,.2f}")

    # Get current positions
    positions = bot.get_current_positions()
    if positions:
        logger.info(f"\n💼 Current Positions:")
        for symbol, pos in positions.items():
            logger.info(f"   {symbol}: {pos['shares']} shares @ ${pos['entry_price']:.2f}")
            logger.info(f"      P&L: ${pos['unrealized_pl']:.2f} ({pos['unrealized_plpc']*100:.1f}%)")
    else:
        logger.info("\n💼 No current positions")

    logger.info(f"\n🚀 Starting Claude AI Trading...")
    logger.info(f"   Claude will analyze each stock and make intelligent decisions")
    logger.info(f"   Check interval: 5 minutes (recommended for Claude API limits)")
    logger.info(f"   Press Ctrl+C to stop\n")

    try:
        bot.run_trading_loop(
            symbols=config.STOCK_UNIVERSE,
            check_interval=300  # 5 minutes - respectful of Claude API limits
        )
    except KeyboardInterrupt:
        logger.info("\n\nShutting down Claude AI Trading Bot...")
        bot.cancel_all_orders()
        logger.info("Trading bot stopped")


if __name__ == "__main__":
    main()
