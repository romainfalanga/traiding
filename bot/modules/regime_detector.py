"""
Macro Pulse — Couche 9 : Regime Detector.

Probabilistic scoring engine that classifies the current market into one
of five regimes (EUPHORIA, OPTIMISM, NEUTRAL, FEAR, CAPITULATION) based
on nine input metrics.  Applies cooldown-gated transition logic so the
detected regime cannot flip-flop faster than once every four hours.

Produces a snapshot compatible with the ``regime_history`` Supabase table.
"""

import sys
import os
import logging
from datetime import datetime, timezone, timedelta

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

logger = logging.getLogger(__name__)

# ──────────────────────────── Constants ──────────────────────────────

REGIMES = ["EUPHORIA", "OPTIMISM", "NEUTRAL", "FEAR", "CAPITULATION"]

# Ordered index for adjacency calculations
_REGIME_INDEX = {regime: idx for idx, regime in enumerate(REGIMES)}

# Minimum hours between regime transitions
_COOLDOWN_HOURS = 4

# Confidence thresholds for transitions
_CONFIDENCE_SAME_OR_ADJACENT = 0.30
_CONFIDENCE_DEFAULT = 0.35
_CONFIDENCE_DISTANT = 0.45


class RegimeDetector:
    """Scores five market regimes from nine input metrics and manages
    cooldown-gated regime transitions."""

    def __init__(self) -> None:
        self._regime_history: list[dict] = []
        self._current_regime: str = "NEUTRAL"
        self._current_confidence: float = 0.0
        self._current_scores: dict[str, float] = {}
        self._current_transition_score: float = 0.0
        self._last_transition_time: datetime | None = None
        self._last_metrics: dict = {}
        logger.info("RegimeDetector initialised — default regime: NEUTRAL.")

    # ================================================================ #
    #  1. Main detection entry point                                   #
    # ================================================================ #

    def detect(self, metrics: dict) -> str:
        """Score every regime, normalise into probabilities, and apply
        transition logic to decide the current regime.

        Parameters
        ----------
        metrics : dict
            Must contain up to nine keys:
                fear_greed, funding_rate, volume_change_24h,
                price_momentum, whale_flow_index, trend_strength,
                macro_risk_score, liquidity_pulse_score,
                market_breadth_sma50_pct

            Missing keys are silently ignored (their scoring rules
            contribute zero).

        Returns
        -------
        str — one of EUPHORIA, OPTIMISM, NEUTRAL, FEAR, CAPITULATION.
        """
        self._last_metrics = dict(metrics)

        # --- Step 1: raw scoring ---
        raw_scores = {
            "EUPHORIA": self._score_euphoria(metrics),
            "OPTIMISM": self._score_optimism(metrics),
            "NEUTRAL": self._score_neutral(metrics),
            "FEAR": self._score_fear(metrics),
            "CAPITULATION": self._score_capitulation(metrics),
        }

        # --- Step 2: normalise to probability distribution ---
        total = sum(raw_scores.values())
        if total > 0:
            probabilities = {r: s / total for r, s in raw_scores.items()}
        else:
            # Fallback: uniform distribution
            probabilities = {r: 1.0 / len(REGIMES) for r in REGIMES}

        # --- Step 3: pick the highest-probability regime ---
        best_regime = max(probabilities, key=probabilities.get)  # type: ignore[arg-type]
        best_confidence = probabilities[best_regime]

        self._current_scores = probabilities

        # --- Step 4: apply transition logic ---
        now = datetime.now(timezone.utc)
        previous_regime = self._current_regime

        transition_allowed, transition_score = self._evaluate_transition(
            previous_regime, best_regime, best_confidence, now,
        )

        if transition_allowed:
            self._current_regime = best_regime
            self._current_confidence = best_confidence
            self._current_transition_score = transition_score
            self._last_transition_time = now

            # Record the transition in history
            self._regime_history.append({
                "regime": best_regime,
                "previous_regime": previous_regime,
                "confidence": round(best_confidence, 4),
                "transition_score": round(transition_score, 4),
                "scores": {k: round(v, 4) for k, v in probabilities.items()},
                "metrics": dict(metrics),
                "timestamp": now.isoformat(),
            })

            logger.info(
                "Regime transition: %s -> %s (confidence=%.3f, transition_score=%.3f)",
                previous_regime, best_regime, best_confidence, transition_score,
            )
        else:
            # Stay in current regime but update confidence and scores
            self._current_confidence = probabilities.get(self._current_regime, 0.0)
            self._current_transition_score = transition_score

            logger.debug(
                "Regime unchanged: %s (best candidate=%s conf=%.3f, "
                "transition blocked — score=%.3f)",
                self._current_regime, best_regime, best_confidence,
                transition_score,
            )

        return self._current_regime

    # ================================================================ #
    #  2. Regime scoring functions                                     #
    # ================================================================ #

    @staticmethod
    def _score_euphoria(m: dict) -> float:
        """Score for EUPHORIA — overheated market, potential top."""
        score = 0.0
        fg = m.get("fear_greed")
        if fg is not None and fg > 80:
            score += 25

        fr = m.get("funding_rate")
        if fr is not None and fr > 0.0005:
            score += 15

        vc = m.get("volume_change_24h")
        if vc is not None and vc > 50:
            score += 10

        pm = m.get("price_momentum")
        if pm is not None and pm > 5:
            score += 15

        wf = m.get("whale_flow_index")
        if wf is not None and wf < -0.3:
            score += 10

        ts = m.get("trend_strength")
        if ts is not None and ts > 70:
            score += 10

        mrs = m.get("macro_risk_score")
        if mrs is not None and mrs > 80:
            score += 5

        lps = m.get("liquidity_pulse_score")
        if lps is not None and lps > 70:
            score += 5

        mb = m.get("market_breadth_sma50_pct")
        if mb is not None and mb > 80:
            score += 5

        return score

    @staticmethod
    def _score_optimism(m: dict) -> float:
        """Score for OPTIMISM — healthy uptrend."""
        score = 0.0
        fg = m.get("fear_greed")
        if fg is not None and 55 <= fg <= 80:
            score += 20

        fr = m.get("funding_rate")
        if fr is not None and 0.0001 <= fr <= 0.0005:
            score += 15

        vc = m.get("volume_change_24h")
        if vc is not None and 10 <= vc <= 50:
            score += 10

        pm = m.get("price_momentum")
        if pm is not None and 1 <= pm <= 5:
            score += 15

        wf = m.get("whale_flow_index")
        if wf is not None and wf > 0.1:
            score += 15

        ts = m.get("trend_strength")
        if ts is not None and 50 <= ts <= 70:
            score += 10

        mrs = m.get("macro_risk_score")
        if mrs is not None and mrs > 60:
            score += 5

        lps = m.get("liquidity_pulse_score")
        if lps is not None and lps > 50:
            score += 5

        mb = m.get("market_breadth_sma50_pct")
        if mb is not None and 50 <= mb <= 80:
            score += 5

        return score

    @staticmethod
    def _score_neutral(m: dict) -> float:
        """Score for NEUTRAL — range-bound, indecisive market."""
        score = 0.0
        fg = m.get("fear_greed")
        if fg is not None and 40 <= fg <= 55:
            score += 20

        fr = m.get("funding_rate")
        if fr is not None and -0.0001 <= fr <= 0.0001:
            score += 15

        vc = m.get("volume_change_24h")
        if vc is not None and -10 <= vc <= 10:
            score += 15

        pm = m.get("price_momentum")
        if pm is not None and -1 <= pm <= 1:
            score += 20

        wf = m.get("whale_flow_index")
        if wf is not None and -0.1 <= wf <= 0.1:
            score += 10

        ts = m.get("trend_strength")
        if ts is not None and 30 <= ts <= 50:
            score += 10

        mrs = m.get("macro_risk_score")
        if mrs is not None and 40 <= mrs <= 60:
            score += 5

        lps = m.get("liquidity_pulse_score")
        if lps is not None and 40 <= lps <= 60:
            score += 5

        return score

    @staticmethod
    def _score_fear(m: dict) -> float:
        """Score for FEAR — declining market, risk-off sentiment."""
        score = 0.0
        fg = m.get("fear_greed")
        if fg is not None and 20 <= fg <= 40:
            score += 20

        fr = m.get("funding_rate")
        if fr is not None and -0.0005 <= fr <= -0.0001:
            score += 15

        vc = m.get("volume_change_24h")
        if vc is not None and vc < -10:
            score += 10

        pm = m.get("price_momentum")
        if pm is not None and -5 <= pm <= -1:
            score += 15

        wf = m.get("whale_flow_index")
        if wf is not None and wf < -0.1:
            score += 15

        ts = m.get("trend_strength")
        if ts is not None and ts < 30:
            score += 10

        mrs = m.get("macro_risk_score")
        if mrs is not None and mrs < 40:
            score += 5

        lps = m.get("liquidity_pulse_score")
        if lps is not None and lps < 40:
            score += 5

        mb = m.get("market_breadth_sma50_pct")
        if mb is not None and mb < 40:
            score += 5

        return score

    @staticmethod
    def _score_capitulation(m: dict) -> float:
        """Score for CAPITULATION — panic selling, potential bottom."""
        score = 0.0
        fg = m.get("fear_greed")
        if fg is not None and fg < 20:
            score += 25

        fr = m.get("funding_rate")
        if fr is not None and fr < -0.0005:
            score += 15

        vc = m.get("volume_change_24h")
        if vc is not None and vc > 80:
            score += 10

        pm = m.get("price_momentum")
        if pm is not None and pm < -5:
            score += 15

        wf = m.get("whale_flow_index")
        if wf is not None and wf < -0.5:
            score += 10

        ts = m.get("trend_strength")
        if ts is not None and ts < 20:
            score += 10

        mrs = m.get("macro_risk_score")
        if mrs is not None and mrs < 20:
            score += 5

        lps = m.get("liquidity_pulse_score")
        if lps is not None and lps < 30:
            score += 5

        mb = m.get("market_breadth_sma50_pct")
        if mb is not None and mb < 20:
            score += 5

        return score

    # ================================================================ #
    #  3. Transition logic                                             #
    # ================================================================ #

    def _evaluate_transition(
        self,
        current: str,
        candidate: str,
        candidate_confidence: float,
        now: datetime,
    ) -> tuple[bool, float]:
        """Decide whether a regime transition should occur.

        Returns
        -------
        tuple[bool, float]
            (transition_allowed, transition_score)
            transition_score is a 0-1 measure of how confident the
            transition is.
        """
        # Same regime — always allowed (no actual transition)
        if candidate == current:
            return True, candidate_confidence

        # Check cooldown
        if self._last_transition_time is not None:
            elapsed = now - self._last_transition_time
            if elapsed < timedelta(hours=_COOLDOWN_HOURS):
                remaining = timedelta(hours=_COOLDOWN_HOURS) - elapsed
                logger.debug(
                    "Cooldown active — %s remaining before next transition allowed.",
                    remaining,
                )
                return False, candidate_confidence

        # Distance between regimes in the ordered list
        distance = abs(_REGIME_INDEX[candidate] - _REGIME_INDEX[current])

        # Determine required confidence threshold
        if distance <= 1:
            # Adjacent regimes (e.g. OPTIMISM <-> NEUTRAL)
            required_confidence = _CONFIDENCE_SAME_OR_ADJACENT
        elif distance >= 2:
            # Distant jump (e.g. EUPHORIA -> FEAR)
            required_confidence = _CONFIDENCE_DISTANT
        else:
            required_confidence = _CONFIDENCE_DEFAULT

        # Calculate transition score: how strongly the evidence supports
        # moving away from the current regime.
        # Combines the candidate's probability with the deficit of the
        # current regime's probability.
        current_prob = self._current_scores.get(current, 0.0)
        gap = candidate_confidence - current_prob
        transition_score = np.clip(
            candidate_confidence * 0.7 + max(0.0, gap) * 0.3,
            0.0,
            1.0,
        )

        if candidate_confidence >= required_confidence:
            logger.debug(
                "Transition approved: %s -> %s (conf=%.3f >= req=%.3f, "
                "distance=%d, tscore=%.3f)",
                current, candidate, candidate_confidence,
                required_confidence, distance, transition_score,
            )
            return True, float(transition_score)

        logger.debug(
            "Transition denied: %s -> %s (conf=%.3f < req=%.3f, distance=%d)",
            current, candidate, candidate_confidence,
            required_confidence, distance,
        )
        return False, float(transition_score)

    # ================================================================ #
    #  4. Public accessors                                             #
    # ================================================================ #

    def get_current_regime(self) -> dict:
        """Return the current regime snapshot.

        Returns
        -------
        dict with keys:
            regime, confidence, transition_score, scores, timestamp
        """
        return {
            "regime": self._current_regime,
            "confidence": round(self._current_confidence, 4),
            "transition_score": round(self._current_transition_score, 4),
            "scores": {k: round(v, 4) for k, v in self._current_scores.items()},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def get_regime_history(self, n: int = 20) -> list[dict]:
        """Return the last *n* regime transitions.

        Parameters
        ----------
        n : int
            Maximum number of history entries to return (default 20).

        Returns
        -------
        list[dict] — most recent transitions, newest first.
        """
        return list(reversed(self._regime_history[-n:]))

    def to_dict(self) -> dict:
        """Return a dict matching the ``regime_history`` Supabase table
        schema, suitable for direct insertion.

        Returns
        -------
        dict with keys:
            regime, confidence, transition_score, fear_greed,
            funding_rate, volume_change, price_momentum, whale_flow,
            trend_strength, macro_risk_score, liquidity_pulse_score,
            market_breadth_sma50_pct, timestamp
        """
        m = self._last_metrics
        return {
            "regime": self._current_regime,
            "confidence": round(self._current_confidence, 4),
            "transition_score": round(self._current_transition_score, 4),
            "fear_greed": m.get("fear_greed"),
            "funding_rate": m.get("funding_rate"),
            "volume_change": m.get("volume_change_24h"),
            "price_momentum": m.get("price_momentum"),
            "whale_flow": m.get("whale_flow_index"),
            "trend_strength": m.get("trend_strength"),
            "macro_risk_score": m.get("macro_risk_score"),
            "liquidity_pulse_score": m.get("liquidity_pulse_score"),
            "market_breadth_sma50_pct": m.get("market_breadth_sma50_pct"),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


# ──────────────────────────── CLI quick-test ─────────────────────────────
if __name__ == "__main__":
    logging.basicConfig(
        level=getattr(logging, config.LOG_LEVEL, logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    )

    detector = RegimeDetector()

    # --- Test 1: Euphoria scenario ---
    print("\n=== Test 1: EUPHORIA scenario ===")
    euphoria_metrics = {
        "fear_greed": 88,
        "funding_rate": 0.0008,
        "volume_change_24h": 65,
        "price_momentum": 7.2,
        "whale_flow_index": -0.4,
        "trend_strength": 78,
        "macro_risk_score": 85,
        "liquidity_pulse_score": 75,
        "market_breadth_sma50_pct": 85,
    }
    regime = detector.detect(euphoria_metrics)
    print(f"  Detected: {regime}")
    state = detector.get_current_regime()
    for k, v in state.items():
        print(f"  {k}: {v}")

    # --- Test 2: Neutral scenario ---
    print("\n=== Test 2: NEUTRAL scenario ===")
    neutral_metrics = {
        "fear_greed": 48,
        "funding_rate": 0.00005,
        "volume_change_24h": 3,
        "price_momentum": 0.4,
        "whale_flow_index": 0.02,
        "trend_strength": 42,
        "macro_risk_score": 50,
        "liquidity_pulse_score": 52,
        "market_breadth_sma50_pct": 55,
    }
    # Force cooldown to expire for testing
    detector._last_transition_time = datetime.now(timezone.utc) - timedelta(hours=5)
    regime = detector.detect(neutral_metrics)
    print(f"  Detected: {regime}")
    state = detector.get_current_regime()
    for k, v in state.items():
        print(f"  {k}: {v}")

    # --- Test 3: Fear scenario ---
    print("\n=== Test 3: FEAR scenario ===")
    fear_metrics = {
        "fear_greed": 28,
        "funding_rate": -0.0003,
        "volume_change_24h": -18,
        "price_momentum": -3.5,
        "whale_flow_index": -0.25,
        "trend_strength": 22,
        "macro_risk_score": 30,
        "liquidity_pulse_score": 32,
        "market_breadth_sma50_pct": 30,
    }
    detector._last_transition_time = datetime.now(timezone.utc) - timedelta(hours=5)
    regime = detector.detect(fear_metrics)
    print(f"  Detected: {regime}")
    state = detector.get_current_regime()
    for k, v in state.items():
        print(f"  {k}: {v}")

    # --- Test 4: Capitulation scenario ---
    print("\n=== Test 4: CAPITULATION scenario ===")
    capitulation_metrics = {
        "fear_greed": 10,
        "funding_rate": -0.001,
        "volume_change_24h": 120,
        "price_momentum": -12,
        "whale_flow_index": -0.7,
        "trend_strength": 12,
        "macro_risk_score": 15,
        "liquidity_pulse_score": 20,
        "market_breadth_sma50_pct": 12,
    }
    detector._last_transition_time = datetime.now(timezone.utc) - timedelta(hours=5)
    regime = detector.detect(capitulation_metrics)
    print(f"  Detected: {regime}")
    state = detector.get_current_regime()
    for k, v in state.items():
        print(f"  {k}: {v}")

    # --- Test 5: Cooldown block ---
    print("\n=== Test 5: Cooldown block (back to neutral but too soon) ===")
    detector._last_transition_time = datetime.now(timezone.utc) - timedelta(hours=1)
    regime = detector.detect(neutral_metrics)
    print(f"  Detected: {regime}  (should stay CAPITULATION due to cooldown)")

    # --- Test 6: Optimism scenario ---
    print("\n=== Test 6: OPTIMISM scenario ===")
    optimism_metrics = {
        "fear_greed": 65,
        "funding_rate": 0.0003,
        "volume_change_24h": 25,
        "price_momentum": 2.8,
        "whale_flow_index": 0.3,
        "trend_strength": 58,
        "macro_risk_score": 68,
        "liquidity_pulse_score": 60,
        "market_breadth_sma50_pct": 65,
    }
    detector._last_transition_time = datetime.now(timezone.utc) - timedelta(hours=5)
    regime = detector.detect(optimism_metrics)
    print(f"  Detected: {regime}")
    state = detector.get_current_regime()
    for k, v in state.items():
        print(f"  {k}: {v}")

    # --- Regime history ---
    print("\n=== Regime History ===")
    history = detector.get_regime_history()
    for entry in history:
        print(f"  {entry['timestamp']} — {entry.get('previous_regime')} -> {entry['regime']} "
              f"(conf={entry['confidence']})")

    # --- to_dict ---
    print("\n=== to_dict() (table schema) ===")
    record = detector.to_dict()
    for k, v in record.items():
        print(f"  {k}: {v}")
