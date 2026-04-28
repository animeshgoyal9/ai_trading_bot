"""
Claude AI Trading Agent
Uses Claude's reasoning to decide when to trade
"""
import anthropic
import json
from datetime import datetime
from loguru import logger
import config


class ClaudeTrader:
    """AI agent that uses Claude to make trading decisions"""

    def __init__(self):
        self.api_key = config.ANTHROPIC_API_KEY
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY not set in .env file")

        # max_retries=5 handles 529 overloaded errors automatically with backoff
        self.client = anthropic.Anthropic(api_key=self.api_key, max_retries=5)
        self.model = config.CLAUDE_MODEL
        logger.info(f"Initialized Claude Trading Agent with {self.model}")

    def analyze_and_decide(self, symbol, technical_data, market_context=None, current_position=None):
        """
        Ask Claude to analyze the stock and decide whether to trade

        Args:
            symbol: Stock ticker
            technical_data: Dict with technical indicators
            market_context: Optional market context (news, etc.)
            current_position: Optional dict with current position info (for sell decisions)

        Returns:
            Dict with decision, confidence, and reasoning
        """
        try:
            # Prepare the analysis prompt
            prompt = self._build_analysis_prompt(symbol, technical_data, market_context, current_position)

            # Ask Claude
            logger.info(f"Asking Claude to analyze {symbol}...")
            response = self.client.messages.create(
                model=self.model,
                max_tokens=2000,
                temperature=0.1,  # Low temperature for consistent decisions
                system=self._get_system_prompt(),
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            # Parse Claude's response
            decision = self._parse_decision(response.content[0].text)

            logger.info(f"Claude's decision for {symbol}: {decision['action']} "
                       f"(confidence: {decision['confidence']:.0%})")
            logger.debug(f"Reasoning: {decision['reasoning'][:200]}...")

            return decision

        except Exception as e:
            logger.error(f"Error getting Claude's analysis: {e}")
            return {
                'action': 'hold',
                'confidence': 0.0,
                'reasoning': f'Error: {str(e)}',
                'risk_level': 'high'
            }

    def _get_system_prompt(self):
        """System prompt that defines Claude's role as a trader"""
        return """You are an expert quantitative trading analyst with 20+ years of experience.
Your role is to analyze stock data and make informed trading decisions.

Your analysis approach:
1. Review all technical indicators carefully
2. Consider risk/reward ratios
3. Think about market conditions and context
4. Make conservative, risk-aware decisions
5. Explain your reasoning clearly

Trading rules you MUST follow:
- Only recommend BUY when there's clear opportunity with good risk/reward
- Only recommend SELL when there's clear reason to exit (take profits, cut losses, negative outlook)
- Recommend HOLD when signals are mixed or unclear
- Never recommend trades during extreme volatility without clear edge
- Always consider downside risk
- Be conservative - it's better to miss an opportunity than lose money

Output format:
You must respond with ONLY a JSON object (no other text) with this structure:
{
    "action": "buy", "hold", or "sell",
    "confidence": 0.0 to 1.0,
    "reasoning": "Your detailed analysis explaining why",
    "risk_level": "low", "medium", or "high",
    "key_factors": ["factor1", "factor2", "factor3"],
    "entry_price_recommendation": float or null,
    "stop_loss_recommendation": float or null,
    "take_profit_recommendation": float or null
}"""

    def _build_analysis_prompt(self, symbol, technical_data, market_context, current_position=None):
        """Build the prompt with all relevant data"""

        # Different prompt based on whether we have a position
        has_position = current_position is not None

        if has_position:
            task_description = f"Analyze {symbol} and decide if we should SELL our position or HOLD it."
            action_options = '"sell" or "hold"'
        else:
            task_description = f"Analyze {symbol} and decide if we should BUY or HOLD."
            action_options = '"buy" or "hold"'

        prompt = f"""{task_description}

CURRENT DATA:
=============

Stock: {symbol}
Current Price: ${technical_data.get('current_price', 0):.2f}
Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}
"""

        # Add position information if we have one
        if has_position:
            entry_price = current_position.get('entry_price', 0)
            shares = current_position.get('shares', 0)
            unrealized_pl = current_position.get('unrealized_pl', 0)
            unrealized_plpc = current_position.get('unrealized_plpc', 0)

            prompt += f"""
CURRENT POSITION:
-----------------
Entry Price: ${entry_price:.2f}
Shares: {shares}
Current P&L: ${unrealized_pl:.2f} ({unrealized_plpc*100:.1f}%)

"""

        prompt += """TECHNICAL INDICATORS:
--------------------
"""

        # Add technical indicators
        if 'rsi' in technical_data:
            prompt += f"RSI (14): {technical_data['rsi']:.2f}"
            if technical_data['rsi'] < 30:
                prompt += " (OVERSOLD) ⚠️\n"
            elif technical_data['rsi'] > 70:
                prompt += " (OVERBOUGHT) ⚠️\n"
            else:
                prompt += " (neutral)\n"

        if 'macd' in technical_data:
            macd_signal = "BULLISH 📈" if technical_data.get('macd_diff', 0) > 0 else "BEARISH 📉"
            prompt += f"MACD: {technical_data['macd']:.4f} (Signal: {technical_data.get('macd_signal', 0):.4f}) - {macd_signal}\n"

        if 'sma_fast' in technical_data and 'sma_slow' in technical_data:
            trend = "UPTREND 📈" if technical_data['sma_fast'] > technical_data['sma_slow'] else "DOWNTREND 📉"
            prompt += f"SMA Fast/Slow: {technical_data['sma_fast']:.2f} / {technical_data['sma_slow']:.2f} - {trend}\n"

        if 'bb_position' in technical_data:
            bb_pos = technical_data['bb_position']
            if bb_pos < 0.2:
                bb_signal = "Near lower band (potential bounce)"
            elif bb_pos > 0.8:
                bb_signal = "Near upper band (potential reversal)"
            else:
                bb_signal = "Middle of bands"
            prompt += f"Bollinger Bands Position: {bb_pos:.2f} - {bb_signal}\n"

        if 'adx' in technical_data:
            strength = "Strong" if technical_data['adx'] > 25 else "Weak"
            prompt += f"ADX (Trend Strength): {technical_data['adx']:.2f} - {strength} trend\n"

        if 'volume_ratio' in technical_data:
            vol_signal = "HIGH" if technical_data['volume_ratio'] > 1.5 else "NORMAL"
            prompt += f"Volume Ratio: {technical_data['volume_ratio']:.2f} - {vol_signal}\n"

        if 'volatility' in technical_data:
            prompt += f"Volatility (Annual): {technical_data['volatility']*100:.1f}%\n"

        # Add price momentum
        if 'momentum_5' in technical_data and 'momentum_10' in technical_data:
            prompt += f"\nPrice Momentum:\n"
            prompt += f"  5-day: ${technical_data['momentum_5']:.2f}\n"
            prompt += f"  10-day: ${technical_data['momentum_10']:.2f}\n"

        # Add returns
        if 'returns' in technical_data:
            prompt += f"  Recent return: {technical_data['returns']*100:.2f}%\n"

        # Add market context if available
        if market_context:
            prompt += f"\nMARKET CONTEXT:\n"
            prompt += f"--------------------\n"
            if 'vix' in market_context:
                vix_level = "HIGH FEAR" if market_context['vix'] > 25 else "LOW FEAR"
                prompt += f"VIX (Fear Index): {market_context['vix']:.2f} - {vix_level}\n"
            if 'news_summary' in market_context:
                prompt += f"Recent News: {market_context['news_summary']}\n"
            if 'market_trend' in market_context:
                prompt += f"Overall Market: {market_context['market_trend']}\n"

        prompt += f"""

TRADING PARAMETERS:
------------------
Position Size: {config.MAX_POSITION_SIZE*100:.0f}% of capital
Stop Loss: {config.STOP_LOSS_PERCENT*100:.1f}% below entry
Take Profit: {config.TAKE_PROFIT_PERCENT*100:.1f}% above entry

YOUR TASK:
----------
Based on this data, what should we do with {symbol}?

Consider:
"""
        if has_position:
            prompt += """1. Should we take profits or let it run?
2. Has the reason we bought changed?
3. Is there negative news or technical deterioration?
4. Are there better opportunities elsewhere?
5. Should we cut losses or hold for recovery?
"""
        else:
            prompt += """1. Is there a clear technical setup?
2. Is the risk/reward favorable?
3. Are we buying at a good price?
4. What could go wrong?
5. Does this fit our risk parameters?
"""

        prompt += f"""
Respond with ONLY a JSON object (no markdown, no other text) with "action" set to {action_options}.
Follow the exact format specified in your system prompt."""

        return prompt

    def _parse_decision(self, response_text):
        """Parse Claude's response into a structured decision"""
        try:
            # Try to extract JSON from response
            response_text = response_text.strip()

            # Remove markdown code blocks if present
            if response_text.startswith('```'):
                response_text = response_text.split('```')[1]
                if response_text.startswith('json'):
                    response_text = response_text[4:]
                response_text = response_text.strip()

            # Parse JSON
            decision = json.loads(response_text)

            # Validate required fields
            required_fields = ['action', 'confidence', 'reasoning', 'risk_level']
            for field in required_fields:
                if field not in decision:
                    raise ValueError(f"Missing required field: {field}")

            # Normalize action
            decision['action'] = decision['action'].lower()
            if decision['action'] not in ['buy', 'hold', 'sell']:
                logger.warning(f"Invalid action '{decision['action']}', defaulting to 'hold'")
                decision['action'] = 'hold'

            # Ensure confidence is between 0 and 1
            decision['confidence'] = max(0.0, min(1.0, float(decision['confidence'])))

            return decision

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Claude's response as JSON: {e}")
            logger.error(f"Response was: {response_text}")
            return {
                'action': 'hold',
                'confidence': 0.0,
                'reasoning': 'Failed to parse response',
                'risk_level': 'high'
            }
        except Exception as e:
            logger.error(f"Error parsing decision: {e}")
            return {
                'action': 'hold',
                'confidence': 0.0,
                'reasoning': f'Error: {str(e)}',
                'risk_level': 'high'
            }

    def get_portfolio_advice(self, current_positions, market_data):
        """
        Get Claude's advice on overall portfolio management

        Args:
            current_positions: List of current positions
            market_data: Current market conditions

        Returns:
            Dict with portfolio recommendations
        """
        try:
            prompt = f"""Review my current trading portfolio and provide recommendations.

CURRENT POSITIONS:
=================
"""
            if not current_positions:
                prompt += "No open positions\n"
            else:
                for pos in current_positions:
                    prompt += f"\n{pos['symbol']}:\n"
                    prompt += f"  Shares: {pos.get('shares', 0)}\n"
                    prompt += f"  Entry: ${pos.get('entry_price', 0):.2f}\n"
                    prompt += f"  Current: ${pos.get('current_price', 0):.2f}\n"
                    prompt += f"  P&L: ${pos.get('unrealized_pl', 0):.2f} ({pos.get('unrealized_plpc', 0)*100:.1f}%)\n"

            prompt += f"""

MARKET CONDITIONS:
=================
{json.dumps(market_data, indent=2)}

QUESTIONS:
==========
1. Should I hold or exit any positions?
2. Is the portfolio well-balanced?
3. What are the biggest risks?
4. Any recommendations for improvement?

Provide your analysis in a clear, actionable format."""

            response = self.client.messages.create(
                model=self.model,
                max_tokens=1500,
                temperature=0.3,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            advice = response.content[0].text
            logger.info("Received portfolio advice from Claude")

            return {
                'advice': advice,
                'timestamp': datetime.now()
            }

        except Exception as e:
            logger.error(f"Error getting portfolio advice: {e}")
            return {
                'advice': f'Error: {str(e)}',
                'timestamp': datetime.now()
            }
