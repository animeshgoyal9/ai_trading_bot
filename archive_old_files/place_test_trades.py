"""
Place Test Trades
Execute 1-2 small test trades to verify the trading bot is working
"""
import alpaca_trade_api as tradeapi
import config


def place_test_trades():
    """Place small test trades to verify bot functionality"""

    print("="*60)
    print("🧪 PLACING TEST TRADES")
    print("="*60)

    # Initialize Alpaca API
    api = tradeapi.REST(
        config.ALPACA_API_KEY,
        config.ALPACA_SECRET_KEY,
        config.ALPACA_BASE_URL,
        api_version='v2'
    )

    # Get account info
    account = api.get_account()
    print(f"\n📊 Account Info:")
    print(f"   Portfolio Value: ${float(account.portfolio_value):,.2f}")
    print(f"   Cash Available: ${float(account.cash):,.2f}")
    print(f"   Buying Power: ${float(account.buying_power):,.2f}")

    # Define test trades - small positions in liquid stocks
    test_trades = [
        {'symbol': 'AAPL', 'qty': 1, 'reason': 'Liquid, stable tech stock'},
        {'symbol': 'NVDA', 'qty': 1, 'reason': 'AI/chip leader with momentum'},
    ]

    print(f"\n🎯 Will place {len(test_trades)} test trades:")
    for trade in test_trades:
        print(f"   - {trade['symbol']}: {trade['qty']} share(s) - {trade['reason']}")

    # Check if market is open
    clock = api.get_clock()
    if not clock.is_open:
        logger.warning("\n⚠️  Market is currently CLOSED")
        print("These orders will be queued and executed when market opens")
    else:
        print("\n✅ Market is OPEN - orders will execute immediately")

    # Place orders
    successful_orders = []
    failed_orders = []

    print("\n📝 Placing orders...")

    for trade in test_trades:
        try:
            # Get current price for logging
            try:
                quote = api.get_latest_trade(trade['symbol'])
                current_price = quote.price
                estimated_cost = current_price * trade['qty']
                print(f"\n{trade['symbol']}:")
                print(f"   Current Price: ${current_price:.2f}")
                print(f"   Estimated Cost: ${estimated_cost:.2f}")
            except Exception as e:
                print(f"   Could not get price: {e}")
                current_price = None

            # Place market order
            order = api.submit_order(
                symbol=trade['symbol'],
                qty=trade['qty'],
                side='buy',
                type='market',
                time_in_force='day'
            )

            print(f"   ✅ Order placed successfully!")
            print(f"   Order ID: {order.id}")
            print(f"   Status: {order.status}")

            successful_orders.append({
                'symbol': trade['symbol'],
                'qty': trade['qty'],
                'order_id': order.id,
                'price': current_price
            })

        except Exception as e:
            print(f"   ❌ Failed to place order: {e}")
            failed_orders.append({
                'symbol': trade['symbol'],
                'error': str(e)
            })

    # Summary
    print("\n" + "="*60)
    print("📊 TEST TRADES SUMMARY")
    print("="*60)

    if successful_orders:
        print(f"\n✅ Successfully placed {len(successful_orders)} order(s):")
        for order in successful_orders:
            print(f"   {order['symbol']}: {order['qty']} share(s)")
            print(f"      Order ID: {order['order_id']}")
            if order['price']:
                print(f"      Est. Price: ${order['price']:.2f}")

    if failed_orders:
        print(f"\n❌ Failed to place {len(failed_orders)} order(s):")
        for order in failed_orders:
            print(f"   {order['symbol']}: {order['error']}")

    print("\n" + "="*60)
    print("🤖 NEXT STEPS")
    print("="*60)
    print("\n1. Wait a few minutes for orders to fill")
    print("2. Run: python run_claude_bot.py")
    print("3. Claude will analyze these positions and manage them")
    print("4. Claude may HOLD, SELL, or add to positions based on analysis")
    print("\nPress Ctrl+C to exit\n")


if __name__ == "__main__":
    place_test_trades()
