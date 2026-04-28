"""
Gemini AI Trading Agent
Uses Google's Gemini to make intelligent trading decisions
"""
import json
from datetime import datetime
from loguru import logger
from google import genai
import config


class GeminiTrader:
    """AI agent that uses Google Gemini to make trading decisions"""

    def __init__(self):
        self.api_key = config.GEMINI_API_KEY
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY not set in .env file")

        self.client = genai.Client(api_key=self.api_key)
        self.model = 'gemini-2.0-flash'
        logger.info(f"Initialized Gemini Trading Agent with {self.model}")

    def analyze_and_decide(self, symbol, technical_data, market_context=None,
                           news_context=None, current_position=None):
        try:
            prompt = self._build_prompt(symbol, technical_data, market_context, current_position)
            logger.info(f"Asking Gemini to analyze {symbol}...")

            response = self.client.models.generate_content(
                model=self.model,
                contents=self._get_system_prompt() + "\n\n" + prompt,
            )

            decision = self._parse_decision(response.text)
            logger.info(f"Gemini's decision for {symbol}: {decision['action']} "
                        f"(confidence: {decision['confidence']:.0%})")
            return decision

        except Exception as e:
            logger.error(f"Error getting Gemini's analysis: {e}")
            return {
                'action': 'hold',
                'confidence': 0.0,
                'reasoning': f'Error: {str(e)}',
                'risk_level': 'high'
            }

    def _get_system_prompt(self):
        return """You are an expert quantitative trading analyst with 20+ years of experience.
Analyze stock/crypto data and make informed trading decisions.

Trading rules:
- Only recommend BUY when there's clear opportunity with good risk/reward
- Only recommend SELL when there's clear reason to exit
- Recommend HOLD when signals are mixed or unclear
- Always consider downside risk
- Be conservative

You must respond with ONLY a JSON object (no markdown, no other text):
{
    "action": "buy", "hold", or "sell",
    "confidence": 0.0 to 1.0,
    "reasoning": "detailed analysis",
    "risk_level": "low", "medium", or "high",
    "key_factors": ["factor1", "factor2"],
    "entry_price_recommendation": null,
    "stop_loss_recommendation": null,
    "take_profit_recommendation": null
}"""

    def _build_prompt(self, symbol, technical_data, market_context, current_position):
        has_position = current_position is not None
        if has_position:
            task = f"Analyze {symbol} and decide: SELL our position or HOLD it."
            action_options = '"sell" or "hold"'
        else:
            task = f"Analyze {symbol} and decide: BUY or HOLD."
            action_options = '"buy" or "hold"'

        prompt = f"""{task}

Stock: {symbol}
Current Price: ${technical_data.get('current_price', 0):.2f}
Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}
"""
        if has_position:
            entry = current_position.get('entry_price', 0)
            shares = current_position.get('shares', current_position.get('qty', 0))
            pl = current_position.get('unrealized_pl', 0)
            plpc = current_position.get('unrealized_plpc', 0)
            prompt += f"""
CURRENT POSITION:
Entry Price: ${entry:.2f}
Shares/Units: {shares}
P&L: ${pl:.2f} ({plpc*100:.1f}%)
"""

        prompt += "\nTECHNICAL INDICATORS:\n"
        if 'rsi' in technical_data:
            rsi = technical_data['rsi']
            tag = ' (OVERSOLD)' if rsi < 30 else ' (OVERBOUGHT)' if rsi > 70 else ''
            prompt += f"RSI (14): {rsi:.2f}{tag}\n"
        if 'macd' in technical_data:
            direction = 'BULLISH' if technical_data.get('macd_diff', 0) > 0 else 'BEARISH'
            prompt += f"MACD: {technical_data['macd']:.4f} - {direction}\n"
        if 'sma_fast' in technical_data and 'sma_slow' in technical_data:
            trend = 'UPTREND' if technical_data['sma_fast'] > technical_data['sma_slow'] else 'DOWNTREND'
            prompt += f"SMA Fast/Slow: {technical_data['sma_fast']:.2f} / {technical_data['sma_slow']:.2f} - {trend}\n"
        if 'adx' in technical_data:
            prompt += f"ADX: {technical_data['adx']:.2f}\n"
        if 'volume_ratio' in technical_data:
            prompt += f"Volume Ratio: {technical_data['volume_ratio']:.2f}\n"

        if market_context:
            prompt += f"\nMARKET CONTEXT:\n{market_context}\n"

        prompt += f"""
TRADING PARAMETERS:
Stop Loss: {config.STOP_LOSS_PERCENT*100:.1f}% | Take Profit: {config.TAKE_PROFIT_PERCENT*100:.1f}%

Respond with ONLY a JSON object with "action" set to {action_options}."""
        return prompt

    def _parse_decision(self, response_text):
        try:
            text = response_text.strip()
            if text.startswith('```'):
                text = text.split('```')[1]
                if text.startswith('json'):
                    text = text[4:]
                text = text.strip()

            decision = json.loads(text)
            for field in ['action', 'confidence', 'reasoning', 'risk_level']:
                if field not in decision:
                    raise ValueError(f"Missing field: {field}")

            decision['action'] = decision['action'].lower()
            if decision['action'] not in ['buy', 'hold', 'sell']:
                decision['action'] = 'hold'
            decision['confidence'] = max(0.0, min(1.0, float(decision['confidence'])))
            return decision

        except Exception as e:
            logger.error(f"Failed to parse Gemini response: {e}\nResponse: {response_text}")
            return {
                'action': 'hold',
                'confidence': 0.0,
                'reasoning': 'Failed to parse response',
                'risk_level': 'high'
            }
