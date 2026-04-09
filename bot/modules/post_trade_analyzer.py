"""
Macro Pulse -- Post-Trade Analyzer.

Auto-learning module that analyses completed trades via LLM and synthesises
recurring patterns once enough data has accumulated.  Uses the free
MODEL_LIGHT for individual trade reviews and the heavier AGENT_QUANT_MODEL
for periodic meta-analyses.
"""

import json
import logging
import sys
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import requests

# ---------------------------------------------------------------------------
# Config import -- works both as package import and standalone execution
# ---------------------------------------------------------------------------
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

logger = logging.getLogger(__name__)


class PostTradeAnalyzer:
    """Analyses completed trades and extracts actionable lessons."""

    # ------------------------------------------------------------------ init
    def __init__(self, data_store) -> None:
        self.data_store = data_store
        logger.info("PostTradeAnalyzer initialised")

    # =======================================================================
    #  Analyse a single completed trade
    # =======================================================================

    async def analyze_trade(self, trade: Dict[str, Any]) -> Dict[str, Any]:
        """Run an LLM analysis on a completed trade and persist the result.

        Parameters
        ----------
        trade : dict
            A completed trade dict containing at minimum:
            symbol, direction, entry_price, entry_time, exit_price, exit_time,
            pnl, pnl_pct, stop_loss, take_profit, close_reason, event_name,
            regime, agent_consensus.

        Returns
        -------
        dict   The parsed analysis (what_worked, what_failed, ...).
        """

        symbol = trade.get("symbol", "N/A")
        direction = trade.get("direction", "N/A")
        entry_price = trade.get("entry_price", "N/A")
        entry_time = trade.get("entry_time", "N/A")
        exit_price = trade.get("exit_price", "N/A")
        exit_time = trade.get("exit_time", "N/A")
        pnl = trade.get("pnl", 0)
        pnl_pct = trade.get("pnl_pct", 0)
        stop_loss = trade.get("stop_loss", "N/A")
        take_profit = trade.get("take_profit", "N/A")
        close_reason = trade.get("close_reason", "N/A")
        event_name = trade.get("event_name", "N/A")
        regime = trade.get("regime", "N/A")
        agent_consensus = trade.get("agent_consensus", "N/A")

        user_prompt = (
            f"Analyze this completed trade:\n"
            f"Symbol: {symbol}, Direction: {direction}\n"
            f"Entry: {entry_price} at {entry_time}\n"
            f"Exit: {exit_price} at {exit_time}\n"
            f"PnL: {pnl} ({pnl_pct}%)\n"
            f"Stop Loss: {stop_loss}, Take Profit: {take_profit}\n"
            f"Close Reason: {close_reason}\n"
            f"Event: {event_name}\n"
            f"Regime at entry: {regime}\n"
            f"Agent Consensus: {agent_consensus}\n"
            f"\n"
            f"Analyze: What worked? What failed? If you could redo with same "
            f"entry data, what would you change? Identify recurring patterns.\n"
            f"\n"
            f'Respond as JSON: {{"what_worked": "...", "what_failed": "...", '
            f'"alternative_action": "...", "recurring_pattern": "...", '
            f'"suggested_adjustments": {{"param": "value"}}}}'
        )

        system_prompt = (
            "You are a quantitative trading analyst specialising in crypto "
            "macro-event trading.  Respond ONLY with the requested JSON object, "
            "no markdown fences, no commentary."
        )

        # Call the free / light model
        raw_response = self._call_openrouter(
            model=config.MODEL_LIGHT,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
        )

        # ------------------------------------------------------------------
        # Parse the JSON response (with fallback)
        # ------------------------------------------------------------------
        analysis: Dict[str, Any] = self._parse_json_response(raw_response)

        # ------------------------------------------------------------------
        # Persist to Supabase via data_store
        # ------------------------------------------------------------------
        row = {
            "trade_id": trade.get("id"),
            "symbol": symbol,
            "direction": direction,
            "pnl": pnl,
            "pnl_pct": pnl_pct,
            "close_reason": close_reason,
            "what_worked": analysis.get("what_worked", ""),
            "what_failed": analysis.get("what_failed", ""),
            "alternative_action": analysis.get("alternative_action", ""),
            "recurring_pattern": analysis.get("recurring_pattern", ""),
            "suggested_adjustments": analysis.get("suggested_adjustments", {}),
            "raw_response": raw_response,
            "model_used": config.MODEL_LIGHT,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        try:
            self.data_store.insert_post_trade_analysis(row)
            logger.info(
                "Post-trade analysis saved for trade %s (%s %.2f%%)",
                trade.get("id", "?"),
                symbol,
                pnl_pct,
            )
        except Exception:
            logger.exception("Failed to persist post-trade analysis")

        return analysis

    # =======================================================================
    #  Meta-analysis: synthesise patterns across many trades
    # =======================================================================

    async def generate_meta_analysis(
        self,
        analyses: List[Dict[str, Any]],
        min_trades: int = 20,
    ) -> Dict[str, Any]:
        """Synthesise insights from *analyses* once we have enough data.

        Parameters
        ----------
        analyses : list[dict]
            A list of individual post-trade analysis dicts (as returned by
            ``analyze_trade`` or fetched from the database).
        min_trades : int
            Minimum number of analyses required before running the synthesis.

        Returns
        -------
        dict  ``{"synthesis": str, "suggested_adjustments": dict}``
              or an empty dict if there are not enough trades.
        """

        if len(analyses) < min_trades:
            logger.info(
                "Meta-analysis skipped: only %d analyses (need %d)",
                len(analyses),
                min_trades,
            )
            return {}

        # Build a compact summary of each analysis for the prompt
        summaries: List[str] = []
        for idx, a in enumerate(analyses, 1):
            summaries.append(
                f"#{idx}  symbol={a.get('symbol','?')}  pnl={a.get('pnl_pct','?')}%  "
                f"reason={a.get('close_reason','?')}  "
                f"worked={a.get('what_worked','?')}  "
                f"failed={a.get('what_failed','?')}  "
                f"pattern={a.get('recurring_pattern','?')}  "
                f"adjustments={json.dumps(a.get('suggested_adjustments', {}))}"
            )

        analyses_text = "\n".join(summaries)

        user_prompt = (
            f"Here are {len(analyses)} post-trade analyses from a crypto "
            f"macro-event trading bot:\n\n"
            f"{analyses_text}\n\n"
            f"Identify the top 3 recurring error patterns and suggest specific "
            f"parameter adjustments (ATR multipliers, confidence thresholds, "
            f"regime weights, stop-loss distances, take-profit ratios, etc.).\n\n"
            f"Respond as JSON:\n"
            f'{{"top_3_error_patterns": ["...", "...", "..."], '
            f'"suggested_adjustments": {{"param_name": "new_value", ...}}, '
            f'"synthesis": "2-3 sentence executive summary"}}'
        )

        system_prompt = (
            "You are a senior quantitative researcher reviewing a systematic "
            "crypto trading strategy.  Respond ONLY with the requested JSON "
            "object, no markdown fences, no commentary."
        )

        raw_response = self._call_openrouter(
            model=config.AGENT_QUANT_MODEL,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
        )

        result = self._parse_json_response(raw_response)

        logger.info(
            "Meta-analysis complete (%d analyses -> %d error patterns)",
            len(analyses),
            len(result.get("top_3_error_patterns", [])),
        )

        return {
            "synthesis": result.get("synthesis", raw_response),
            "suggested_adjustments": result.get("suggested_adjustments", {}),
            "top_3_error_patterns": result.get("top_3_error_patterns", []),
            "raw_response": raw_response,
            "model_used": config.AGENT_QUANT_MODEL,
            "analyses_count": len(analyses),
        }

    # =======================================================================
    #  OpenRouter API helper
    # =======================================================================

    def _call_openrouter(
        self,
        model: str,
        system_prompt: str,
        user_prompt: str,
    ) -> str:
        """Send a chat-completion request to OpenRouter and return the text.

        Uses synchronous ``requests`` for simplicity.  Returns the assistant
        content string or a descriptive error string on failure.
        """

        url = f"{config.OPENROUTER_BASE_URL}/chat/completions"

        headers = {
            "Authorization": f"Bearer {config.OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.3,
            "max_tokens": 2048,
        }

        try:
            response = requests.post(url, headers=headers, json=payload, timeout=60)
            response.raise_for_status()
            data = response.json()
            content = (
                data.get("choices", [{}])[0]
                .get("message", {})
                .get("content", "")
            )
            if not content:
                logger.warning("OpenRouter returned empty content for model %s", model)
                return ""
            return content.strip()

        except requests.exceptions.Timeout:
            logger.error("OpenRouter request timed out (model=%s)", model)
            return '{"error": "timeout"}'
        except requests.exceptions.HTTPError as exc:
            status = exc.response.status_code if exc.response is not None else "unknown"
            logger.error(
                "OpenRouter HTTP error %s (model=%s): %s",
                status,
                model,
                exc,
            )
            return f'{{"error": "http_{status}"}}'
        except Exception:
            logger.exception("Unexpected error calling OpenRouter (model=%s)", model)
            return '{"error": "unexpected"}'

    # =======================================================================
    #  JSON parsing helper
    # =======================================================================

    @staticmethod
    def _parse_json_response(raw: str) -> Dict[str, Any]:
        """Best-effort extraction of a JSON object from an LLM response.

        Handles common issues like markdown fences, leading/trailing text, etc.
        """

        text = raw.strip()

        # Strip markdown code fences if present
        if text.startswith("```"):
            # Remove opening fence (possibly ```json)
            first_newline = text.find("\n")
            if first_newline != -1:
                text = text[first_newline + 1:]
            # Remove closing fence
            if text.endswith("```"):
                text = text[:-3].strip()

        # Try direct parse first
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # Try to find the first { ... } block
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(text[start : end + 1])
            except json.JSONDecodeError:
                pass

        # Last resort -- return the raw text wrapped in a dict
        logger.warning("Could not parse JSON from LLM response; returning raw text")
        return {"raw": text}
