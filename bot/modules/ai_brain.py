"""
Macro Pulse — Couche 10 : AI Brain — Multi-Agent Decision System.
3 independent AI agents vote on trading decisions via OpenRouter.
"""

import sys
import os
import asyncio
import json
import re
import logging
from datetime import datetime, timezone

import aiohttp

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

logger = logging.getLogger("ai_brain")

OPENROUTER_URL = f"{config.OPENROUTER_BASE_URL}/chat/completions"
HEADERS = {
    "Authorization": f"Bearer {config.OPENROUTER_API_KEY}",
    "Content-Type": "application/json",
    "HTTP-Referer": "https://macro-pulse.app",
    "X-Title": "Macro Pulse Trading Bot",
}

# Load prompt templates
_PROMPTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "prompts")


def _load_prompt(filename: str) -> str:
    path = os.path.join(_PROMPTS_DIR, filename)
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        logger.warning("Prompt file not found: %s", path)
        return ""


SYSTEM_PROMPTS = {
    1: _load_prompt("agent_quant_system.txt"),
    2: _load_prompt("agent_macro_system.txt"),
    3: _load_prompt("agent_contrarian_system.txt"),
}

ANALYSIS_TEMPLATE = _load_prompt("analysis_template.txt")
SYNTHESIS_TEMPLATE = _load_prompt("synthesis_template.txt")

AGENT_MODELS = {
    1: config.AGENT_QUANT_MODEL,
    2: config.AGENT_MACRO_MODEL,
    3: config.AGENT_CONTRARIAN_MODEL,
}

AGENT_NAMES = {
    1: "The Quant",
    2: "The Macro Strategist",
    3: "The Contrarian",
}


class AIBrain:
    """Multi-agent AI decision system with consensus voting."""

    def __init__(self):
        self.calibration_factors = {1: 1.0, 2: 1.0, 3: 1.0}
        self.calibration_history: dict[int, list[dict]] = {1: [], 2: [], 3: []}

    # ──────────────────── Prompt Building ──────────────────────────

    def build_analysis_prompt(
        self,
        event_data: dict | None = None,
        market_data: dict | None = None,
        technical_data: dict | None = None,
        tradfi_data: dict | None = None,
        defi_data: dict | None = None,
        options_data: dict | None = None,
        sentiment_data: dict | None = None,
        whale_data: dict | None = None,
        regime_data: dict | None = None,
    ) -> str:
        ev = event_data or {}
        mk = market_data or {}
        te = technical_data or {}
        tf = tradfi_data or {}
        df = defi_data or {}
        op = options_data or {}
        se = sentiment_data or {}
        wh = whale_data or {}
        rg = regime_data or {}

        liq = mk.get("estimated_liquidation_levels", {})
        if isinstance(liq, str):
            try:
                liq = json.loads(liq)
            except Exception:
                liq = {}

        liq_10x = liq.get("10", liq.get(10, {}))
        liq_25x = liq.get("25", liq.get(25, {}))

        replacements = {
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
            "regime": rg.get("regime", "NEUTRAL"),
            "regime_confidence": rg.get("confidence", 0),
            # Event
            "event_name": ev.get("event_name", "N/A"),
            "country": ev.get("country", "N/A"),
            "impact": ev.get("impact", "N/A"),
            "priority": "HIGH" if ev.get("is_priority") else "NORMAL",
            "actual": ev.get("actual", "N/A"),
            "forecast": ev.get("forecast", "N/A"),
            "previous": ev.get("previous", "N/A"),
            "surprise_score": ev.get("surprise_score", "N/A"),
            "revision_adjusted": ev.get("revision_adjusted_surprise", "N/A"),
            "cumulative_momentum": ev.get("cumulative_surprise_momentum", "N/A"),
            # Market
            "symbol": mk.get("symbol", "BTC/USDT"),
            "price": mk.get("price", "N/A"),
            "volume_24h": mk.get("volume_24h", "N/A"),
            "change_24h": mk.get("change_24h", "N/A"),
            "funding_rate": mk.get("funding_rate", "N/A"),
            "open_interest": mk.get("open_interest", "N/A"),
            "long_short_ratio": mk.get("long_short_ratio", "N/A"),
            "fear_greed": mk.get("fear_greed_index", "N/A"),
            "fear_greed_label": mk.get("fear_greed_label", "N/A"),
            # Technical
            "timeframe": te.get("timeframe", "1h"),
            "rsi": te.get("rsi", "N/A"),
            "rsi_divergence": te.get("rsi_divergence", "none"),
            "macd_signal": te.get("macd_signal", "N/A"),
            "macd_histogram": te.get("macd_histogram", "N/A"),
            "sma_20": te.get("sma_20", "N/A"),
            "sma_50": te.get("sma_50", "N/A"),
            "sma_200": te.get("sma_200", "N/A"),
            "ema_12": te.get("ema_12", "N/A"),
            "ema_26": te.get("ema_26", "N/A"),
            "atr": te.get("atr", "N/A"),
            "bollinger_lower": te.get("bollinger_lower", "N/A"),
            "bollinger_upper": te.get("bollinger_upper", "N/A"),
            "keltner_squeeze": te.get("keltner_squeeze", "N/A"),
            "obv": te.get("obv", "N/A"),
            "vwap": te.get("vwap", "N/A"),
            "cvd": te.get("cvd", "N/A"),
            "pivot_point": te.get("pivot_point", "N/A"),
            "support_1": te.get("support_1", "N/A"),
            "resistance_1": te.get("resistance_1", "N/A"),
            "trend_strength": te.get("trend_strength_score", "N/A"),
            "momentum_exhaustion": te.get("momentum_exhaustion", "N/A"),
            "volatility_regime": te.get("volatility_regime", "N/A"),
            "mtf_confluence": te.get("mtf_confluence_score", "N/A"),
            # TradFi
            "dxy_price": tf.get("dxy_price", "N/A"),
            "dxy_change_24h": tf.get("dxy_change_24h", "N/A"),
            "vix_value": tf.get("vix_value", "N/A"),
            "vix_percentile_90d": tf.get("vix_percentile_90d", "N/A"),
            "sp500_price": tf.get("sp500_price", "N/A"),
            "sp500_change_24h": tf.get("sp500_change_24h", "N/A"),
            "us10y_yield": tf.get("us10y_yield", "N/A"),
            "us10y_change_24h": tf.get("us10y_change_24h", "N/A"),
            "gold_price": tf.get("gold_price", "N/A"),
            "gold_change_24h": tf.get("gold_change_24h", "N/A"),
            "btc_spx_correlation_30d": tf.get("btc_spx_correlation_30d", "N/A"),
            "macro_risk_score": tf.get("macro_risk_score", "N/A"),
            # DeFi
            "total_tvl": df.get("total_tvl", "N/A"),
            "tvl_change_7d_pct": df.get("tvl_change_7d_pct", "N/A"),
            "stablecoin_total_supply": df.get("stablecoin_total_supply", "N/A"),
            "stablecoin_supply_change_7d": df.get("stablecoin_supply_change_7d", "N/A"),
            "stablecoin_mint_rate": df.get("stablecoin_mint_rate", "N/A"),
            "dex_cex_ratio": df.get("dex_cex_ratio", "N/A"),
            "liquidity_pulse_score": df.get("liquidity_pulse_score", "N/A"),
            # Options
            "btc_dvol": op.get("btc_dvol", "N/A"),
            "eth_dvol": op.get("eth_dvol", "N/A"),
            "dvol_percentile_90d": op.get("dvol_percentile_90d", "N/A"),
            "btc_max_pain": op.get("btc_max_pain", "N/A"),
            "btc_max_pain_distance_pct": op.get("btc_max_pain_distance_pct", "N/A"),
            "next_expiry_date": op.get("next_expiry_date", "N/A"),
            "btc_put_call_ratio": op.get("btc_put_call_ratio", "N/A"),
            "eth_put_call_ratio": op.get("eth_put_call_ratio", "N/A"),
            "vol_term_structure": op.get("vol_term_structure", "N/A"),
            # Market Breadth
            "market_breadth_above_sma50_pct": mk.get("market_breadth_above_sma50_pct", "N/A"),
            "market_breadth_above_sma200_pct": mk.get("market_breadth_above_sma200_pct", "N/A"),
            # ETF
            "etf_net_flow_usd": se.get("etf_net_flow_usd", "N/A"),
            "etf_flow_summary": se.get("etf_flow_summary", "N/A"),
            # Liquidation levels
            "liq_long_10x": liq_10x.get("long", "N/A") if isinstance(liq_10x, dict) else "N/A",
            "liq_long_25x": liq_25x.get("long", "N/A") if isinstance(liq_25x, dict) else "N/A",
            "liq_short_10x": liq_10x.get("short", "N/A") if isinstance(liq_10x, dict) else "N/A",
            "liq_short_25x": liq_25x.get("short", "N/A") if isinstance(liq_25x, dict) else "N/A",
            # Sentiment
            "sentiment_score": se.get("sentiment_score", "N/A"),
            "sentiment_label": se.get("sentiment_label", "N/A"),
            "sentiment_divergence_score": se.get("sentiment_divergence_score", "N/A"),
            "sentiment_summary": se.get("summary", "N/A"),
            # Whale
            "whale_flow_index": wh.get("whale_flow_index", "N/A"),
            "whale_net_flow_usd": wh.get("net_flow_usd", "N/A"),
            "whale_inflow_usd": wh.get("total_inflow_usd", "N/A"),
            "whale_outflow_usd": wh.get("total_outflow_usd", "N/A"),
            "significant_movements": wh.get("significant_movements", "N/A"),
        }

        prompt = ANALYSIS_TEMPLATE
        for key, val in replacements.items():
            prompt = prompt.replace(f"{{{key}}}", str(val))
        return prompt

    def _get_system_prompt(self, agent_num: int) -> str:
        return SYSTEM_PROMPTS.get(agent_num, "You are a crypto trading analyst.")

    # ──────────────────── Agent Calls ──────────────────────────────

    async def _call_agent(
        self, session: aiohttp.ClientSession, agent_num: int, user_prompt: str
    ) -> dict:
        model = AGENT_MODELS[agent_num]
        system_prompt = self._get_system_prompt(agent_num)
        name = AGENT_NAMES[agent_num]

        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.3 if agent_num != 3 else 0.5,
            "max_tokens": 4096,
        }

        result = {
            "agent_num": agent_num,
            "name": name,
            "model": model,
            "response_text": "",
            "market_impact": "neutral",
            "confidence": 0.0,
            "confidence_calibrated": 0.0,
            "trades": [],
            "contrarian_risk": None,
        }

        try:
            async with session.post(
                OPENROUTER_URL, json=payload, headers=HEADERS, timeout=aiohttp.ClientTimeout(total=120)
            ) as resp:
                if resp.status != 200:
                    err = await resp.text()
                    logger.error("Agent %d (%s) API error %d: %s", agent_num, name, resp.status, err[:300])
                    return result

                data = await resp.json()
                content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                result["response_text"] = content

                parsed = self._extract_json(content)
                if parsed:
                    result["market_impact"] = parsed.get("market_impact", "neutral")
                    raw_conf = float(parsed.get("confidence", 0.5))
                    result["confidence"] = max(0.0, min(1.0, raw_conf))
                    result["confidence_calibrated"] = result["confidence"] * self.calibration_factors.get(agent_num, 1.0)
                    result["trades"] = parsed.get("trades", [])
                    if agent_num == 3:
                        result["contrarian_risk"] = parsed.get("contrarian_risk", parsed.get("reasoning", ""))
                else:
                    logger.warning("Agent %d: could not parse JSON from response", agent_num)

        except asyncio.TimeoutError:
            logger.error("Agent %d (%s) timed out", agent_num, name)
        except Exception:
            logger.exception("Agent %d (%s) call failed", agent_num, name)

        return result

    # ──────────────────── Main Analysis ────────────────────────────

    async def analyze(
        self,
        event_data: dict | None = None,
        market_data: dict | None = None,
        technical_data: dict | None = None,
        tradfi_data: dict | None = None,
        defi_data: dict | None = None,
        options_data: dict | None = None,
        sentiment_data: dict | None = None,
        whale_data: dict | None = None,
        regime_data: dict | None = None,
    ) -> dict:
        prompt = self.build_analysis_prompt(
            event_data, market_data, technical_data, tradfi_data,
            defi_data, options_data, sentiment_data, whale_data, regime_data
        )

        async with aiohttp.ClientSession() as session:
            # Call all 3 agents in parallel
            tasks = [self._call_agent(session, i, prompt) for i in (1, 2, 3)]
            agent_results = await asyncio.gather(*tasks, return_exceptions=True)

        # Handle exceptions from gather
        clean_results = []
        for i, r in enumerate(agent_results, 1):
            if isinstance(r, Exception):
                logger.error("Agent %d raised exception: %s", i, r)
                clean_results.append({
                    "agent_num": i, "name": AGENT_NAMES[i], "model": AGENT_MODELS[i],
                    "response_text": f"Error: {r}", "market_impact": "neutral",
                    "confidence": 0.0, "confidence_calibrated": 0.0, "trades": [],
                    "contrarian_risk": None,
                })
            else:
                clean_results.append(r)

        # Consensus vote
        vote = self._vote_consensus(clean_results)

        # Synthesis
        synthesis = await self._generate_synthesis(session=None, agent_results=clean_results, vote_result=vote)

        return {
            "agents": clean_results,
            "vote": vote,
            "synthesis": synthesis,
            "prompt_length": len(prompt),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    # ──────────────────── Consensus Voting ─────────────────────────

    def _vote_consensus(self, agent_results: list[dict]) -> dict:
        impacts = [r.get("market_impact", "neutral") for r in agent_results]
        confidences = [r.get("confidence", 0.0) for r in agent_results]
        calibrated = [r.get("confidence_calibrated", 0.0) for r in agent_results]

        bullish_count = impacts.count("bullish")
        bearish_count = impacts.count("bearish")
        neutral_count = impacts.count("neutral")

        result = {
            "vote_result": "no_consensus",
            "consensus_direction": "neutral",
            "consensus_confidence_avg": sum(confidences) / max(len(confidences), 1),
            "consensus_calibrated_avg": sum(calibrated) / max(len(calibrated), 1),
            "size_multiplier": 0.0,
            "contrarian_warning": None,
            "votes": {"bullish": bullish_count, "bearish": bearish_count, "neutral": neutral_count},
        }

        # Unanimous (3/3)
        if bullish_count == 3 or bearish_count == 3:
            direction = "bullish" if bullish_count == 3 else "bearish"
            avg_conf = sum(confidences) / 3
            avg_cal = sum(calibrated) / 3
            if avg_conf >= config.MIN_CONFIDENCE_AVG:
                result["vote_result"] = "unanimous"
                result["consensus_direction"] = direction
                result["consensus_confidence_avg"] = avg_conf
                result["consensus_calibrated_avg"] = avg_cal
                result["size_multiplier"] = 1.0
                return result

        # Majority (2/3)
        if bullish_count >= 2 or bearish_count >= 2:
            direction = "bullish" if bullish_count >= 2 else "bearish"
            agreeing = [r for r in agent_results if r.get("market_impact") == direction]
            avg_conf = sum(r["confidence"] for r in agreeing) / len(agreeing)
            avg_cal = sum(r["confidence_calibrated"] for r in agreeing) / len(agreeing)

            if avg_conf >= 0.65:
                result["vote_result"] = "majority"
                result["consensus_direction"] = direction
                result["consensus_confidence_avg"] = avg_conf
                result["consensus_calibrated_avg"] = avg_cal
                result["size_multiplier"] = 0.7

                # Check if Agent 3 (Contrarian) is the dissenter with a specific risk
                dissenter = next((r for r in agent_results if r.get("market_impact") != direction), None)
                if dissenter and dissenter.get("agent_num") == 3:
                    risk = dissenter.get("contrarian_risk", "")
                    if risk and len(risk) > 20:
                        result["size_multiplier"] *= 0.8
                        result["contrarian_warning"] = risk

                return result

        return result

    # ──────────────────── Synthesis ─────────────────────────────────

    async def _generate_synthesis(self, session, agent_results: list[dict], vote_result: dict) -> str:
        try:
            prompt = SYNTHESIS_TEMPLATE
            for i, agent in enumerate(agent_results, 1):
                prompt = prompt.replace(f"{{agent_{i}_model}}", agent.get("model", "unknown"))
                prompt = prompt.replace(f"{{agent_{i}_impact}}", agent.get("market_impact", "N/A"))
                prompt = prompt.replace(f"{{agent_{i}_confidence}}", str(agent.get("confidence", 0)))
                prompt = prompt.replace(f"{{agent_{i}_response}}", agent.get("response_text", "N/A")[:1000])
            prompt = prompt.replace("{agent_3_contrarian_risk}", agent_results[2].get("contrarian_risk") or "None")
            prompt = prompt.replace("{vote_result}", vote_result.get("vote_result", "N/A"))
            prompt = prompt.replace("{consensus_direction}", vote_result.get("consensus_direction", "N/A"))
            prompt = prompt.replace("{consensus_confidence_avg}", str(vote_result.get("consensus_confidence_avg", 0)))

            payload = {
                "model": config.MODEL_LIGHT,
                "messages": [
                    {"role": "system", "content": "You are a financial analyst synthesizer. Summarize the multi-agent analysis concisely."},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.3,
                "max_tokens": 1024,
            }

            use_session = session
            close_session = False
            if use_session is None:
                use_session = aiohttp.ClientSession()
                close_session = True

            try:
                async with use_session.post(
                    OPENROUTER_URL, json=payload, headers=HEADERS, timeout=aiohttp.ClientTimeout(total=60)
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return data.get("choices", [{}])[0].get("message", {}).get("content", "Synthesis unavailable.")
                    return "Synthesis generation failed."
            finally:
                if close_session:
                    await use_session.close()

        except Exception:
            logger.exception("Synthesis generation failed")
            return "Synthesis unavailable due to error."

    # ──────────────────── Calibration ──────────────────────────────

    def update_calibration(self, agent_num: int, predicted_confidence: float, actual_win: bool):
        self.calibration_history[agent_num].append({
            "predicted": predicted_confidence,
            "actual": 1.0 if actual_win else 0.0,
        })
        history = self.calibration_history[agent_num]
        if len(history) >= 30:
            avg_predicted = sum(h["predicted"] for h in history) / len(history)
            actual_winrate = sum(h["actual"] for h in history) / len(history)
            if avg_predicted > 0:
                factor = actual_winrate / avg_predicted
                self.calibration_factors[agent_num] = max(0.5, min(1.5, factor))
                logger.info(
                    "Agent %d calibration updated: predicted=%.2f, actual=%.2f, factor=%.3f",
                    agent_num, avg_predicted, actual_winrate, self.calibration_factors[agent_num],
                )

    # ──────────────────── JSON Extraction ──────────────────────────

    @staticmethod
    def _extract_json(text: str) -> dict | None:
        if not text:
            return None
        # Try to find JSON in markdown code blocks
        patterns = [
            r"```json\s*(.*?)\s*```",
            r"```\s*(.*?)\s*```",
            r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}",
        ]
        for pattern in patterns:
            matches = re.findall(pattern, text, re.DOTALL)
            for match in matches:
                try:
                    obj = json.loads(match)
                    if isinstance(obj, dict):
                        return obj
                except (json.JSONDecodeError, TypeError):
                    continue
        # Last resort: try parsing the entire text
        try:
            obj = json.loads(text)
            if isinstance(obj, dict):
                return obj
        except (json.JSONDecodeError, TypeError):
            pass
        return None

    # ──────────────────── Serialization ────────────────────────────

    def to_dict(
        self,
        event_id: str | None,
        regime_id: str | None,
        agent_results: list[dict],
        vote_result: dict,
        synthesis: str,
    ) -> dict:
        agents = {r["agent_num"]: r for r in agent_results}
        a1 = agents.get(1, {})
        a2 = agents.get(2, {})
        a3 = agents.get(3, {})

        approved = []
        rejected_reasons = []
        proposed = []
        for a in agent_results:
            for t in a.get("trades", []):
                proposed.append(t)

        if vote_result.get("vote_result") != "no_consensus":
            direction = vote_result.get("consensus_direction")
            for t in proposed:
                if t.get("direction", "").lower() in (direction, direction[:4]):
                    approved.append(t)
                else:
                    rejected_reasons.append({"trade": t, "reason": "Against consensus direction"})
        else:
            rejected_reasons = [{"trade": t, "reason": "No consensus reached"} for t in proposed]

        return {
            "event_id": event_id,
            "regime_id": regime_id,
            "agent_1_model": a1.get("model"),
            "agent_1_response": a1.get("response_text", "")[:5000],
            "agent_1_impact": a1.get("market_impact"),
            "agent_1_confidence": a1.get("confidence"),
            "agent_1_confidence_calibrated": a1.get("confidence_calibrated"),
            "agent_2_model": a2.get("model"),
            "agent_2_response": a2.get("response_text", "")[:5000],
            "agent_2_impact": a2.get("market_impact"),
            "agent_2_confidence": a2.get("confidence"),
            "agent_2_confidence_calibrated": a2.get("confidence_calibrated"),
            "agent_3_model": a3.get("model"),
            "agent_3_response": a3.get("response_text", "")[:5000],
            "agent_3_impact": a3.get("market_impact"),
            "agent_3_confidence": a3.get("confidence"),
            "agent_3_contrarian_risk": a3.get("contrarian_risk"),
            "vote_result": vote_result.get("vote_result"),
            "consensus_direction": vote_result.get("consensus_direction"),
            "consensus_confidence_avg": vote_result.get("consensus_confidence_avg"),
            "consensus_calibrated_avg": vote_result.get("consensus_calibrated_avg"),
            "final_synthesis": synthesis,
            "trades_proposed": json.dumps(proposed),
            "trades_approved": json.dumps(approved),
            "trades_rejected_reasons": json.dumps(rejected_reasons),
            "correlation_check": json.dumps(vote_result.get("votes", {})),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    brain = AIBrain()
    prompt = brain.build_analysis_prompt(
        event_data={"event_name": "CPI", "actual": 3.2, "forecast": 3.3},
        market_data={"price": 65000, "symbol": "BTC/USDT"},
    )
    print(f"Prompt length: {len(prompt)} chars")
