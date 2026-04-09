"""
Macro Pulse -- Backtester.

Replays historical macro events and simulates trades to evaluate strategy
performance.  Fetches stored events, market data, technical snapshots, regime
history, and (optionally) stored AI decisions from the DataStore, then runs
a paper-trading simulation with configurable parameters.
"""

import json
import logging
import math
import sys
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Config import -- works both as package import and standalone execution
# ---------------------------------------------------------------------------
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

logger = logging.getLogger(__name__)


class Backtester:
    """Replays historical events and measures strategy performance."""

    # ------------------------------------------------------------------ init
    def __init__(self, data_store) -> None:
        self.data_store = data_store
        logger.info("Backtester initialised")

    # =======================================================================
    #  Main back-test entry point
    # =======================================================================

    async def run_backtest(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a full back-test over a date range.

        Parameters
        ----------
        params : dict
            Required keys:
                ``start_date``  -- ISO-8601 date string (e.g. ``"2025-01-01"``).
                ``end_date``    -- ISO-8601 date string.
                ``name``        -- Human-readable label for this run.
            Optional:
                ``custom_params`` -- dict overriding defaults:
                    ``confidence_threshold`` (float, default 0.6),
                    ``atr_multiplier``       (float, default 2.0),
                    ``take_profit_rr``       (float, default 1.5),
                    ``max_position_pct``     (float, default 5.0),
                    ``trading_fee_pct``      (float, default 0.075).

        Returns
        -------
        dict
            A dict matching the ``backtest_results`` table schema, ready for
            insertion via ``data_store.insert_backtest_result()``.
        """

        start_date = params["start_date"]
        end_date = params["end_date"]
        name = params.get("name", "Unnamed backtest")
        custom = params.get("custom_params", {})

        # Merge custom parameters with defaults
        confidence_threshold = float(custom.get("confidence_threshold", config.MIN_CONFIDENCE_AVG))
        atr_multiplier = float(custom.get("atr_multiplier", 2.0))
        take_profit_rr = float(custom.get("take_profit_rr", config.MIN_RR_RATIO))
        max_position_pct = float(custom.get("max_position_pct", config.MAX_POSITION_PCT))
        trading_fee_pct = float(custom.get("trading_fee_pct", config.TRADING_FEE_PCT))

        logger.info(
            "Starting backtest '%s'  %s -> %s  (conf=%.2f atr_m=%.1f rr=%.1f)",
            name,
            start_date,
            end_date,
            confidence_threshold,
            atr_multiplier,
            take_profit_rr,
        )

        # ------------------------------------------------------------------
        # 1. Fetch historical data from DataStore
        # ------------------------------------------------------------------
        events = self._fetch_events_in_range(start_date, end_date)
        if not events:
            logger.warning("No events found in range %s -> %s", start_date, end_date)
            empty_metrics = self.calculate_metrics([], config.INITIAL_BALANCE)
            return self.to_dict(name, params, [], empty_metrics)

        logger.info("Fetched %d historical events for backtest", len(events))

        # ------------------------------------------------------------------
        # 2. Simulate trades event by event
        # ------------------------------------------------------------------
        balance = config.INITIAL_BALANCE
        trades: List[Dict[str, Any]] = []
        peak_equity = balance
        balance_curve: List[Dict[str, Any]] = [
            {"timestamp": start_date, "equity": balance},
        ]

        for event in events:
            event_time = event.get("timestamp", "")
            event_name = event.get("event_name", event.get("title", "Unknown"))
            symbol = event.get("symbol", "BTC/USDT")

            # ----- Fetch supporting context for this event -----
            market_data = self._fetch_market_at_time(symbol, event_time)
            technical = self._fetch_technical_at_time(symbol, event_time)
            regime_data = self._fetch_regime_at_time(event_time)
            ai_decision = self._fetch_ai_decision_at_time(event_time)

            # ----- Determine trade direction & confidence -----
            direction: Optional[str] = None
            confidence: float = 0.0

            if ai_decision:
                # Use the stored AI decision if available
                direction = ai_decision.get("consensus_direction")
                confidence = float(ai_decision.get("avg_confidence", 0) or 0)
                vote_result = ai_decision.get("vote_result", "")
                if vote_result in ("NO_TRADE", "HOLD", ""):
                    direction = None
            else:
                # Infer from event impact when no AI decision exists
                impact = event.get("impact", "").upper()
                if impact in ("HIGH_BULLISH", "BULLISH"):
                    direction = "long"
                    confidence = 0.65
                elif impact in ("HIGH_BEARISH", "BEARISH"):
                    direction = "short"
                    confidence = 0.65
                # Neutral / unknown -> skip

            if direction is None or confidence < confidence_threshold:
                continue

            # ----- Derive prices -----
            entry_price = self._extract_price(market_data, event)
            if entry_price is None or entry_price <= 0:
                continue

            atr = self._extract_atr(technical)
            if atr is None or atr <= 0:
                # Fallback: estimate ATR as 2 % of entry price
                atr = entry_price * 0.02

            regime = regime_data.get("regime", "NEUTRAL") if regime_data else "NEUTRAL"

            # ----- Compute SL / TP -----
            sl_distance = atr * atr_multiplier
            if direction == "long":
                stop_loss = entry_price - sl_distance
                take_profit = entry_price + (sl_distance * take_profit_rr)
            else:
                stop_loss = entry_price + sl_distance
                take_profit = entry_price - (sl_distance * take_profit_rr)

            # ----- Position sizing -----
            position_pct = min(max_position_pct, max_position_pct * confidence)
            position_usd = balance * (position_pct / 100.0)
            if position_usd <= 0:
                continue
            quantity = position_usd / entry_price

            # ----- Simulate exit -----
            exit_price, close_reason = self._simulate_exit(
                symbol=symbol,
                direction=direction,
                entry_price=entry_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                event_time=event_time,
                market_data=market_data,
                technical=technical,
            )

            # ----- Calculate PnL -----
            if direction == "long":
                raw_pnl = (exit_price - entry_price) * quantity
            else:
                raw_pnl = (entry_price - exit_price) * quantity

            # Subtract round-trip fees
            entry_fee = position_usd * (trading_fee_pct / 100.0)
            exit_value = quantity * exit_price
            exit_fee = exit_value * (trading_fee_pct / 100.0)
            net_pnl = raw_pnl - entry_fee - exit_fee
            pnl_pct = (net_pnl / position_usd) * 100.0 if position_usd > 0 else 0.0

            balance += net_pnl
            peak_equity = max(peak_equity, balance)

            trade_record = {
                "symbol": symbol,
                "direction": direction,
                "entry_price": round(entry_price, 2),
                "exit_price": round(exit_price, 2),
                "entry_time": event_time,
                "exit_time": event_time,  # simplified -- same event window
                "stop_loss": round(stop_loss, 2),
                "take_profit": round(take_profit, 2),
                "position_usd": round(position_usd, 2),
                "quantity": round(quantity, 6),
                "pnl": round(net_pnl, 2),
                "pnl_pct": round(pnl_pct, 2),
                "close_reason": close_reason,
                "event_name": event_name,
                "regime": regime,
                "confidence": round(confidence, 4),
                "balance_after": round(balance, 2),
                "atr": round(atr, 2),
                "fees": round(entry_fee + exit_fee, 2),
            }
            trades.append(trade_record)

            balance_curve.append({
                "timestamp": event_time,
                "equity": round(balance, 2),
            })

        # ------------------------------------------------------------------
        # 3. Calculate performance metrics
        # ------------------------------------------------------------------
        metrics = self.calculate_metrics(trades, config.INITIAL_BALANCE)

        logger.info(
            "Backtest '%s' complete: %d trades | win_rate=%.1f%% | pnl=%.2f%% | "
            "max_dd=%.2f%% | sharpe=%.2f",
            name,
            metrics["total_trades"],
            metrics["win_rate"] * 100,
            metrics["total_pnl_pct"],
            metrics["max_drawdown"],
            metrics["sharpe_ratio"],
        )

        result = self.to_dict(name, params, trades, metrics)
        result["balance_curve"] = balance_curve
        return result

    # =======================================================================
    #  Performance metrics
    # =======================================================================

    def calculate_metrics(
        self,
        trades: List[Dict[str, Any]],
        initial_balance: float,
    ) -> Dict[str, Any]:
        """Compute comprehensive performance metrics from a list of trades.

        Parameters
        ----------
        trades : list[dict]
            Each dict must have at least ``pnl`` and ``pnl_pct``.
        initial_balance : float
            Starting balance for equity-curve and drawdown calculations.

        Returns
        -------
        dict  Metrics dict with keys documented below.
        """

        total_trades = len(trades)
        if total_trades == 0:
            return {
                "total_trades": 0,
                "wins": 0,
                "losses": 0,
                "win_rate": 0.0,
                "total_pnl": 0.0,
                "total_pnl_pct": 0.0,
                "max_drawdown": 0.0,
                "sharpe_ratio": 0.0,
                "profit_factor": 0.0,
                "avg_win": 0.0,
                "avg_loss": 0.0,
                "max_consecutive_wins": 0,
                "max_consecutive_losses": 0,
                "expectancy": 0.0,
            }

        # ----- Basic counts -----
        wins = [t for t in trades if float(t.get("pnl", 0)) > 0]
        losses = [t for t in trades if float(t.get("pnl", 0)) <= 0]
        num_wins = len(wins)
        num_losses = len(losses)
        win_rate = num_wins / total_trades if total_trades > 0 else 0.0

        # ----- PnL totals -----
        total_pnl = sum(float(t.get("pnl", 0)) for t in trades)
        total_pnl_pct = (total_pnl / initial_balance) * 100.0 if initial_balance > 0 else 0.0

        # ----- Gross profit / loss & profit factor -----
        gross_profit = sum(float(t.get("pnl", 0)) for t in wins)
        gross_loss = abs(sum(float(t.get("pnl", 0)) for t in losses))
        profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else float("inf") if gross_profit > 0 else 0.0

        # ----- Average win / loss -----
        avg_win = (gross_profit / num_wins) if num_wins > 0 else 0.0
        avg_loss = (gross_loss / num_losses) if num_losses > 0 else 0.0

        # ----- Max drawdown from peak equity -----
        equity = initial_balance
        peak = equity
        max_dd = 0.0
        for t in trades:
            equity += float(t.get("pnl", 0))
            peak = max(peak, equity)
            dd = ((peak - equity) / peak) * 100.0 if peak > 0 else 0.0
            max_dd = max(max_dd, dd)

        # ----- Sharpe ratio (annualised, assuming ~365 trading days) -----
        daily_returns = [float(t.get("pnl_pct", 0)) / 100.0 for t in trades]
        if len(daily_returns) >= 2:
            avg_ret = sum(daily_returns) / len(daily_returns)
            std_ret = (
                sum((r - avg_ret) ** 2 for r in daily_returns)
                / (len(daily_returns) - 1)
            ) ** 0.5
            sharpe_ratio = (avg_ret / std_ret) * math.sqrt(365) if std_ret > 0 else 0.0
        else:
            sharpe_ratio = 0.0

        # ----- Consecutive wins / losses -----
        max_consec_wins = 0
        max_consec_losses = 0
        current_wins = 0
        current_losses = 0
        for t in trades:
            pnl = float(t.get("pnl", 0))
            if pnl > 0:
                current_wins += 1
                current_losses = 0
                max_consec_wins = max(max_consec_wins, current_wins)
            else:
                current_losses += 1
                current_wins = 0
                max_consec_losses = max(max_consec_losses, current_losses)

        # ----- Expectancy -----
        # E = (win_rate * avg_win) - ((1 - win_rate) * avg_loss)
        expectancy = (win_rate * avg_win) - ((1 - win_rate) * avg_loss)

        return {
            "total_trades": total_trades,
            "wins": num_wins,
            "losses": num_losses,
            "win_rate": round(win_rate, 4),
            "total_pnl": round(total_pnl, 2),
            "total_pnl_pct": round(total_pnl_pct, 2),
            "max_drawdown": round(max_dd, 2),
            "sharpe_ratio": round(sharpe_ratio, 4),
            "profit_factor": round(profit_factor, 4) if profit_factor != float("inf") else 9999.99,
            "avg_win": round(avg_win, 2),
            "avg_loss": round(avg_loss, 2),
            "max_consecutive_wins": max_consec_wins,
            "max_consecutive_losses": max_consec_losses,
            "expectancy": round(expectancy, 2),
        }

    # =======================================================================
    #  Serialise results for storage
    # =======================================================================

    def to_dict(
        self,
        name: str,
        params: Dict[str, Any],
        trades: List[Dict[str, Any]],
        metrics: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Build a dict matching the ``backtest_results`` table schema.

        Parameters
        ----------
        name : str
            Human-readable name for this run.
        params : dict
            The full params dict passed to ``run_backtest``.
        trades : list[dict]
            All simulated trade records.
        metrics : dict
            Output of ``calculate_metrics``.

        Returns
        -------
        dict  Ready for ``data_store.insert_backtest_result()``.
        """

        return {
            "name": name,
            "start_date": params.get("start_date"),
            "end_date": params.get("end_date"),
            "params": json.dumps(params.get("custom_params", {})),
            "total_trades": metrics.get("total_trades", 0),
            "win_rate": metrics.get("win_rate", 0.0),
            "total_pnl_pct": metrics.get("total_pnl_pct", 0.0),
            "max_drawdown": metrics.get("max_drawdown", 0.0),
            "sharpe_ratio": metrics.get("sharpe_ratio", 0.0),
            "results_detail": json.dumps({
                "trades": trades,
                "metrics": metrics,
            }),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

    # =======================================================================
    #  Data-fetching helpers (private)
    # =======================================================================

    def _fetch_events_in_range(
        self,
        start_date: str,
        end_date: str,
    ) -> List[Dict[str, Any]]:
        """Fetch macro_events within [start_date, end_date] from Supabase."""
        try:
            response = (
                self.data_store.client.table("macro_events")
                .select("*")
                .gte("timestamp", start_date)
                .lte("timestamp", end_date)
                .order("timestamp", desc=False)
                .execute()
            )
            return response.data or []
        except Exception:
            logger.exception(
                "Failed to fetch events for range %s -> %s", start_date, end_date
            )
            return []

    def _fetch_market_at_time(
        self,
        symbol: str,
        event_time: str,
    ) -> Optional[Dict[str, Any]]:
        """Return the closest market_continuous row at or before *event_time*."""
        try:
            response = (
                self.data_store.client.table("market_continuous")
                .select("*")
                .eq("symbol", symbol)
                .lte("timestamp", event_time)
                .order("timestamp", desc=True)
                .limit(1)
                .execute()
            )
            return response.data[0] if response.data else None
        except Exception:
            logger.exception("Failed to fetch market data for %s at %s", symbol, event_time)
            return None

    def _fetch_technical_at_time(
        self,
        symbol: str,
        event_time: str,
    ) -> Optional[Dict[str, Any]]:
        """Return the closest technical_snapshot at or before *event_time*."""
        try:
            response = (
                self.data_store.client.table("technical_snapshots")
                .select("*")
                .eq("symbol", symbol)
                .lte("timestamp", event_time)
                .order("timestamp", desc=True)
                .limit(1)
                .execute()
            )
            return response.data[0] if response.data else None
        except Exception:
            logger.exception(
                "Failed to fetch technical snapshot for %s at %s", symbol, event_time
            )
            return None

    def _fetch_regime_at_time(self, event_time: str) -> Optional[Dict[str, Any]]:
        """Return the regime_history row closest to (at or before) *event_time*."""
        try:
            response = (
                self.data_store.client.table("regime_history")
                .select("*")
                .lte("timestamp", event_time)
                .order("timestamp", desc=True)
                .limit(1)
                .execute()
            )
            return response.data[0] if response.data else None
        except Exception:
            logger.exception("Failed to fetch regime at %s", event_time)
            return None

    def _fetch_ai_decision_at_time(
        self,
        event_time: str,
    ) -> Optional[Dict[str, Any]]:
        """Return a stored ai_decision nearest to *event_time* (within 1 hour)."""
        try:
            response = (
                self.data_store.client.table("ai_decisions")
                .select("*")
                .lte("created_at", event_time)
                .order("created_at", desc=True)
                .limit(1)
                .execute()
            )
            if not response.data:
                return None

            decision = response.data[0]

            # Only use if it is reasonably close to the event (within 1 hour)
            decision_time = decision.get("created_at", "")
            try:
                dt_event = datetime.fromisoformat(
                    event_time.replace("Z", "+00:00")
                )
                dt_decision = datetime.fromisoformat(
                    decision_time.replace("Z", "+00:00")
                )
                delta_seconds = abs((dt_event - dt_decision).total_seconds())
                if delta_seconds > 3600:
                    return None
            except (ValueError, TypeError):
                pass  # Can't parse -- use the decision anyway

            return decision
        except Exception:
            logger.exception("Failed to fetch AI decision at %s", event_time)
            return None

    # =======================================================================
    #  Exit simulation helpers (private)
    # =======================================================================

    def _simulate_exit(
        self,
        symbol: str,
        direction: str,
        entry_price: float,
        stop_loss: float,
        take_profit: float,
        event_time: str,
        market_data: Optional[Dict[str, Any]],
        technical: Optional[Dict[str, Any]],
    ) -> tuple:
        """Determine simulated exit price and reason.

        Uses stored high / low from market data to check whether SL or TP
        would have been hit.  Falls back to heuristics when data is sparse.

        Returns
        -------
        tuple[float, str]  ``(exit_price, close_reason)``
        """

        high = None
        low = None

        # Try to extract high / low from market_data
        if market_data:
            high = market_data.get("high")
            low = market_data.get("low")
            if high is not None:
                high = float(high)
            if low is not None:
                low = float(low)

        # Also try the technical snapshot for OHLC data
        if (high is None or low is None) and technical:
            indicators = technical.get("indicators", {})
            if isinstance(indicators, str):
                try:
                    indicators = json.loads(indicators)
                except (json.JSONDecodeError, TypeError):
                    indicators = {}
            if high is None:
                high = indicators.get("high")
                if high is not None:
                    high = float(high)
            if low is None:
                low = indicators.get("low")
                if low is not None:
                    low = float(low)

        # ----- Determine outcome -----
        if direction == "long":
            # Check stop-loss hit
            if low is not None and low <= stop_loss:
                return stop_loss, "stop_loss"
            # Check take-profit hit
            if high is not None and high >= take_profit:
                return take_profit, "take_profit"
        else:  # short
            # Check stop-loss hit
            if high is not None and high >= stop_loss:
                return stop_loss, "stop_loss"
            # Check take-profit hit
            if low is not None and low <= take_profit:
                return take_profit, "take_profit"

        # Neither SL nor TP was clearly hit -- use close price or
        # estimate a partial move
        close_price = None
        if market_data:
            close_price = market_data.get("close") or market_data.get("price")
            if close_price is not None:
                close_price = float(close_price)

        if close_price is not None:
            return close_price, "event_window_close"

        # Absolute fallback: assume a small random-like move based on
        # the midpoint of SL / TP (biased slightly toward entry to
        # represent typical noise)
        midpoint = (stop_loss + take_profit) / 2.0
        fallback_exit = (entry_price * 0.7) + (midpoint * 0.3)
        return round(fallback_exit, 2), "simulated_estimate"

    # =======================================================================
    #  Price / ATR extraction helpers
    # =======================================================================

    @staticmethod
    def _extract_price(
        market_data: Optional[Dict[str, Any]],
        event: Dict[str, Any],
    ) -> Optional[float]:
        """Extract an entry price from market data or fall back to event data."""

        if market_data:
            for key in ("price", "close", "last"):
                val = market_data.get(key)
                if val is not None:
                    try:
                        return float(val)
                    except (ValueError, TypeError):
                        continue

        # Fallback: sometimes the event itself carries a reference price
        for key in ("price", "reference_price", "btc_price"):
            val = event.get(key)
            if val is not None:
                try:
                    return float(val)
                except (ValueError, TypeError):
                    continue

        return None

    @staticmethod
    def _extract_atr(technical: Optional[Dict[str, Any]]) -> Optional[float]:
        """Extract ATR from a technical_snapshot row."""

        if technical is None:
            return None

        indicators = technical.get("indicators", {})
        if isinstance(indicators, str):
            try:
                indicators = json.loads(indicators)
            except (json.JSONDecodeError, TypeError):
                return None

        atr = indicators.get("atr") or indicators.get("ATR") or indicators.get("atr_14")
        if atr is not None:
            try:
                return float(atr)
            except (ValueError, TypeError):
                return None

        return None
