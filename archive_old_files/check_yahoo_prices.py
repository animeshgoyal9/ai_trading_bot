#!/usr/bin/env python3
"""
Check Current Stock Prices from Yahoo Finance
Shows real-time market prices (what you see on most websites)
"""
import sys
sys.path.insert(0, '/Users/animeshgoyal/Downloads/ai_trading_bot/trading/lib/python3.11/site-packages')

import yfinance as yf
from datetime import datetime
import config

def main():
    print("="*60)
    print("📊 CURRENT STOCK PRICES (YAHOO FINANCE)")
    print("="*60)
    print(f"\nTime: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("")

    print("Stock Prices:")
    print("-" * 60)

    for symbol in config.STOCK_UNIVERSE:
        try:
            ticker = yf.Ticker(symbol)

            # Get current price (fast_info)
            try:
                current_price = ticker.info.get('currentPrice') or ticker.info.get('regularMarketPrice')
                previous_close = ticker.info.get('previousClose')

                if current_price:
                    change = current_price - previous_close if previous_close else 0
                    change_pct = (change / previous_close * 100) if previous_close else 0

                    arrow = "📈" if change > 0 else "📉" if change < 0 else "➡️"

                    print(f"\n{symbol}:")
                    print(f"  Current: ${current_price:.2f} {arrow}")
                    print(f"  Change: ${change:+.2f} ({change_pct:+.2f}%)")
                    print(f"  Previous Close: ${previous_close:.2f}")
                else:
                    # Try fast method
                    info = ticker.fast_info
                    print(f"\n{symbol}:")
                    print(f"  Last Price: ${info.last_price:.2f}")
                    print(f"  Previous Close: ${info.previous_close:.2f}")

            except Exception as e:
                print(f"\n{symbol}: ⚠️  Could not get detailed info - {e}")

        except Exception as e:
            print(f"\n{symbol}: ❌ Error - {e}")

    print("\n" + "="*60)
    print("ℹ️  Source: Yahoo Finance (real-time market data)")
    print("   This is what you see on most stock websites")
    print("   Alpaca may show slightly different prices due to:")
    print("   - Different data sources")
    print("   - Bid/ask spreads")
    print("   - Market vs limit orders")
    print("="*60)

if __name__ == "__main__":
    main()
