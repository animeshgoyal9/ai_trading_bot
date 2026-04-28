"""
Simple Test Trade Script
Uses direct HTTP requests to place trades without complex dependencies
"""
import requests
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Alpaca API credentials
API_KEY = os.getenv('ALPACA_API_KEY')
SECRET_KEY = os.getenv('ALPACA_SECRET_KEY')
BASE_URL = os.getenv('ALPACA_BASE_URL', 'https://paper-api.alpaca.markets')

# Headers for API requests
headers = {
    'APCA-API-KEY-ID': API_KEY,
    'APCA-API-SECRET-KEY': SECRET_KEY,
    'Content-Type': 'application/json'
}

def get_account():
    """Get account information"""
    response = requests.get(f"{BASE_URL}/v2/account", headers=headers)
    return response.json()

def place_order(symbol, qty, side='buy'):
    """Place a market order"""
    order_data = {
        'symbol': symbol,
        'qty': qty,
        'side': side,
        'type': 'market',
        'time_in_force': 'day'
    }
    response = requests.post(f"{BASE_URL}/v2/orders", headers=headers, json=order_data)
    return response.json()

def get_latest_trade(symbol):
    """Get latest trade price"""
    response = requests.get(f"{BASE_URL}/v2/stocks/{symbol}/trades/latest", headers=headers)
    return response.json()

def main():
    print("="*60)
    print("🧪 PLACING TEST TRADES")
    print("="*60)

    # Get account info
    try:
        account = get_account()
        print(f"\n📊 Account Info:")
        print(f"   Portfolio Value: ${float(account['portfolio_value']):,.2f}")
        print(f"   Cash Available: ${float(account['cash']):,.2f}")
        print(f"   Buying Power: ${float(account['buying_power']):,.2f}")
    except Exception as e:
        print(f"❌ Error getting account: {e}")
        return

    # Define test trades
    test_trades = [
        {'symbol': 'AAPL', 'qty': 1},
        {'symbol': 'NVDA', 'qty': 1},
    ]

    print(f"\n🎯 Will place {len(test_trades)} test trades:")
    for trade in test_trades:
        print(f"   - {trade['symbol']}: {trade['qty']} share(s)")

    print("\n📝 Placing orders...")

    successful = 0
    failed = 0

    for trade in test_trades:
        try:
            # Get current price
            try:
                latest = get_latest_trade(trade['symbol'])
                price = latest['trade']['p']
                print(f"\n{trade['symbol']}:")
                print(f"   Current Price: ${price:.2f}")
                print(f"   Estimated Cost: ${price * trade['qty']:.2f}")
            except:
                print(f"\n{trade['symbol']}: Placing order...")

            # Place order
            order = place_order(trade['symbol'], trade['qty'])

            if 'id' in order:
                print(f"   ✅ Order placed successfully!")
                print(f"   Order ID: {order['id']}")
                print(f"   Status: {order['status']}")
                successful += 1
            else:
                print(f"   ❌ Order failed: {order}")
                failed += 1

        except Exception as e:
            print(f"   ❌ Error: {e}")
            failed += 1

    # Summary
    print("\n" + "="*60)
    print("📊 SUMMARY")
    print("="*60)
    print(f"\n✅ Successful: {successful}")
    print(f"❌ Failed: {failed}")

    if successful > 0:
        print("\n" + "="*60)
        print("🤖 NEXT STEPS")
        print("="*60)
        print("\n1. Wait a few minutes for orders to fill")
        print("2. Run: python run_claude_bot.py")
        print("3. Claude will analyze and manage these positions")
        print("\nPress any key to exit...")

if __name__ == "__main__":
    main()
