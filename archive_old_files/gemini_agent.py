"""
Gemini AI Trading Agent
Uses Google's Gemini to make intelligent trading decisions
"""
import google.generativeai as genai
import json
from datetime import datetime
from loguru import logger
import config


class GeminiTrader:
    """AI agent that uses Google Gemini to make trading decisions"""

    def __init__(self):
        self.api_key = config.GEMINI_API_KEY
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY not set in .env file")

        # Configure Gemini
        genai.configure(api_key=self.api_key)

        # Initialize model
        self.model_name = config.GEMINI_MODEL
        self.model = genai.GenerativeModel(
            model_name=self.model_name,
            generation_config={
                'temperature': 0.1,  # Low for consistent decisions
                'top_p': 0.95,
                'top_k': 40,
                'max_output_tokens': 2048,
            }
        )

        logger.info(f"Initialized Gemini Trading Agent with {self.model_name}")

    def analyze_and_decide(self, symbol, technical_data, market_context=None, news_context=None, current_position=None):
        """
        Ask Gemini to analyze the stock and decide whether to trade

        Args:
            symbol: Stock ticker
            technical_data: Dict with technical indicators
            market_context: Optional market context
            news_context: Optional news headlines context
            current_position: Optional dict with current position info (for sell decisions)

        Returns:
            Dict with decision, confidence, and reasoning
        """
        try:
            # Build the prompt
            prompt = self._build_analysis_prompt(symbol, technical_data, market_context, news_context, current_position)

            # Ask Gemini
            logger.info(f"Asking Gemini to analyze {symbol}...")
            response = self.model.generate_content(prompt)

            # Parse response
            decision = self._parse_decision(response.text)

            logger.info(f"Gemini's decision for {symbol}: {decision['action']} "
                       f"(confidence: {decision['confidence']:.0%})")
            logger.debug(f"Reasoning: {decision['reasoning'][:200]}...")

            return decision

        except Exception as e:
            logger.error(f"Error getting Gemini's analysis: {e}")
            return {
                'action': 'hold',
                'confidence': 0.0,
                'reasoning': f'Error: {str(e)}',
                'risk_level': 'high'
            }

    def _build_analysis_prompt(self, symbol, technical_data, market_context, news_context=None, current_position=None):
        """Build comprehensive analysis prompt for Gemini"""

        # Different prompt based on whether we have a position
        has_position = current_position is not None

        if has_position:
            task_description = f"Analyze {symbol} and decide if we should SELL our position or HOLD it."
            action_options = '"sell" or "hold"'
        else:
            task_description = f"Analyze {symbol} and decide if we should BUY or HOLD."
            action_options = '"buy" or "hold"'

        prompt = f"""You are an expert quantitative trading analyst with 20+ years of experience.
Your role is to analyze stock data and make informed trading decisions.

IMPORTANT RULES:
- Only recommend BUY when there's clear opportunity with good risk/reward
- Only recommend SELL when there's clear reason to exit (better opportunities, negative outlook, risk management)
- Recommend HOLD when signals are mixed or unclear
- Be conservative - it's better to miss an opportunity than lose money
- Always consider downside risk
- Consider both technical indicators AND news sentiment

ANALYSIS TASK:
{task_description}

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
            rsi_signal = "OVERSOLD ⚠️" if technical_data['rsi'] < 30 else "OVERBOUGHT ⚠️" if technical_data['rsi'] > 70 else "neutral"
            prompt += f"RSI (14): {technical_data['rsi']:.2f} ({rsi_signal})\n"

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

        # Add market context
        if market_context:
            prompt += f"\nMARKET CONTEXT:\n"
            prompt += f"--------------------\n"
            if 'vix' in market_context:
                vix_level = "HIGH FEAR" if market_context['vix'] > 25 else "LOW FEAR"
                prompt += f"VIX (Fear Index): {market_context['vix']:.2f} - {vix_level}\n"
            if 'market_trend' in market_context:
                prompt += f"Overall Market: {market_context['market_trend']}\n"

        # Add news context
        if news_context:
            prompt += f"\nRECENT NEWS & SENTIMENT:\n"
            prompt += f"--------------------\n"
            prompt += news_context + "\n"
            prompt += "\nConsider how these headlines might impact the price in the short term.\n"

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
5. How does current news sentiment affect our position?
"""
        else:
            prompt += """1. Is there a clear technical setup?
2. Is the risk/reward favorable?
3. Are we buying at a good price?
4. What could go wrong?
5. How does the news sentiment align with technical signals?
"""

        prompt += f"""
OUTPUT FORMAT (IMPORTANT):
You MUST respond with ONLY a valid JSON object (no markdown, no extra text) with this exact structure:
{{
    "action": {action_options},
    "confidence": 0.0 to 1.0,
    "reasoning": "Your detailed analysis explaining why (consider both technicals and news)",
    "risk_level": "low", "medium", or "high",
    "key_factors": ["factor1", "factor2", "factor3"]
}}

Respond now with ONLY the JSON:"""

        return prompt

    def _parse_decision(self, response_text):
        """Parse Gemini's response into structured decision"""
        try:
            # Clean up response
            response_text = response_text.strip()

            # Remove markdown code blocks if present
            if '```json' in response_text:
                response_text = response_text.split('```json')[1].split('```')[0]
            elif '```' in response_text:
                response_text = response_text.split('```')[1].split('```')[0]

            # Extract JSON if embedded in text
            if '{' in response_text and '}' in response_text:
                start = response_text.find('{')
                end = response_text.rfind('}') + 1
                response_text = response_text[start:end]

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
            logger.error(f"Failed to parse Gemini's response as JSON: {e}")
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
        Get Gemini's advice on overall portfolio management

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
                    prompt += f"  P&L: ${pos.get('unrealized_pl', 0):.2f}\n"

            prompt += f"""

MARKET CONDITIONS:
=================
{json.dumps(market_data, indent=2)}

Provide clear, actionable portfolio advice covering:
1. Should I hold or exit any positions?
2. What are the biggest risks?
3. Any recommendations?"""

            response = self.model.generate_content(prompt)
            advice = response.text

            logger.info("Received portfolio advice from Gemini")

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
