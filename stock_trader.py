"""
Stock Trader - Continuous background runner
Analyzes and trades STOCK_UNIVERSE every 5 minutes during market hours.
Sleeps automatically when market is closed.
"""
from claude_trading_bot import ClaudeTradingBot
import config

if __name__ == '__main__':
    print(f'Starting stock trader for: {", ".join(config.STOCK_UNIVERSE)}')
    print('Trades every 3 hrs during market hours. Sleeps when market is closed.')
    print('Logs -> logs/stock_trader.log | Ctrl+C to stop\n')

    bot = ClaudeTradingBot()
    bot.run_trading_loop(
        symbols=config.STOCK_UNIVERSE,
        check_interval=10800,  # 3 hours
    )
