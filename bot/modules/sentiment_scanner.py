"""
Macro Pulse — Couche 7 : Sentiment Scanner.

Analyses crypto sentiment via Sonar (OpenRouter), LunarCrush public API,
and ETF flow tracking.  Produces a unified sentiment snapshot compatible
with the ``sentiment_snapshots`` Supabase table.
"""

import sys
import os
import re
import json
import logging
import time
from datetime import datetime, timezone

import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

logger = logging.getLogger(__name__)

# ──────────────────────────── Constants ──────────────────────────────
OPENROUTER_CHAT_URL = "https://openrouter.ai/api/v1/chat/completions"
LUNARCRUSH_BITCOIN_URL = "https://lunarcrush.com/api4/public/topic/bitcoin"

# Minimum interval between consecutive OpenRouter calls (seconds)
_OPENROUTER_MIN_INTERVAL = 0.5  # ≤ 2 requests/second


class SentimentScanner:
    """Fetches and synthesises sentiment data from multiple sources."""

    def __init__(self):
        self._openrouter_headers = {
            "Authorization": f"Bearer {config.OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
        }
        self._last_openrouter_call: float = 0.0
        logger.info("SentimentScanner initialised.")

    # ================================================================
    #  Rate-limiter helper
    # ================================================================

    def _rate_limit_openrouter(self) -> None:
        """Block until at least ``_OPENROUTER_MIN_INTERVAL`` seconds have
        elapsed since the last OpenRouter request."""
        elapsed = time.monotonic() - self._last_openrouter_call
        if elapsed < _OPENROUTER_MIN_INTERVAL:
            wait = _OPENROUTER_MIN_INTERVAL - elapsed
            logger.debug("Rate-limiting OpenRouter — sleeping %.3fs", wait)
            time.sleep(wait)
        self._last_openrouter_call = time.monotonic()

    # ================================================================
    #  Generic OpenRouter chat helper
    # ================================================================

    def _openrouter_chat(self, model: str, prompt: str, max_tokens: int = 1024) -> str:
        """Send a single-turn chat completion to OpenRouter and return the
        assistant content string.  Returns an empty string on failure."""
        self._rate_limit_openrouter()

        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": 0.3,
        }

        try:
            resp = requests.post(
                OPENROUTER_CHAT_URL,
                headers=self._openrouter_headers,
                json=payload,
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
            content = (
                data.get("choices", [{}])[0]
                .get("message", {})
                .get("content", "")
            )
            return content.strip()
        except requests.RequestException as exc:
            logger.error("OpenRouter request failed (model=%s): %s", model, exc)
            return ""
        except (KeyError, IndexError, TypeError) as exc:
            logger.error("Unexpected OpenRouter response structure: %s", exc)
            return ""

    # ================================================================
    #  1. Sonar sentiment
    # ================================================================

    def fetch_sonar_sentiment(self) -> str:
        """Query Sonar (Perplexity via OpenRouter) for a qualitative
        sentiment summary of the last 24 hours.

        Returns
        -------
        str  — narrative summary text, or empty string on failure.
        """
        prompt = (
            "What is the current market sentiment for Bitcoin and crypto? "
            "Summarize the key narratives, major news, and overall market mood "
            "in the last 24 hours. Be specific about bullish and bearish factors."
        )

        try:
            summary = self._openrouter_chat(config.MODEL_SEARCH, prompt, max_tokens=1024)
            if summary:
                logger.info(
                    "Sonar sentiment fetched — %d chars", len(summary)
                )
            else:
                logger.warning("Sonar sentiment returned empty response.")
            return summary
        except Exception as exc:
            logger.error("fetch_sonar_sentiment error: %s", exc)
            return ""

    # ================================================================
    #  2. ETF flows
    # ================================================================

    def fetch_etf_flows(self) -> tuple[str, float | None]:
        """Query Sonar for the latest Bitcoin spot ETF flow data.

        Returns
        -------
        tuple[str, float | None]
            (etf_flow_summary, etf_net_flow_usd_millions)
            The numeric value is in *millions* USD, or ``None`` if parsing
            failed.
        """
        prompt = (
            "What were today's Bitcoin spot ETF net flows in USD? "
            "Include individual ETF data for IBIT, FBTC, ARKB, GBTC. "
            "If today's data is not yet available, provide the most "
            "recent day's data."
        )

        try:
            summary = self._openrouter_chat(config.MODEL_SEARCH, prompt, max_tokens=1024)
            if not summary:
                logger.warning("ETF flows — empty response from Sonar.")
                return "", None

            logger.info("ETF flow summary fetched — %d chars", len(summary))

            net_flow_usd = self._parse_etf_net_flow(summary)
            return summary, net_flow_usd

        except Exception as exc:
            logger.error("fetch_etf_flows error: %s", exc)
            return "", None

    @staticmethod
    def _parse_etf_net_flow(text: str) -> float | None:
        """Extract the aggregate net flow USD figure from free-form text.

        Recognises patterns such as:
            $500M, $1.2B, -$340 million, +$2.1 billion, $50.3m, etc.

        Returns the value in *millions* USD (e.g. $1.2B -> 1200.0).
        If multiple values are found, the first one following keywords
        like 'net' or 'total' is preferred; otherwise the first match
        is used.
        """
        if not text:
            return None

        # Pattern: optional sign, $, digits with optional decimal, unit suffix
        pattern = r'([+-]?)\s*\$\s*([\d,]+(?:\.\d+)?)\s*(billion|bill|B|million|mill|M)\b'
        matches = re.findall(pattern, text, re.IGNORECASE)

        if not matches:
            # Fallback: try "X million/billion" without $ sign
            pattern_alt = r'([+-]?)\s*([\d,]+(?:\.\d+)?)\s*(billion|bill|B|million|mill|M)\s*(?:USD|dollars?)?'
            matches = re.findall(pattern_alt, text, re.IGNORECASE)

        if not matches:
            logger.debug("Could not parse numeric ETF net flow from text.")
            return None

        # Prefer the match closest to keywords "net" or "total"
        best_match = matches[0]
        text_lower = text.lower()
        for keyword in ("net flow", "total net", "net inflow", "net outflow", "total flow"):
            idx = text_lower.find(keyword)
            if idx != -1:
                # Find the first pattern match *after* this keyword
                segment = text[idx:]
                local = re.findall(pattern, segment, re.IGNORECASE)
                if not local:
                    local = re.findall(
                        r'([+-]?)\s*\$?\s*([\d,]+(?:\.\d+)?)\s*(billion|bill|B|million|mill|M)',
                        segment,
                        re.IGNORECASE,
                    )
                if local:
                    best_match = local[0]
                    break

        sign_str, number_str, unit_str = best_match
        try:
            number = float(number_str.replace(",", ""))
        except ValueError:
            return None

        unit = unit_str.strip().lower()
        if unit in ("b", "billion", "bill"):
            number *= 1000  # convert to millions
        # 'm', 'million', 'mill' are already in millions

        if sign_str.strip() == "-":
            number = -number

        return round(number, 2)

    # ================================================================
    #  3. LunarCrush sentiment
    # ================================================================

    def fetch_lunarcrush_sentiment(self) -> dict:
        """Fetch Bitcoin social sentiment metrics from the LunarCrush
        public API (no auth required).

        Returns
        -------
        dict with keys:
            sentiment_score, social_volume, social_dominance,
            bullish_posts, bearish_posts
        All values default to ``None`` on failure.
        """
        result = {
            "sentiment_score": None,
            "social_volume": None,
            "social_dominance": None,
            "bullish_posts": None,
            "bearish_posts": None,
        }

        try:
            resp = requests.get(LUNARCRUSH_BITCOIN_URL, timeout=15)
            resp.raise_for_status()
            data = resp.json()

            # The LunarCrush v4 public endpoint returns a nested structure.
            # Adapt to the actual schema; common paths:
            topic_data = data if isinstance(data, dict) else {}

            # Try top-level keys first, then nested 'data' object
            source = topic_data.get("data", topic_data)
            if isinstance(source, list) and source:
                source = source[0]

            result["sentiment_score"] = (
                source.get("sentiment")
                or source.get("sentiment_score")
                or source.get("average_sentiment")
            )
            result["social_volume"] = (
                source.get("social_volume")
                or source.get("num_posts")
                or source.get("posts_count")
            )
            result["social_dominance"] = (
                source.get("social_dominance")
                or source.get("dominance")
            )
            result["bullish_posts"] = (
                source.get("bullish_posts")
                or source.get("types_sentiment", {}).get("bullish")
                if isinstance(source.get("types_sentiment"), dict)
                else source.get("bullish_posts")
            )
            result["bearish_posts"] = (
                source.get("bearish_posts")
                or source.get("types_sentiment", {}).get("bearish")
                if isinstance(source.get("types_sentiment"), dict)
                else source.get("bearish_posts")
            )

            logger.info(
                "LunarCrush sentiment — score=%s, volume=%s, dominance=%s",
                result["sentiment_score"],
                result["social_volume"],
                result["social_dominance"],
            )

        except requests.RequestException as exc:
            logger.error("LunarCrush request failed: %s", exc)
        except (ValueError, KeyError, TypeError) as exc:
            logger.error("LunarCrush response parsing error: %s", exc)
        except Exception as exc:
            logger.error("Unexpected error in fetch_lunarcrush_sentiment: %s", exc)

        return result

    # ================================================================
    #  4. Classify sentiment
    # ================================================================

    def classify_sentiment(self, summary_text: str) -> dict:
        """Ask a lightweight LLM to classify sentiment from a narrative
        summary into a structured score + label + key factors.

        Returns
        -------
        dict with keys: score (float -1..1), label (str), key_factors (list[str])
        """
        default = {"score": 0.0, "label": "neutral", "key_factors": []}

        if not summary_text:
            return default

        prompt = (
            "Given the following market summary, classify the overall crypto "
            "sentiment as a JSON object with exactly these fields:\n"
            '{"score": <float from -1 to 1>, '
            '"label": "<very_bearish|bearish|neutral|bullish|very_bullish>", '
            '"key_factors": ["factor1", "factor2", ...]}\n\n'
            "Return ONLY valid JSON, no commentary.\n\n"
            f"Market summary:\n{summary_text}"
        )

        try:
            raw = self._openrouter_chat(config.MODEL_LIGHT, prompt, max_tokens=512)
            if not raw:
                logger.warning("classify_sentiment — empty LLM response.")
                return default

            parsed = self._extract_json(raw)
            if parsed is None:
                logger.warning("classify_sentiment — could not parse JSON from response.")
                return default

            score = float(parsed.get("score", 0.0))
            score = max(-1.0, min(1.0, score))

            label = str(parsed.get("label", "neutral")).lower().strip()
            valid_labels = {"very_bearish", "bearish", "neutral", "bullish", "very_bullish"}
            if label not in valid_labels:
                label = "neutral"

            key_factors = parsed.get("key_factors", [])
            if not isinstance(key_factors, list):
                key_factors = []
            key_factors = [str(f) for f in key_factors]

            logger.info(
                "Sentiment classified — score=%.2f, label=%s, factors=%d",
                score,
                label,
                len(key_factors),
            )
            return {"score": score, "label": label, "key_factors": key_factors}

        except Exception as exc:
            logger.error("classify_sentiment error: %s", exc)
            return default

    @staticmethod
    def _extract_json(text: str) -> dict | None:
        """Best-effort extraction of the first JSON object from *text*.

        Handles cases where the model wraps JSON in markdown code fences
        or adds commentary around it.
        """
        # Strip markdown code fences if present
        cleaned = re.sub(r"```(?:json)?\s*", "", text)
        cleaned = cleaned.strip().rstrip("`")

        # Try direct parse first
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            pass

        # Try to find a JSON object substring
        match = re.search(r'\{[^{}]*\}', cleaned, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass

        # Try matching nested braces
        brace_depth = 0
        start = None
        for i, ch in enumerate(cleaned):
            if ch == '{':
                if brace_depth == 0:
                    start = i
                brace_depth += 1
            elif ch == '}':
                brace_depth -= 1
                if brace_depth == 0 and start is not None:
                    try:
                        return json.loads(cleaned[start:i + 1])
                    except json.JSONDecodeError:
                        start = None

        return None

    # ================================================================
    #  5. Sentiment divergence
    # ================================================================

    @staticmethod
    def calculate_sentiment_divergence(
        sentiment_score: float,
        price_change_24h: float,
    ) -> float:
        """Detect divergence between social/narrative sentiment and price
        action.  Divergences are treated as *contrarian* signals.

        Parameters
        ----------
        sentiment_score : float
            Sentiment score in [-1, 1].
        price_change_24h : float
            24-hour price change in percent (e.g. -3.5 means -3.5 %).

        Returns
        -------
        float in [-1, 1]
            - Positive → bullish divergence (sentiment bearish, price rising)
            - Negative → bearish divergence (sentiment bullish, price falling)
            - Near zero → no meaningful divergence
        """
        divergence = 0.0

        # Bullish divergence: sentiment bearish but price rising
        if sentiment_score < -0.3 and price_change_24h > 2.0:
            # Strength proportional to how extreme the mismatch is
            sent_strength = min(abs(sentiment_score), 1.0)
            price_strength = min(price_change_24h / 10.0, 1.0)
            divergence = (sent_strength + price_strength) / 2.0

        # Bearish divergence: sentiment bullish but price falling
        elif sentiment_score > 0.3 and price_change_24h < -2.0:
            sent_strength = min(abs(sentiment_score), 1.0)
            price_strength = min(abs(price_change_24h) / 10.0, 1.0)
            divergence = -((sent_strength + price_strength) / 2.0)

        # Clamp to [-1, 1]
        divergence = max(-1.0, min(1.0, divergence))

        logger.info(
            "Sentiment divergence — sent=%.2f, price_chg=%.2f%% -> divergence=%.3f",
            sentiment_score,
            price_change_24h,
            divergence,
        )
        return round(divergence, 4)

    # ================================================================
    #  6. Main aggregator
    # ================================================================

    def fetch_all(self, price_change_24h: float = 0.0) -> dict:
        """Run the complete sentiment pipeline and return a dict matching
        the ``sentiment_snapshots`` Supabase table schema.

        Parameters
        ----------
        price_change_24h : float
            24-hour BTC price change in percent, used for divergence
            calculation.

        Returns
        -------
        dict with keys: source, summary, sentiment_score, sentiment_label,
            sentiment_divergence_score, etf_flow_summary, etf_net_flow_usd,
            lunarcrush_data, timestamp
        """
        logger.info("fetch_all — starting full sentiment scan")

        # 1. Sonar narrative summary
        sonar_summary = self.fetch_sonar_sentiment()

        # 2. ETF flows
        etf_summary, etf_net_flow = self.fetch_etf_flows()

        # 3. LunarCrush social metrics
        lunar = self.fetch_lunarcrush_sentiment()

        # 4. Classify sentiment from the Sonar summary
        classification = self.classify_sentiment(sonar_summary)

        # 5. Calculate divergence
        sentiment_score = classification["score"]
        divergence = self.calculate_sentiment_divergence(
            sentiment_score, price_change_24h
        )

        # Build combined summary text
        combined_summary = sonar_summary
        if lunar.get("sentiment_score") is not None:
            combined_summary += (
                f"\n\n[LunarCrush] Social sentiment score: {lunar['sentiment_score']}, "
                f"social volume: {lunar.get('social_volume')}, "
                f"dominance: {lunar.get('social_dominance')}"
            )

        record = {
            "source": "sonar+lunarcrush+etf",
            "summary": combined_summary,
            "sentiment_score": sentiment_score,
            "sentiment_label": classification["label"],
            "sentiment_divergence_score": divergence,
            "etf_flow_summary": etf_summary,
            "etf_net_flow_usd": etf_net_flow,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        logger.info(
            "fetch_all — complete: score=%.2f, label=%s, divergence=%.3f, "
            "etf_flow=%s M USD",
            record["sentiment_score"],
            record["sentiment_label"],
            record["sentiment_divergence_score"],
            record["etf_net_flow_usd"],
        )
        return record


# ──────────────────────────── CLI quick-test ─────────────────────────────
if __name__ == "__main__":
    logging.basicConfig(
        level=getattr(logging, config.LOG_LEVEL, logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    )
    scanner = SentimentScanner()

    print("\n=== Sonar Sentiment ===")
    sonar = scanner.fetch_sonar_sentiment()
    print(f"  {sonar[:200]}..." if len(sonar) > 200 else f"  {sonar}")

    print("\n=== ETF Flows ===")
    etf_text, etf_usd = scanner.fetch_etf_flows()
    print(f"  Net flow: {etf_usd} M USD")
    print(f"  Summary: {etf_text[:200]}..." if len(etf_text) > 200 else f"  Summary: {etf_text}")

    print("\n=== LunarCrush ===")
    lc = scanner.fetch_lunarcrush_sentiment()
    for k, v in lc.items():
        print(f"  {k}: {v}")

    print("\n=== Classify Sentiment ===")
    if sonar:
        cls = scanner.classify_sentiment(sonar)
        for k, v in cls.items():
            print(f"  {k}: {v}")
    else:
        print("  (skipped — no sonar summary)")

    print("\n=== Divergence (example) ===")
    div = scanner.calculate_sentiment_divergence(0.6, -4.0)
    print(f"  bullish sent + falling price -> divergence: {div}")

    print("\n=== Full Scan (fetch_all) ===")
    full = scanner.fetch_all(price_change_24h=-1.5)
    for k, v in full.items():
        if isinstance(v, str) and len(v) > 120:
            print(f"  {k}: {v[:120]}...")
        else:
            print(f"  {k}: {v}")
