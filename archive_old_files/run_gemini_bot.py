"""
Run Gemini AI Trading Bot
Starts paper trading with Google Gemini AI making decisions
"""
from loguru import logger
from gemini_trading_bot import GeminiTradingBot
import config
from utils import setup_logging


def main():
    """Main function to run Gemini AI trading bot"""
    setup_logging()

    logger.info("="*60)
    logger.info("🤖 GEMINI AI TRADING BOT")
    logger.info("="*60)

    # Check API credentials
    if not config.GEMINI_API_KEY or config.GEMINI_API_KEY == 'your_gemini_key_here':
        logger.error("❌ GEMINI_API_KEY not configured!")
        logger.error("")
        logger.error("Get your FREE Gemini API key in 30 seconds:")
        logger.error("1. Go to: https://aistudio.google.com/apikey")
        logger.error("2. Click 'Create API Key'")
        logger.error("3. Copy the key")
        logger.error("4. Add to .env file: GEMINI_API_KEY=your_key")
        logger.error("")
        logger.error("Gemini has a generous FREE tier - perfect for trading!")
        return

    if not config.ALPACA_API_KEY or not config.ALPACA_SECRET_KEY:
        logger.error("❌ Alpaca API credentials not configured!")
        logger.error("Get free paper trading account at: https://alpaca.markets/")
        return

    logger.info(f"\n✅ Gemini Model: {config.GEMINI_MODEL}")
    logger.info(f"✅ Min Confidence: {config.GEMINI_MIN_CONFIDENCE:.0%}")
    logger.info(f"✅ Trading Capital: ${config.TRADING_CAPITAL:,.0f}")
    logger.info(f"✅ Trading Mode: {config.TRADING_MODE.upper()}")
    logger.info(f"✅ Assets to Trade: {len(config.TRADING_UNIVERSE)}")

    # Initialize Gemini trading bot
    logger.info("\n🚀 Initializing Gemini AI Trading Bot...")
    bot = GeminiTradingBot()

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

    asset_type = "cryptocurrencies" if config.TRADING_MODE == 'crypto' else "stocks"
    logger.info(f"\n🎯 Starting Gemini AI Trading...")
    logger.info(f"   Trading: {', '.join(config.TRADING_UNIVERSE)}")
    logger.info(f"   Gemini will analyze each {asset_type.rstrip('s')} with AI reasoning")
    logger.info(f"   Check interval: 5 minutes")
    logger.info(f"   Press Ctrl+C to stop\n")

    try:
        bot.run_trading_loop(
            symbols=config.TRADING_UNIVERSE,
            check_interval=300  # 5 minutes
        )
    except KeyboardInterrupt:
        logger.info("\n\n⏹️  Shutting down Gemini AI Trading Bot...")
        bot.cancel_all_orders()
        logger.info("✅ Trading bot stopped")


if __name__ == "__main__":
    main()
