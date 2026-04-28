"""
Comprehensive Stock Analyzer with Claude AI
Analyzes all your stocks and shows BUY/SELL/HOLD recommendations in a table
"""
import logging
import sys
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

from claude_trading_bot import ClaudeTradingBot
import config


def analyze_all_stocks(show_reasoning=False):
    """
    Analyze all stocks and show recommendations in a table

    Args:
        show_reasoning: Whether to show detailed reasoning for each stock
    """
    print("="*100)
    print("📊 COMPREHENSIVE STOCK ANALYSIS - CLAUDE AI POWERED")
    print("="*100)
    print(f"\n⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📈 Portfolio: {', '.join(config.STOCK_UNIVERSE)}")
    print(f"💰 Min Confidence Threshold: {config.CLAUDE_MIN_CONFIDENCE:.0%}")

    # Initialize bot
    print(f"\n🤖 Initializing Claude AI Trading Bot...")
    try:
        bot = ClaudeTradingBot()
    except Exception as e:
        print(f"❌ Failed to initialize: {e}")
        return

    # Check market status
    market_open = bot.is_market_open()
    print(f"   Market Status: {'🟢 OPEN' if market_open else '🔴 CLOSED'}")

    # Get current positions
    current_positions = bot.get_current_positions()
    if current_positions:
        print(f"\n💼 Current Holdings: {len(current_positions)} positions")
        for sym, pos in current_positions.items():
            pnl_pct = pos['unrealized_plpc'] * 100
            print(f"   {sym}: {pos['shares']} shares @ ${pos['entry_price']:.2f} | P&L: ${pos['unrealized_pl']:.2f} ({pnl_pct:+.1f}%)")
    else:
        print(f"\n💼 Current Holdings: None")

    print(f"\n🔎 Analyzing all stocks...\n")

    # Track results
    results = []

    for i, symbol in enumerate(config.STOCK_UNIVERSE, 1):
        try:
            print(f"   [{i}/{len(config.STOCK_UNIVERSE)}] Analyzing {symbol}...", end=' ', flush=True)

            # Get data
            bars = bot.get_latest_bars([symbol], limit=100)
            if symbol not in bars:
                print("❌ No data")
                results.append({
                    'symbol': symbol,
                    'action': 'ERROR',
                    'confidence': 0,
                    'price': 0,
                    'rsi': 0,
                    'reasoning': 'No data available',
                    'has_position': False
                })
                continue

            df = bars[symbol]

            # Get current price
            current_price = bot.get_current_price(symbol)
            if current_price is None:
                print("❌ No price")
                results.append({
                    'symbol': symbol,
                    'action': 'ERROR',
                    'confidence': 0,
                    'price': 0,
                    'rsi': 0,
                    'reasoning': 'Could not get price',
                    'has_position': False
                })
                continue

            # Calculate technical indicators
            df = bot.feature_engine.add_technical_indicators(df)
            latest = df.iloc[-1]

            # Check if we have a position
            has_position = symbol in current_positions
            current_position = current_positions.get(symbol) if has_position else None

            # Get Claude's analysis
            decision = bot.analyze_with_claude(symbol, df, current_position=current_position)

            # Store result
            result = {
                'symbol': symbol,
                'action': decision['action'].upper(),
                'confidence': decision['confidence'],
                'risk_level': decision['risk_level'],
                'price': current_price,
                'rsi': latest.get('rsi', 0),
                'macd': latest.get('macd', 0),
                'macd_signal': latest.get('macd_signal', 0),
                'adx': latest.get('adx', 0),
                'reasoning': decision['reasoning'],
                'has_position': has_position
            }

            if has_position:
                result['position'] = current_position

            results.append(result)

            # Quick feedback
            action_emoji = "🎯" if decision['action'] == 'buy' else "🔴" if decision['action'] == 'sell' else "⏸️"
            print(f"{action_emoji} {decision['action'].upper()} ({decision['confidence']:.0%})")

        except Exception as e:
            print(f"❌ Error: {e}")
            results.append({
                'symbol': symbol,
                'action': 'ERROR',
                'confidence': 0,
                'price': 0,
                'rsi': 0,
                'reasoning': str(e),
                'has_position': False
            })
            continue

    # Display results in table format
    print("\n" + "="*100)
    print("📊 ANALYSIS SUMMARY - ALL STOCKS")
    print("="*100)

    # Table header
    print(f"\n{'Stock':<8} {'Action':<8} {'Conf':<6} {'Price':<10} {'RSI':<6} {'MACD':<8} {'ADX':<6} {'Holdings':<20}")
    print("-" * 100)

    # Sort: SELL first (if holding), then BUY, then HOLD
    def sort_key(r):
        if r['action'] == 'SELL' and r['has_position']:
            return (0, -r['confidence'])  # Highest priority sells first
        elif r['action'] == 'BUY':
            return (1, -r['confidence'])  # Then buys
        elif r['action'] == 'SELL':
            return (2, -r['confidence'])  # Sells without position
        else:
            return (3, -r['confidence'])  # Then holds

    results.sort(key=sort_key)

    # Table rows
    buy_count = 0
    sell_count = 0
    hold_count = 0

    for r in results:
        if r['action'] == 'ERROR':
            continue

        # Action with emoji
        if r['action'] == 'BUY':
            action_str = "🎯 BUY"
            buy_count += 1
        elif r['action'] == 'SELL':
            action_str = "🔴 SELL"
            sell_count += 1
        else:
            action_str = "⏸️  HOLD"
            hold_count += 1

        # MACD trend
        macd_trend = "↗" if r.get('macd', 0) > r.get('macd_signal', 0) else "↘"

        # Holdings info
        if r['has_position']:
            pos = r['position']
            pnl_pct = pos['unrealized_plpc'] * 100
            holdings = f"{pos['shares']}sh ({pnl_pct:+.1f}%)"
        else:
            holdings = "-"

        # Color coding for confidence
        conf_str = f"{r['confidence']:.0%}"

        print(f"{r['symbol']:<8} {action_str:<12} {conf_str:<6} ${r['price']:<9.2f} {r['rsi']:<6.1f} {macd_trend:<8} {r['adx']:<6.1f} {holdings:<20}")

    print("-" * 100)
    print(f"{'Total:':<8} 🎯 {buy_count} BUY | 🔴 {sell_count} SELL | ⏸️  {hold_count} HOLD")
    print("="*100)

    # Show detailed reasoning if requested
    if show_reasoning:
        print("\n" + "="*100)
        print("📝 DETAILED REASONING")
        print("="*100)

        for r in results:
            if r['action'] == 'ERROR':
                continue

            action_emoji = "🎯" if r['action'] == 'BUY' else "🔴" if r['action'] == 'SELL' else "⏸️"
            print(f"\n{action_emoji} {r['symbol']} - {r['action']} (Confidence: {r['confidence']:.0%}, Risk: {r['risk_level']})")
            print(f"   Price: ${r['price']:.2f}")
            print(f"   Technical: RSI {r['rsi']:.1f} | MACD {'Bullish' if r.get('macd', 0) > r.get('macd_signal', 0) else 'Bearish'} | ADX {r['adx']:.1f}")
            if r['has_position']:
                pos = r['position']
                print(f"   Position: {pos['shares']} shares @ ${pos['entry_price']:.2f} | P&L: ${pos['unrealized_pl']:.2f} ({pos['unrealized_plpc']*100:+.1f}%)")
            print(f"   Reasoning: {r['reasoning']}")

        print("\n" + "="*100)

    # Action recommendations
    print("\n💡 RECOMMENDED ACTIONS:\n")

    # Urgent sells (holding positions Claude recommends selling)
    urgent_sells = [r for r in results if r['action'] == 'SELL' and r['has_position'] and r['confidence'] >= config.CLAUDE_MIN_CONFIDENCE]
    if urgent_sells:
        print("🔴 URGENT - SELL THESE POSITIONS:")
        for r in urgent_sells:
            pos = r['position']
            print(f"   {r['symbol']}: {pos['shares']} shares @ ${pos['entry_price']:.2f} → Current: ${r['price']:.2f}")
            print(f"      Confidence: {r['confidence']:.0%} | P&L: ${pos['unrealized_pl']:.2f} ({pos['unrealized_plpc']*100:+.1f}%)")
            print(f"      Reason: {r['reasoning'][:120]}...")
            print()

    # High confidence buys
    strong_buys = [r for r in results if r['action'] == 'BUY' and r['confidence'] >= 0.75]
    if strong_buys:
        print("🎯 HIGH CONFIDENCE BUYS (75%+):")
        for r in strong_buys:
            account = bot.get_account_info()
            shares = int((account['cash'] * config.MAX_POSITION_SIZE) / r['price'])
            print(f"   {r['symbol']}: ${r['price']:.2f} | Confidence: {r['confidence']:.0%} | Suggested: {shares} shares")
            print(f"      Reason: {r['reasoning'][:120]}...")
            print()

    # Moderate buys
    moderate_buys = [r for r in results if r['action'] == 'BUY' and config.CLAUDE_MIN_CONFIDENCE <= r['confidence'] < 0.75]
    if moderate_buys:
        print(f"📊 MODERATE BUYS ({config.CLAUDE_MIN_CONFIDENCE:.0%}-74%):")
        for r in moderate_buys:
            print(f"   {r['symbol']}: ${r['price']:.2f} | Confidence: {r['confidence']:.0%}")

    print("\n" + "="*100)

    # Save to file
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"logs/analysis_{timestamp}.txt"

    with open(filename, 'w') as f:
        f.write("COMPREHENSIVE STOCK ANALYSIS\n")
        f.write(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Stocks Analyzed: {len([r for r in results if r['action'] != 'ERROR'])}\n\n")

        f.write(f"{'Stock':<8} {'Action':<8} {'Conf':<6} {'Price':<10} {'RSI':<6} {'MACD':<8} {'Holdings':<20}\n")
        f.write("-" * 80 + "\n")

        for r in results:
            if r['action'] == 'ERROR':
                continue

            macd_trend = "Bullish" if r.get('macd', 0) > r.get('macd_signal', 0) else "Bearish"
            holdings = f"{r['position']['shares']}sh" if r['has_position'] else "-"

            f.write(f"{r['symbol']:<8} {r['action']:<8} {r['confidence']:<6.0%} ${r['price']:<9.2f} {r['rsi']:<6.1f} {macd_trend:<8} {holdings:<20}\n")

        f.write("\n\nDETAILED REASONING:\n\n")
        for r in results:
            if r['action'] == 'ERROR':
                continue
            f.write(f"{r['symbol']} - {r['action']} ({r['confidence']:.0%})\n")
            f.write(f"Reasoning: {r['reasoning']}\n\n")

    print(f"📁 Full analysis saved to: {filename}\n")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Analyze all stocks and show BUY/SELL/HOLD recommendations')
    parser.add_argument('--detailed', action='store_true',
                       help='Show detailed reasoning for each stock')

    args = parser.parse_args()

    analyze_all_stocks(show_reasoning=args.detailed)
