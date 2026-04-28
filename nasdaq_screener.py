"""
Stock Screener with Claude AI
Analyzes your portfolio stocks and shows only high-confidence BUY opportunities
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


def screen_stocks(min_confidence=0.70):
    """
    Screen your portfolio stocks for high-confidence buy opportunities

    Args:
        min_confidence: Minimum confidence threshold (default 70%)
    """
    print("="*80)
    print("🔍 STOCK SCREENER - CLAUDE AI POWERED")
    print("="*80)
    print(f"\n📊 Configuration:")
    print(f"   Minimum Confidence: {min_confidence:.0%}")
    print(f"   Stocks to Analyze: {len(config.STOCK_UNIVERSE)}")
    print(f"   Portfolio: {', '.join(config.STOCK_UNIVERSE)}")
    print(f"   Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

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
    print(f"   Model: {config.CLAUDE_MODEL}")

    print(f"\n🔎 Analyzing stocks...\n")

    # Track results
    buy_opportunities = []
    analyzed = 0
    errors = 0

    stocks_to_analyze = config.STOCK_UNIVERSE

    for i, symbol in enumerate(stocks_to_analyze, 1):
        try:
            print(f"   [{i}/{len(stocks_to_analyze)}] Analyzing {symbol}...", end=' ')

            # Get data
            bars = bot.get_latest_bars([symbol], limit=100)
            if symbol not in bars:
                print("❌ No data")
                errors += 1
                continue

            df = bars[symbol]

            # Get current price
            current_price = bot.get_current_price(symbol)
            if current_price is None:
                print("❌ No price")
                errors += 1
                continue

            # Calculate technical indicators for summary
            df = bot.feature_engine.add_technical_indicators(df)
            latest = df.iloc[-1]

            # Get Claude's analysis
            decision = bot.analyze_with_claude(symbol, df)
            analyzed += 1

            # Show result
            if decision['action'] == 'buy' and decision['confidence'] >= min_confidence:
                print(f"🎯 BUY @ ${current_price:.2f} (Confidence: {decision['confidence']:.0%})")
                print(f"      RSI: {latest.get('rsi', 0):.1f} | MACD: {'Bullish' if latest.get('macd', 0) > latest.get('macd_signal', 0) else 'Bearish'} | ADX: {latest.get('adx', 0):.1f}")
                buy_opportunities.append({
                    'symbol': symbol,
                    'price': current_price,
                    'confidence': decision['confidence'],
                    'risk_level': decision['risk_level'],
                    'reasoning': decision['reasoning'],
                    'rsi': latest.get('rsi', 0),
                    'macd': latest.get('macd', 0),
                    'adx': latest.get('adx', 0),
                })
            elif decision['action'] == 'buy':
                print(f"⏸️  BUY but low confidence ({decision['confidence']:.0%})")
                print(f"      RSI: {latest.get('rsi', 0):.1f} | MACD: {'Bullish' if latest.get('macd', 0) > latest.get('macd_signal', 0) else 'Bearish'}")
            else:
                print(f"⏸️  {decision['action'].upper()} ({decision['confidence']:.0%})")
                print(f"      RSI: {latest.get('rsi', 0):.1f} | ADX: {latest.get('adx', 0):.1f}")

        except KeyboardInterrupt:
            print(f"\n\n⚠️  Analysis interrupted by user")
            break
        except Exception as e:
            print(f"❌ Error: {e}")
            errors += 1
            continue

    # Display results
    print("\n" + "="*80)
    print("📊 SCREENING RESULTS")
    print("="*80)
    print(f"\nStocks Analyzed: {analyzed}")
    print(f"Errors/Skipped: {errors}")
    print(f"Buy Opportunities Found: {len(buy_opportunities)}")

    if not buy_opportunities:
        print("\n❌ No high-confidence buy opportunities found.")
        print(f"   Try lowering the confidence threshold (current: {min_confidence:.0%})")
        return

    # Sort by confidence (highest first)
    buy_opportunities.sort(key=lambda x: x['confidence'], reverse=True)

    print(f"\n{'='*80}")
    print(f"🎯 BUY OPPORTUNITIES (Confidence >= {min_confidence:.0%})")
    print(f"{'='*80}\n")

    for i, opp in enumerate(buy_opportunities, 1):
        print(f"{i}. {opp['symbol']} @ ${opp['price']:.2f}")
        print(f"   Confidence: {opp['confidence']:.0%} | Risk: {opp['risk_level']}")
        print(f"   Indicators: RSI {opp.get('rsi', 0):.1f} | MACD {'Bullish' if opp.get('macd', 0) > 0 else 'Bearish'} | ADX {opp.get('adx', 0):.1f}")
        print(f"   Reasoning: {opp['reasoning']}")

        # Calculate potential position
        account = bot.get_account_info()
        position_value = account['cash'] * config.MAX_POSITION_SIZE
        shares = int(position_value / opp['price'])
        if shares > 0:
            print(f"   💰 Suggested Position: {shares} shares (${shares * opp['price']:.2f})")
        print()

    print("="*80)
    print("✅ Screening complete!")
    print("="*80)

    # Save results to file
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"logs/screen_results_{timestamp}.txt"

    with open(filename, 'w') as f:
        f.write("STOCK SCREENING RESULTS\n")
        f.write(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Min Confidence: {min_confidence:.0%}\n")
        f.write(f"Stocks Analyzed: {analyzed}\n\n")

        for i, opp in enumerate(buy_opportunities, 1):
            f.write(f"{i}. {opp['symbol']} @ ${opp['price']:.2f}\n")
            f.write(f"   Confidence: {opp['confidence']:.0%}\n")
            f.write(f"   Risk: {opp['risk_level']}\n")
            f.write(f"   Indicators: RSI {opp.get('rsi', 0):.1f} | MACD {'Bullish' if opp.get('macd', 0) > 0 else 'Bearish'} | ADX {opp.get('adx', 0):.1f}\n")
            f.write(f"   Reasoning: {opp['reasoning']}\n\n")

    print(f"\n📁 Results saved to: {filename}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Screen your portfolio stocks for buy opportunities')
    parser.add_argument('--confidence', type=float, default=0.70,
                       help='Minimum confidence threshold (default: 0.70 = 70%%)')

    args = parser.parse_args()

    screen_stocks(min_confidence=args.confidence)
