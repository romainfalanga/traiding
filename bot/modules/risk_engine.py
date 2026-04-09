"""
Macro Pulse -- Risk Engine.

Centralised risk management: position sizing (Half-Kelly), dynamic stop-loss /
take-profit, trailing stops, max-pain gravity, correlation filtering, circuit
breakers, and Portfolio Fitness Index (PFI).
"""

import sys
import os
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Regime multipliers used across several methods
# ---------------------------------------------------------------------------
REGIME_POSITION_MULTIPLIER = {
    "EUPHORIA": 0.5,
    "OPTIMISM": 1.0,
    "NEUTRAL": 0.8,
    "FEAR": 0.6,
    "CAPITULATION": 0.3,
}

REGIME_STOP_ATR_MULTIPLIER = {
    "EUPHORIA": 1.5,
    "OPTIMISM": 2.0,
    "NEUTRAL": 2.0,
    "FEAR": 2.0,
    "CAPITULATION": 2.5,
}

REGIME_TRAILING_ATR_MULTIPLIER = {
    "EUPHORIA": 1.5,
    "OPTIMISM": 2.0,
    "NEUTRAL": 2.5,
    "FEAR": 3.0,
    "CAPITULATION": 3.0,
}


class RiskEngine:
    """Full-spectrum risk management for the Macro Pulse trading bot."""

    # ------------------------------------------------------------------ init
    def __init__(self) -> None:
        self.initial_balance: float = config.INITIAL_BALANCE
        self.max_position_pct: float = config.MAX_POSITION_PCT
        self.max_concurrent_trades: int = config.MAX_CONCURRENT_TRADES
        self.min_rr_ratio: float = config.MIN_RR_RATIO
        self.correlation_threshold: float = config.CORRELATION_THRESHOLD
        self.circuit_breaker_consec: int = config.CIRCUIT_BREAKER_CONSECUTIVE_LOSSES
        self.circuit_breaker_dd_pause: float = config.CIRCUIT_BREAKER_DRAWDOWN_PAUSE
        self.circuit_breaker_dd_stop: float = config.CIRCUIT_BREAKER_DRAWDOWN_STOP
        logger.info(
            "RiskEngine initialised (initial_balance=%.2f, max_pos=%.1f%%)",
            self.initial_balance,
            self.max_position_pct,
        )

    # =======================================================================
    #  Position sizing -- Half-Kelly Criterion
    # =======================================================================

    def calculate_position_size(
        self,
        balance: float,
        confidence: float,
        atr: float,
        entry_price: float,
        regime: str,
        win_rate: float = 0.55,
        avg_win: float = 1.8,
        avg_loss: float = 1.0,
    ) -> float:
        """Return a position size in USDT using the Half-Kelly criterion.

        Parameters
        ----------
        balance : float
            Current portfolio balance in USDT.
        confidence : float
            Signal confidence (0-1). Scales the final size.
        atr : float
            Current ATR value for the asset.
        entry_price : float
            Expected entry price.
        regime : str
            Market regime label (e.g. ``"OPTIMISM"``).
        win_rate : float
            Historical win-rate estimate (default 0.55).
        avg_win : float
            Average winning trade size in R-multiples (default 1.8).
        avg_loss : float
            Average losing trade size in R-multiples (default 1.0).

        Returns
        -------
        float
            Position size in USDT, capped at ``MAX_POSITION_PCT`` of balance.
        """
        if avg_win <= 0:
            logger.warning("avg_win <= 0 -- returning zero position size")
            return 0.0

        # Full Kelly fraction
        kelly_fraction = (win_rate * avg_win - (1 - win_rate) * avg_loss) / avg_win

        # Clamp to [0, 1] to avoid negative or oversized fractions
        kelly_fraction = max(0.0, min(kelly_fraction, 1.0))

        # Half-Kelly for safety
        half_kelly = kelly_fraction / 2.0

        # Regime adjustment
        regime_mult = REGIME_POSITION_MULTIPLIER.get(regime, 0.8)

        # Confidence scaling
        adjusted_fraction = half_kelly * regime_mult * confidence

        # Position in USDT
        position_usd = balance * adjusted_fraction

        # Hard cap at MAX_POSITION_PCT of balance
        max_allowed = balance * (self.max_position_pct / 100.0)
        position_usd = min(position_usd, max_allowed)

        # Minimum sensible size guard
        position_usd = max(position_usd, 0.0)

        logger.debug(
            "Position size: kelly=%.4f half=%.4f regime_m=%.2f conf=%.2f -> $%.2f",
            kelly_fraction,
            half_kelly,
            regime_mult,
            confidence,
            position_usd,
        )
        return round(position_usd, 2)

    # =======================================================================
    #  Stop-loss -- ATR-based with regime adjustment
    # =======================================================================

    def calculate_stop_loss(
        self,
        entry_price: float,
        atr: float,
        direction: str,
        regime: str,
    ) -> float:
        """Return a stop-loss price based on ATR and market regime.

        Parameters
        ----------
        entry_price : float
        atr : float
        direction : str
            ``"long"`` or ``"short"``.
        regime : str
            Market regime label.

        Returns
        -------
        float
            Stop-loss price.
        """
        multiplier = REGIME_STOP_ATR_MULTIPLIER.get(regime, 2.0)
        distance = multiplier * atr

        if direction == "long":
            stop = entry_price - distance
        else:
            stop = entry_price + distance

        logger.debug(
            "Stop-loss (%s): entry=%.2f atr=%.2f mult=%.1f -> stop=%.2f",
            direction,
            entry_price,
            atr,
            multiplier,
            stop,
        )
        return round(stop, 2)

    # =======================================================================
    #  Take-profit -- minimum R:R ratio
    # =======================================================================

    def calculate_take_profit(
        self,
        entry_price: float,
        stop_loss: float,
        direction: str,
        min_rr: Optional[float] = None,
    ) -> float:
        """Return a take-profit price guaranteeing at least ``min_rr`` reward:risk.

        Parameters
        ----------
        entry_price : float
        stop_loss : float
        direction : str
            ``"long"`` or ``"short"``.
        min_rr : float, optional
            Minimum reward-to-risk ratio. Falls back to ``config.MIN_RR_RATIO``.

        Returns
        -------
        float
            Take-profit price.
        """
        if min_rr is None:
            min_rr = self.min_rr_ratio

        risk = abs(entry_price - stop_loss)

        if direction == "long":
            take_profit = entry_price + (risk * min_rr)
        else:
            take_profit = entry_price - (risk * min_rr)

        logger.debug(
            "Take-profit (%s): entry=%.2f risk=%.2f rr=%.1f -> tp=%.2f",
            direction,
            entry_price,
            risk,
            min_rr,
            take_profit,
        )
        return round(take_profit, 2)

    # =======================================================================
    #  Trailing stop -- regime-aware
    # =======================================================================

    def calculate_trailing_stop(
        self,
        entry_price: float,
        current_price: float,
        atr: float,
        direction: str,
        regime: str,
    ) -> Optional[float]:
        """Return a trailing-stop price that only moves in the profitable direction.

        Returns ``None`` if the trade is not yet in profit (trailing not activated).
        """
        trail_mult = REGIME_TRAILING_ATR_MULTIPLIER.get(regime, 2.5)
        trail_distance = trail_mult * atr

        if direction == "long":
            # Only trail when price is above entry
            if current_price <= entry_price:
                return None
            new_stop = current_price - trail_distance
            return round(new_stop, 2)
        else:
            # Short -- only trail when price is below entry
            if current_price >= entry_price:
                return None
            new_stop = current_price + trail_distance
            return round(new_stop, 2)

    # =======================================================================
    #  Max-pain gravity adjustment
    # =======================================================================

    def check_max_pain_gravity(
        self,
        take_profit: float,
        max_pain: float,
        direction: str,
        hours_to_expiry: float,
    ) -> float:
        """Adjust take-profit towards max-pain when expiry is near (<48 h).

        Parameters
        ----------
        take_profit : float
            Current take-profit target.
        max_pain : float
            Options max-pain strike.
        direction : str
            ``"long"`` or ``"short"``.
        hours_to_expiry : float
            Hours remaining until expiry.

        Returns
        -------
        float
            Adjusted take-profit price (may be unchanged).
        """
        if hours_to_expiry >= 48:
            return take_profit

        if direction == "long" and take_profit > max_pain:
            logger.info(
                "Max-pain gravity: long TP %.2f > max_pain %.2f with %.1fh to expiry -- capping TP",
                take_profit,
                max_pain,
                hours_to_expiry,
            )
            return round(max_pain, 2)

        if direction == "short" and take_profit < max_pain:
            logger.info(
                "Max-pain gravity: short TP %.2f < max_pain %.2f with %.1fh to expiry -- raising TP",
                take_profit,
                max_pain,
                hours_to_expiry,
            )
            return round(max_pain, 2)

        return take_profit

    # =======================================================================
    #  Correlation filter
    # =======================================================================

    def check_correlation(
        self,
        new_symbol: str,
        new_direction: str,
        open_positions: List[Dict[str, Any]],
        price_history: Dict[str, List[float]],
    ) -> Tuple[bool, str]:
        """Check whether a new trade is too correlated with open positions.

        Parameters
        ----------
        new_symbol : str
            Symbol of the proposed trade (e.g. ``"BTC/USDT"``).
        new_direction : str
            ``"long"`` or ``"short"``.
        open_positions : list[dict]
            Currently open positions, each with ``symbol`` and ``direction``.
        price_history : dict[str, list[float]]
            Recent closing prices keyed by symbol.  At least 20 data-points
            are recommended for a meaningful correlation.

        Returns
        -------
        tuple[bool, str]
            ``(approved, reason)`` -- ``approved`` is ``True`` when the trade
            passes the correlation check.
        """
        if new_symbol not in price_history or len(price_history[new_symbol]) < 10:
            # Not enough data to evaluate correlation -- allow by default
            return True, "Insufficient price history for correlation check -- approved by default"

        new_prices = np.array(price_history[new_symbol], dtype=float)

        for pos in open_positions:
            pos_symbol = pos.get("symbol", "")
            pos_direction = pos.get("direction", "")

            if pos_symbol == new_symbol and pos_direction == new_direction:
                return False, f"Duplicate trade: already {pos_direction} on {pos_symbol}"

            if pos_symbol not in price_history or len(price_history[pos_symbol]) < 10:
                continue

            pos_prices = np.array(price_history[pos_symbol], dtype=float)

            # Align lengths
            min_len = min(len(new_prices), len(pos_prices))
            a = new_prices[-min_len:]
            b = pos_prices[-min_len:]

            # Percentage returns for correlation
            if min_len < 2:
                continue
            returns_a = np.diff(a) / a[:-1]
            returns_b = np.diff(b) / b[:-1]

            # Avoid divide-by-zero with constant series
            if np.std(returns_a) == 0 or np.std(returns_b) == 0:
                continue

            corr = float(np.corrcoef(returns_a, returns_b)[0, 1])

            if abs(corr) > self.correlation_threshold and pos_direction == new_direction:
                reason = (
                    f"High correlation ({corr:.2f}) between {new_symbol} and "
                    f"{pos_symbol} (both {new_direction}) -- trade rejected"
                )
                logger.warning(reason)
                return False, reason

        return True, "Correlation check passed"

    # =======================================================================
    #  Circuit breaker
    # =======================================================================

    def check_circuit_breaker(
        self,
        recent_trades: List[Dict[str, Any]],
        balance: float,
        initial_balance: float,
    ) -> Dict[str, Any]:
        """Evaluate circuit-breaker conditions.

        Parameters
        ----------
        recent_trades : list[dict]
            Trade records ordered newest-first, each with at least a ``pnl`` key.
        balance : float
            Current portfolio balance.
        initial_balance : float
            Starting balance for drawdown calculation.

        Returns
        -------
        dict
            ``{active: bool, reason: str, resume_time: datetime | None}``
        """
        now = datetime.now(timezone.utc)

        # --- Consecutive losses ---
        consecutive_losses = 0
        for trade in recent_trades:
            pnl = trade.get("pnl", 0)
            if pnl is None:
                continue
            if float(pnl) < 0:
                consecutive_losses += 1
            else:
                break  # streak broken

        if consecutive_losses >= self.circuit_breaker_consec:
            resume = now + timedelta(hours=1)
            reason = (
                f"Circuit breaker: {consecutive_losses} consecutive losses "
                f"(>= {self.circuit_breaker_consec}) -- pausing for 1 h"
            )
            logger.warning(reason)
            return {"active": True, "reason": reason, "resume_time": resume}

        # --- Drawdown from peak equity ---
        peak_equity = initial_balance
        for trade in reversed(recent_trades):
            cumulative = trade.get("cumulative_equity", None)
            if cumulative is not None:
                peak_equity = max(peak_equity, float(cumulative))

        # Also consider that balance itself may be the current peak
        peak_equity = max(peak_equity, initial_balance)

        drawdown_pct = ((peak_equity - balance) / peak_equity) * 100.0 if peak_equity > 0 else 0.0

        if drawdown_pct >= self.circuit_breaker_dd_stop:
            reason = (
                f"Circuit breaker: drawdown {drawdown_pct:.1f}% >= "
                f"{self.circuit_breaker_dd_stop}% -- STOP trading entirely"
            )
            logger.critical(reason)
            return {"active": True, "reason": reason, "resume_time": None}

        if drawdown_pct >= self.circuit_breaker_dd_pause:
            resume = now + timedelta(hours=4)
            reason = (
                f"Circuit breaker: drawdown {drawdown_pct:.1f}% >= "
                f"{self.circuit_breaker_dd_pause}% -- pausing for 4 h"
            )
            logger.warning(reason)
            return {"active": True, "reason": reason, "resume_time": resume}

        return {"active": False, "reason": "No circuit-breaker triggered", "resume_time": None}

    # =======================================================================
    #  Portfolio Fitness Index (PFI)
    # =======================================================================

    def calculate_pfi(
        self,
        balance: float,
        initial_balance: float,
        total_trades: int,
        win_rate: float,
        max_drawdown: float,
        sharpe: float,
    ) -> float:
        """Compute a Portfolio Fitness Index (0-100).

        The PFI blends:
        - **Return score** (35 %): total return normalised against a 50 % target.
        - **Consistency score** (30 %): win-rate contribution + trade volume bonus.
        - **Risk-adjusted score** (35 %): Sharpe ratio quality + drawdown penalty.

        Parameters
        ----------
        balance : float
            Current portfolio balance.
        initial_balance : float
            Starting balance.
        total_trades : int
            Total number of closed trades.
        win_rate : float
            Win-rate as a fraction (0-1).
        max_drawdown : float
            Maximum drawdown percentage experienced (0-100).
        sharpe : float
            Sharpe ratio estimate.

        Returns
        -------
        float
            Score in [0, 100].
        """
        # --- Return component (0-35) ---
        total_return_pct = ((balance - initial_balance) / initial_balance) * 100.0 if initial_balance > 0 else 0.0
        # Normalise: 50 % return = perfect 35 points
        return_score = min(35.0, max(0.0, (total_return_pct / 50.0) * 35.0))

        # --- Consistency component (0-30) ---
        # Win-rate portion (0-20): 60 % win-rate = full 20 pts
        wr_score = min(20.0, max(0.0, (win_rate / 0.60) * 20.0))
        # Trade-volume bonus (0-10): having >= 30 trades = full 10 pts
        vol_score = min(10.0, max(0.0, (total_trades / 30.0) * 10.0))
        consistency_score = wr_score + vol_score

        # --- Risk-adjusted component (0-35) ---
        # Sharpe portion (0-20): Sharpe >= 2.0 = perfect 20 pts
        sharpe_score = min(20.0, max(0.0, (sharpe / 2.0) * 20.0))
        # Drawdown penalty (0-15): 0 % dd = 15 pts, >= 20 % dd = 0 pts
        dd_penalty = min(15.0, max(0.0, (1.0 - max_drawdown / 20.0) * 15.0))
        risk_score = sharpe_score + dd_penalty

        pfi = return_score + consistency_score + risk_score
        pfi = round(max(0.0, min(100.0, pfi)), 1)

        logger.info(
            "PFI=%.1f (return=%.1f consistency=%.1f risk=%.1f)",
            pfi,
            return_score,
            consistency_score,
            risk_score,
        )
        return pfi

    # =======================================================================
    #  Master trade validation
    # =======================================================================

    def validate_trade(
        self,
        trade_proposal: Dict[str, Any],
        balance: float,
        open_positions: List[Dict[str, Any]],
        recent_trades: List[Dict[str, Any]],
        regime: str,
        atr: float,
        max_pain: Optional[float] = None,
        hours_to_expiry: Optional[float] = None,
        price_history: Optional[Dict[str, List[float]]] = None,
    ) -> Dict[str, Any]:
        """Run all risk checks on a proposed trade.

        Parameters
        ----------
        trade_proposal : dict
            Must contain at least: ``symbol``, ``direction``, ``entry_price``,
            ``confidence``.  Optionally: ``stop_loss``, ``take_profit``.
        balance : float
        open_positions : list[dict]
        recent_trades : list[dict]
        regime : str
        atr : float
        max_pain : float, optional
        hours_to_expiry : float, optional
        price_history : dict, optional

        Returns
        -------
        dict
            ``{approved: bool, adjusted_trade: dict, rejection_reasons: list[str]}``
        """
        rejection_reasons: List[str] = []
        symbol = trade_proposal.get("symbol", "UNKNOWN")
        direction = trade_proposal.get("direction", "long")
        entry_price = float(trade_proposal.get("entry_price", 0))
        confidence = float(trade_proposal.get("confidence", 0.5))

        # ----- 1. Circuit breaker -----
        cb = self.check_circuit_breaker(recent_trades, balance, self.initial_balance)
        if cb["active"]:
            rejection_reasons.append(cb["reason"])
            return {
                "approved": False,
                "adjusted_trade": trade_proposal,
                "rejection_reasons": rejection_reasons,
            }

        # ----- 2. Concurrent trades limit -----
        if len(open_positions) >= self.max_concurrent_trades:
            reason = (
                f"Max concurrent trades reached ({len(open_positions)}"
                f"/{self.max_concurrent_trades})"
            )
            rejection_reasons.append(reason)
            return {
                "approved": False,
                "adjusted_trade": trade_proposal,
                "rejection_reasons": rejection_reasons,
            }

        # ----- 3. Correlation check -----
        if price_history is None:
            price_history = {}
        corr_ok, corr_reason = self.check_correlation(
            symbol, direction, open_positions, price_history
        )
        if not corr_ok:
            rejection_reasons.append(corr_reason)
            return {
                "approved": False,
                "adjusted_trade": trade_proposal,
                "rejection_reasons": rejection_reasons,
            }

        # ----- 4. Position sizing -----
        position_size = self.calculate_position_size(
            balance, confidence, atr, entry_price, regime
        )
        if position_size <= 0:
            rejection_reasons.append("Calculated position size is zero or negative")
            return {
                "approved": False,
                "adjusted_trade": trade_proposal,
                "rejection_reasons": rejection_reasons,
            }

        # ----- 5. Stop-loss -----
        stop_loss = trade_proposal.get("stop_loss")
        if stop_loss is None:
            stop_loss = self.calculate_stop_loss(entry_price, atr, direction, regime)
        else:
            stop_loss = float(stop_loss)

        # ----- 6. Take-profit -----
        take_profit = trade_proposal.get("take_profit")
        if take_profit is None:
            take_profit = self.calculate_take_profit(entry_price, stop_loss, direction)
        else:
            take_profit = float(take_profit)

        # ----- 7. Reward-to-risk validation -----
        risk = abs(entry_price - stop_loss)
        reward = abs(take_profit - entry_price)
        rr_ratio = (reward / risk) if risk > 0 else 0.0

        if rr_ratio < self.min_rr_ratio:
            rejection_reasons.append(
                f"R:R ratio {rr_ratio:.2f} below minimum {self.min_rr_ratio}"
            )
            return {
                "approved": False,
                "adjusted_trade": trade_proposal,
                "rejection_reasons": rejection_reasons,
            }

        # ----- 8. Max-pain gravity adjustment -----
        if max_pain is not None and hours_to_expiry is not None:
            take_profit = self.check_max_pain_gravity(
                take_profit, max_pain, direction, hours_to_expiry
            )
            # Re-validate R:R after adjustment
            reward = abs(take_profit - entry_price)
            rr_after = (reward / risk) if risk > 0 else 0.0
            if rr_after < self.min_rr_ratio:
                rejection_reasons.append(
                    f"R:R ratio {rr_after:.2f} after max-pain adjustment "
                    f"below minimum {self.min_rr_ratio}"
                )
                return {
                    "approved": False,
                    "adjusted_trade": trade_proposal,
                    "rejection_reasons": rejection_reasons,
                }

        # ----- Build adjusted trade -----
        quantity = position_size / entry_price if entry_price > 0 else 0.0

        adjusted_trade = {
            **trade_proposal,
            "position_size_usd": round(position_size, 2),
            "quantity": round(quantity, 6),
            "stop_loss": round(stop_loss, 2),
            "take_profit": round(take_profit, 2),
            "rr_ratio": round(rr_ratio, 2),
            "regime": regime,
        }

        logger.info(
            "Trade APPROVED: %s %s @ %.2f | size=$%.2f | SL=%.2f | TP=%.2f | R:R=%.2f",
            direction.upper(),
            symbol,
            entry_price,
            position_size,
            stop_loss,
            take_profit,
            rr_ratio,
        )

        return {
            "approved": True,
            "adjusted_trade": adjusted_trade,
            "rejection_reasons": [],
        }
