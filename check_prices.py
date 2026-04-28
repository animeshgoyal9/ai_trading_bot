#!/usr/bin/env python3
"""
Check Current Stock Prices
Shows what prices the trading bot sees from Alpaca
"""
import sys
sys.path.insert(0, '/Users/animeshgoyal/Downloads/ai_trading_bot/trading/lib/python3.11/site-packages')

import alpaca_trade_api as tradeapi
from datetime import datetime
import config

def main():
    print("="*60)
    print("📊 CURRENT STOCK PRICES FROM ALPACA")
    print("="*60)
    print(f"\nTime: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("")

    # Initialize Alpaca API
    try:
        api = tradeapi.REST(
            config.ALPACA_API_KEY,
            config.ALPACA_SECRET_KEY,
            config.ALPACA_BASE_URL,
            api_version='v2'
        )
    except Exception as e:
        print(f"❌ Error connecting to Alpaca: {e}")
        print("\nMake sure you're not on corporate network!")
        return

    # Get prices for all stocks
    print("Stock Prices:")
    print("-" * 60)

    for symbol in config.STOCK_UNIVERSE:
        try:
            # Get latest trade
            trade = api.get_latest_trade(symbol)
            price = trade.price
            trade_time = trade.timestamp

            # Get latest quote for bid/ask
            quote = api.get_latest_quote(symbol)
            bid = quote.bid_price
            ask = quote.ask_price
            spread = ask - bid

            print(f"\n{symbol}:")
            print(f"  Last Trade: ${price:.2f} at {trade_time.strftime('%H:%M:%S')}")
            print(f"  Bid/Ask: ${bid:.2f} / ${ask:.2f} (spread: ${spread:.2f})")

        except Exception as e:
            print(f"\n{symbol}: ❌ Error - {e}")

    print("\n" + "="*60)
    print("ℹ️  Note: Prices shown are from Alpaca (paper trading)")
    print("   Real-time prices may differ slightly from other sources")
    print("   Market data delays: Real-time for stocks, 15-min for indices")
    print("="*60)

if __name__ == "__main__":
    main()
