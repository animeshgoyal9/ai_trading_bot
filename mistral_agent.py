"""
Mistral AI Trading Agent
Uses Mistral to make intelligent trading decisions
"""
import json
import os
from datetime import datetime
import numpy as np
import pandas as pd
from loguru import logger
from mistralai import Mistral
from dotenv import load_dotenv

load_dotenv()
import config

# ── yfinance cache + throttle ─────────────────────────────────────────────────
_earnings_cache  = {}   # symbol → earnings dict
_enhanced_cache  = {}   # symbol → options/fundamentals dict
_last_yf_call    = 0.0  # timestamp of last yfinance call


def _yf_throttle():
    """Ensure at least 2s between yfinance calls."""
    import time
    global _last_yf_call
    gap = time.time() - _last_yf_call
    if gap < 2.0:
        time.sleep(2.0 - gap)
    _last_yf_call = time.time()


def get_enhanced_context(symbol: str) -> dict:
    """
    Fetch options flow, analyst targets, and fundamentals for a symbol.
    Returns a dict with keys like analyst_upside, pc_ratio, inst_buyer, pos52, etc.
    Results are cached per session to avoid redundant API calls.
    """
    if '/' in symbol:   # crypto — no options/analyst data
        return {}
    if symbol in _enhanced_cache:
        return _enhanced_cache[symbol]

    ctx = {}
    try:
        import yfinance as yf
        _yf_throttle()
        ticker = yf.Ticker(symbol)
        info   = ticker.info or {}

        price = info.get('currentPrice') or info.get('regularMarketPrice', 0)

        # ── Analyst price target ──────────────────────────────────────────
        target = info.get('targetMeanPrice', 0)
        if price and target:
            ctx['analyst_upside'] = round((target / price - 1) * 100, 1)
            ctx['analyst_target'] = round(target, 2)
            ctx['analyst_count']  = info.get('numberOfAnalystOpinions', 0)

        # ── 52-week position ──────────────────────────────────────────────
        w52h = info.get('fiftyTwoWeekHigh', 0)
        w52l = info.get('fiftyTwoWeekLow', 0)
        if price and w52h and w52l and w52h > w52l:
            ctx['pos52']   = round((price - w52l) / (w52h - w52l) * 100, 1)
            ctx['week52h'] = w52h
            ctx['week52l'] = w52l

        # ── Fundamentals ──────────────────────────────────────────────────
        fpe        = info.get('forwardPE')
        peg        = info.get('trailingPegRatio') or info.get('pegRatio')
        rev_growth = info.get('revenueGrowth')
        op_margins = info.get('operatingMargins')
        if fpe:        ctx['forward_pe']  = round(float(fpe), 1)
        if peg:        ctx['peg']         = round(float(peg), 2)
        if rev_growth: ctx['rev_growth']  = round(float(rev_growth) * 100, 1)
        if op_margins: ctx['op_margins']  = round(float(op_margins) * 100, 1)

        # ── Options flow ──────────────────────────────────────────────────
        try:
            _yf_throttle()
            exps = ticker.options
            if exps:
                chain    = ticker.option_chain(exps[0])
                calls_df = chain.calls.copy()
                puts_df  = chain.puts.copy()
                c_vol    = float(calls_df['volume'].fillna(0).sum())
                p_vol    = float(puts_df['volume'].fillna(0).sum())

                if p_vol > 0:
                    ctx['pc_ratio']  = round(c_vol / p_vol, 2)
                    ctx['call_vol']  = int(c_vol)
                    ctx['put_vol']   = int(p_vol)
                    if c_vol / p_vol < 0.7:
                        ctx['options_sentiment'] = 'Bearish (heavy put buying)'
                    elif c_vol / p_vol > 1.5:
                        ctx['options_sentiment'] = 'Bullish (heavy call buying)'
                    else:
                        ctx['options_sentiment'] = 'Neutral'

                # Institutional flow (same 4-signal proxy as dashboard)
                if c_vol > 200 and price:
                    signals = []
                    vol_by_strike = calls_df.groupby('strike')['volume'].sum().fillna(0)
                    total_c = float(vol_by_strike.sum())
                    if total_c > 0:
                        hhi = float(((vol_by_strike / total_c) ** 2).sum())
                        signals.append(min(100, hhi * 200))
                    deep_mask = calls_df['strike'] < price * 0.80
                    deep_vol  = float(calls_df.loc[deep_mask, 'volume'].fillna(0).sum())
                    signals.append(min(100, (deep_vol / c_vol) * 300))
                    max_block = float(calls_df['volume'].fillna(0).max())
                    signals.append(min(100, max_block / 20))
                    if total_c > 0:
                        top5_pct = float(vol_by_strike.nlargest(5).sum()) / total_c
                        signals.append(min(100, max(0, (top5_pct - 0.35) * 250)))
                    inst_conf = round(sum(signals) / len(signals))
                    ctx['inst_conf']  = inst_conf
                    ctx['inst_buyer'] = (
                        'Institutional' if inst_conf >= 55 else
                        'Mixed'         if inst_conf >= 30 else
                        'Retail'
                    )
        except Exception as _oe:
            logger.debug(f"[enhanced] options fetch failed for {symbol}: {_oe}")

    except Exception as e:
        logger.debug(f"[enhanced] context fetch failed for {symbol}: {e}")

    _enhanced_cache[symbol] = ctx
    return ctx

def get_earnings_context(symbol: str) -> dict:
    """Return a dict with upcoming earnings date, last surprise %, and beat streak.
    Returns empty dict for crypto or if data unavailable."""
    import time
    if '/' in symbol:   # crypto — no earnings
        return {}
    if symbol in _earnings_cache:
        return _earnings_cache[symbol]
    try:
        import yfinance as yf
        import requests
        # Throttle: min 2s between yfinance calls to avoid 429s
        global _last_yf_call
        gap = time.time() - _last_yf_call
        if gap < 2.0:
            time.sleep(2.0 - gap)
        _last_yf_call = time.time()

        ticker = yf.Ticker(symbol)

        ctx = {}

        # ── Next earnings date (uses quote endpoint, less rate-limited) ──
        try:
            dates_df = ticker.get_earnings_dates(limit=8)
            if dates_df is not None and not dates_df.empty:
                today = pd.Timestamp.utcnow().normalize()
                future = dates_df[dates_df.index.tz_localize(None) >= today] if dates_df.index.tz else dates_df[dates_df.index >= today]
                if not future.empty:
                    next_date = future.index[0]
                    if hasattr(next_date, 'tz_localize'):
                        next_date = next_date.tz_localize(None) if next_date.tzinfo else next_date
                    days_away = (next_date.normalize() - today).days
                    if 0 <= days_away <= 90:
                        ctx['next_earnings_date'] = next_date.strftime('%Y-%m-%d')
                        ctx['days_to_earnings']   = int(days_away)

                # Past quarters: pull EPS estimate vs actual for surprise
                past = dates_df[dates_df.index.tz_localize(None) < today] if dates_df.index.tz else dates_df[dates_df.index < today]
                if not past.empty:
                    eps_est_col  = next((c for c in past.columns if 'estimate' in c.lower()), None)
                    eps_act_col  = next((c for c in past.columns if 'actual' in c.lower() and 'eps' in c.lower()), None)
                    if eps_est_col and eps_act_col:
                        past = past[[eps_est_col, eps_act_col]].dropna()
                        if not past.empty:
                            surprises = []
                            for _, r in past.iterrows():
                                est = float(r[eps_est_col])
                                act = float(r[eps_act_col])
                                if est != 0:
                                    surprises.append((act - est) / abs(est) * 100)
                            if surprises:
                                ctx['last_surprise_pct'] = round(surprises[-1], 1)
                                streak = 0
                                for s in reversed(surprises):
                                    if s > 0:
                                        if streak >= 0: streak += 1
                                        else: break
                                    elif s < 0:
                                        if streak <= 0: streak -= 1
                                        else: break
                                    else:
                                        break
                                ctx['beat_streak'] = streak
        except Exception as e:
            logger.debug(f"[earnings] yfinance fetch failed for {symbol}: {e}")

        _earnings_cache[symbol] = ctx
        return ctx
    except Exception as e:
        logger.debug(f"[earnings] could not fetch for {symbol}: {e}")
        _earnings_cache[symbol] = {}
        return {}


class MistralTrader:
    """AI agent that uses Mistral to make trading decisions"""

    def __init__(self):
        self.api_key = os.getenv('MISTRAL_API_KEY', '')
        if not self.api_key:
            raise ValueError("MISTRAL_API_KEY not set in .env file")

        self.client = Mistral(api_key=self.api_key)
        self.model = os.getenv('MISTRAL_MODEL', 'mistral-small-latest')
        logger.info(f"Initialized Mistral Trading Agent with {self.model}")

    def analyze_and_decide(self, symbol, technical_data, market_context=None,
                           news_context=None, current_position=None):
        try:
            earnings_ctx  = get_earnings_context(symbol)
            enhanced_ctx  = get_enhanced_context(symbol)
            prompt = self._build_prompt(symbol, technical_data, market_context,
                                        current_position, earnings_ctx, enhanced_ctx)
            logger.info(f"Asking Mistral to analyze {symbol}...")

            from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout
            def _call():
                return self.client.chat.complete(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": self._get_system_prompt()},
                        {"role": "user", "content": prompt},
                    ],
                    temperature=0.1,
                    max_tokens=1000,
                )
            with ThreadPoolExecutor(max_workers=1) as ex:
                future = ex.submit(_call)
                try:
                    response = future.result(timeout=45)   # hard 45-second wall-clock timeout
                except FuturesTimeout:
                    future.cancel()
                    raise Exception("Mistral API timed out after 45 seconds")

            decision = self._parse_decision(response.choices[0].message.content)
            logger.info(f"Mistral's decision for {symbol}: {decision['action']} "
                        f"(confidence: {decision['confidence']:.0%})")
            return decision

        except Exception as e:
            logger.error(f"Error getting Mistral's analysis: {e}")
            return {
                'action': 'hold',
                'confidence': 0.0,
                'reasoning': f'Error: {str(e)}',
                'risk_level': 'high'
            }

    def _get_system_prompt(self):
        return """You are an aggressive quantitative trader with 20+ years of experience.
Your goal is to maximize returns by actively trading opportunities.

Trading rules — TECHNICALS:
- BUY on any bullish signal — oversold RSI, MACD crossover, strong momentum, or dip in an uptrend
- BUY during pullbacks and dips even in volatile conditions — these are opportunities
- SELL to lock in profits or cut losses quickly — don't let winners turn into losers
- HOLD only when there is absolutely no clear signal either way
- Favor action over inaction — missing a trade is worse than a small loss
- Volatility is your friend — high ATR stocks have bigger profit potential

Trading rules — EARNINGS:
- If a stock has 3+ consecutive earnings beats, lean bullish — serial outperformers keep outperforming
- If earnings is within 14 days and the stock is a serial beater, factor in pre-earnings drift
- If a stock has 2+ consecutive misses, be cautious — reduce confidence on buy signals

Trading rules — OPTIONS FLOW (high weight — smart money signals):
- P/C ratio < 0.7: heavy put buying — bearish signal, reduce buy confidence or lean sell
- P/C ratio > 1.5: heavy call buying — bullish signal, increase buy confidence
- Institutional flow detected (conf >= 55%): smart money is positioning — strong bullish signal, boost confidence significantly
- Retail-only flow: less conviction, standard weight
- Institutional buying + bullish P/C + good technicals = very high confidence BUY

Trading rules — ANALYST & FUNDAMENTALS:
- Analyst upside > 30%: Wall Street sees significant value, lean bullish
- Analyst upside < -10%: overvalued vs targets, reduce buy confidence
- 52-week position < 20%: near lows — opportunity zone, lean bullish
- 52-week position > 80%: extended — be cautious on new buys
- PEG < 1.0: undervalued relative to growth — bullish fundamental signal
- Strong revenue growth (>20%) supports bullish thesis

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

    def _build_prompt(self, symbol, technical_data, market_context, current_position,
                      earnings_ctx=None, enhanced_ctx=None):
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
            entry  = current_position.get('entry_price', 0)
            shares = current_position.get('shares', current_position.get('qty', 0))
            pl     = current_position.get('unrealized_pl', 0)
            plpc   = current_position.get('unrealized_plpc', 0)
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
            prompt += f"SMA 10/30-day: {technical_data['sma_fast']:.2f} / {technical_data['sma_slow']:.2f} - {trend}\n"
        price = technical_data.get('current_price', technical_data.get('close', 0))
        if 'sma_50' in technical_data and technical_data['sma_50']:
            rel = 'ABOVE' if price > technical_data['sma_50'] else 'BELOW'
            prompt += f"SMA 50-day: {technical_data['sma_50']:.2f} — price is {rel}\n"
        if 'sma_60' in technical_data and technical_data['sma_60']:
            rel = 'ABOVE' if price > technical_data['sma_60'] else 'BELOW'
            prompt += f"SMA 60-day: {technical_data['sma_60']:.2f} — price is {rel}\n"
        if 'sma_200' in technical_data and technical_data['sma_200']:
            rel = 'ABOVE' if price > technical_data['sma_200'] else 'BELOW'
            tag = ' ✅ BULL MARKET' if price > technical_data['sma_200'] else ' ⚠️ BEAR TERRITORY'
            prompt += f"SMA 200-day: {technical_data['sma_200']:.2f} — price is {rel}{tag}\n"
        if 'adx' in technical_data:
            prompt += f"ADX: {technical_data['adx']:.2f}\n"
        if 'volume_ratio' in technical_data:
            prompt += f"Volume Ratio: {technical_data['volume_ratio']:.2f}\n"

        if market_context:
            prompt += f"\nMARKET CONTEXT:\n{market_context}\n"

        # ── Earnings context ──────────────────────────────────────────
        if earnings_ctx:
            prompt += "\nEARNINGS CONTEXT:\n"
            if 'next_earnings_date' in earnings_ctx:
                days = earnings_ctx.get('days_to_earnings', '?')
                prompt += f"Next Earnings: {earnings_ctx['next_earnings_date']} ({days} days away)\n"
                if isinstance(days, int) and days <= 14:
                    prompt += "  ⚠️  Earnings within 2 weeks — factor in pre-earnings drift potential\n"
            if 'last_surprise_pct' in earnings_ctx:
                sp = earnings_ctx['last_surprise_pct']
                tag = 'BEAT' if sp > 0 else 'MISS'
                prompt += f"Last Earnings Surprise: {sp:+.1f}% ({tag})\n"
            if 'beat_streak' in earnings_ctx:
                streak = earnings_ctx['beat_streak']
                if streak >= 3:
                    prompt += f"Beat Streak: {streak} consecutive beats — serial outperformer, lean bullish\n"
                elif streak == 2:
                    prompt += f"Beat Streak: {streak} consecutive beats\n"
                elif streak <= -2:
                    prompt += f"Miss Streak: {abs(streak)} consecutive misses — caution\n"

        # ── Analyst targets + fundamentals ───────────────────────────────
        if enhanced_ctx:
            prompt += "\nANALYST & FUNDAMENTALS:\n"
            if 'analyst_upside' in enhanced_ctx:
                upside = enhanced_ctx['analyst_upside']
                target = enhanced_ctx.get('analyst_target', '')
                count  = enhanced_ctx.get('analyst_count', '')
                tag    = ' 🎯 STRONG UPSIDE' if upside > 30 else (' ⚠️ OVERVALUED' if upside < -10 else '')
                prompt += f"Analyst Target: ${target} ({upside:+.1f}% upside, {count} analysts){tag}\n"
            if 'pos52' in enhanced_ctx:
                pos = enhanced_ctx['pos52']
                tag = ' 🟢 Near 52W low — opportunity' if pos < 20 else (' 🔴 Near 52W high — extended' if pos > 80 else '')
                prompt += f"52-Week Position: {pos:.0f}% from low (low=${enhanced_ctx.get('week52l','')}, high=${enhanced_ctx.get('week52h','')}){tag}\n"
            parts = []
            if 'forward_pe' in enhanced_ctx: parts.append(f"Fwd P/E: {enhanced_ctx['forward_pe']}")
            if 'peg'        in enhanced_ctx: parts.append(f"PEG: {enhanced_ctx['peg']}" + (' 🟢 cheap' if enhanced_ctx['peg'] < 1.0 else ''))
            if 'rev_growth' in enhanced_ctx: parts.append(f"Rev Growth: {enhanced_ctx['rev_growth']:+.1f}%")
            if 'op_margins' in enhanced_ctx: parts.append(f"Op Margin: {enhanced_ctx['op_margins']:.1f}%")
            if parts:
                prompt += "Fundamentals: " + " | ".join(parts) + "\n"

            # ── Options flow ─────────────────────────────────────────────
            if 'pc_ratio' in enhanced_ctx:
                prompt += "\nOPTIONS FLOW:\n"
                pc   = enhanced_ctx['pc_ratio']
                cvol = enhanced_ctx.get('call_vol', 0)
                pvol = enhanced_ctx.get('put_vol', 0)
                sent = enhanced_ctx.get('options_sentiment', '')
                prompt += f"P/C Ratio: {pc:.2f} (calls {cvol:,} vs puts {pvol:,}) — {sent}\n"
                if 'inst_conf' in enhanced_ctx:
                    conf  = enhanced_ctx['inst_conf']
                    buyer = enhanced_ctx['inst_buyer']
                    tag   = ' 🏛 Smart money loading up — strong bullish signal' if buyer == 'Institutional' else \
                            ' 👤 Retail-driven flow — less conviction' if buyer == 'Retail' else ''
                    prompt += f"Institutional Flow: {conf}% confidence → {buyer} buying{tag}\n"

        prompt += f"""
TRADING PARAMETERS:
Stop Loss: {config.STOP_LOSS_PERCENT*100:.1f}% | Take Profit: {config.TAKE_PROFIT_PERCENT*100:.1f}%

Respond with ONLY a JSON object with "action" set to {action_options}."""
        return prompt

    def _sanitize_json(self, text):
        """Replace arithmetic expressions like 75410.05 * 0.93 with their computed values."""
        import re
        def eval_expr(match):
            try:
                return str(round(eval(match.group(0)), 2))  # noqa: S307
            except Exception:
                return match.group(0)
        # Match simple numeric expressions: number op number (no variables)
        return re.sub(r'[\d.]+\s*[\*\/\+\-]\s*[\d.]+', eval_expr, text)

    def _parse_decision(self, response_text):
        try:
            text = response_text.strip()
            if text.startswith('```'):
                text = text.split('```')[1]
                if text.startswith('json'):
                    text = text[4:]
                text = text.strip()

            text = self._sanitize_json(text)
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
            logger.error(f"Failed to parse Mistral response: {e}\nResponse: {response_text}")
            return {
                'action': 'hold',
                'confidence': 0.0,
                'reasoning': 'Failed to parse response',
                'risk_level': 'high'
            }
