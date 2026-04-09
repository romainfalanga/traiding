"""
Macro Pulse -- Paper Trader.

Simulated trade execution engine with realistic slippage, fees, trailing stops,
max-pain gravity adjustments, and cooldown management.  All state is persisted
to Supabase via the DataStore layer.
"""

import sys
import os
import logging
import random
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

logger = logging.getLogger(__name__)


class PaperTrader:
    """Paper-trading execution engine for the Macro Pulse bot.

    Manages a virtual portfolio with realistic fills (slippage + fees),
    position lifecycle (open / update / close), trailing-stop management,
    max-pain gravity adjustments, and post-event cooldowns.
    """

    # ------------------------------------------------------------------ init
    def __init__(self, data_store: Any, risk_engine: Any) -> None:
        """Initialise with references to DataStore and RiskEngine.

        Parameters
        ----------
        data_store : DataStore
            Supabase persistence layer.
        risk_engine : RiskEngine
            Centralised risk management engine.
        """
        self.data_store = data_store
        self.risk_engine = risk_engine

        # In-memory portfolio state -- hydrated from DB in ``initialize()``.
        self.portfolio: Dict[str, Any] = {
            "balance": config.INITIAL_BALANCE,
            "equity": config.INITIAL_BALANCE,
            "initial_balance": config.INITIAL_BALANCE,
            "open_positions": [],
            "trade_history": [],
            "total_trades": 0,
            "winning_trades": 0,
            "losing_trades": 0,
            "max_drawdown_pct": 0.0,
            "peak_equity": config.INITIAL_BALANCE,
        }

        # Cooldown tracker: event_name -> datetime when cooldown expires
        self.cooldowns: Dict[str, datetime] = {}

        logger.info(
            "PaperTrader created (balance=%.2f, data_store=%s)",
            self.portfolio["balance"],
            type(data_store).__name__,
        )

    # =======================================================================
    #  Async bootstrap
    # =======================================================================

    async def initialize(self) -> None:
        """Load (or create) the portfolio from Supabase.

        If no portfolio row exists, an initial row is persisted so that the
        state survives restarts.
        """
        try:
            existing = self.data_store.get_latest_portfolio()
            if existing:
                self.portfolio["balance"] = float(existing.get("balance", config.INITIAL_BALANCE))
                self.portfolio["equity"] = float(existing.get("equity", config.INITIAL_BALANCE))
                self.portfolio["initial_balance"] = float(
                    existing.get("initial_balance", config.INITIAL_BALANCE)
                )
                self.portfolio["open_positions"] = existing.get("open_positions", []) or []
                self.portfolio["trade_history"] = existing.get("trade_history", []) or []
                self.portfolio["total_trades"] = int(existing.get("total_trades", 0))
                self.portfolio["winning_trades"] = int(existing.get("winning_trades", 0))
                self.portfolio["losing_trades"] = int(existing.get("losing_trades", 0))
                self.portfolio["max_drawdown_pct"] = float(existing.get("max_drawdown_pct", 0.0))
                self.portfolio["peak_equity"] = float(
                    existing.get("peak_equity", self.portfolio["initial_balance"])
                )
                logger.info(
                    "Portfolio loaded from Supabase (balance=%.2f, equity=%.2f, trades=%d)",
                    self.portfolio["balance"],
                    self.portfolio["equity"],
                    self.portfolio["total_trades"],
                )
            else:
                # Persist an initial portfolio row
                self.data_store.update_portfolio({
                    "balance": self.portfolio["balance"],
                    "equity": self.portfolio["equity"],
                    "initial_balance": self.portfolio["initial_balance"],
                    "open_positions": self.portfolio["open_positions"],
                    "trade_history": [],
                    "total_trades": 0,
                    "winning_trades": 0,
                    "losing_trades": 0,
                    "max_drawdown_pct": 0.0,
                    "peak_equity": self.portfolio["peak_equity"],
                })
                logger.info("Initial portfolio created in Supabase (balance=%.2f)", self.portfolio["balance"])
        except Exception:
            logger.exception("Failed to initialise portfolio from Supabase -- using defaults")

    # =======================================================================
    #  Slippage model
    # =======================================================================

    def apply_slippage(self, price: float, direction: str, is_entry: bool = True) -> float:
        """Apply realistic random slippage (0.01-0.05 %) in the adverse direction.

        Parameters
        ----------
        price : float
            The intended fill price.
        direction : str
            ``"long"`` or ``"short"``.
        is_entry : bool
            ``True`` for entry fills, ``False`` for exit fills.

        Returns
        -------
        float
            Adjusted (worse) fill price.
        """
        slippage_pct = random.uniform(0.0001, 0.0005)  # 0.01 % -- 0.05 %

        # Determine adverse direction:
        #   Entry long  -> price goes UP   (pay more)
        #   Entry short -> price goes DOWN (sell cheaper)
        #   Exit long   -> price goes DOWN (receive less)
        #   Exit short  -> price goes UP   (buy back higher)
        if (direction == "long" and is_entry) or (direction == "short" and not is_entry):
            fill_price = price * (1 + slippage_pct)
        else:
            fill_price = price * (1 - slippage_pct)

        logger.debug(
            "Slippage applied: %.2f -> %.2f (%.4f%%, dir=%s, entry=%s)",
            price,
            fill_price,
            slippage_pct * 100,
            direction,
            is_entry,
        )
        return round(fill_price, 2)

    # =======================================================================
    #  Open a new position
    # =======================================================================

    def open_position(
        self,
        symbol: str,
        direction: str,
        entry_price: float,
        stop_loss: float,
        take_profit: float,
        quantity: float,
        position_size_usd: float,
        event_name: str,
        regime: str,
        agent_consensus: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Open a new paper position with realistic execution.

        Parameters
        ----------
        symbol : str
            Trading pair (e.g. ``"BTC/USDT"``).
        direction : str
            ``"long"`` or ``"short"``.
        entry_price : float
            Intended entry price before slippage.
        stop_loss : float
            Stop-loss level.
        take_profit : float
            Take-profit level.
        quantity : float
            Position quantity in base asset.
        position_size_usd : float
            Notional size in USDT.
        event_name : str
            Triggering event name (used for cooldown tracking).
        regime : str
            Market regime at entry.
        agent_consensus : dict, optional
            AI agent consensus snapshot.

        Returns
        -------
        dict
            The created trade record.
        """
        # Apply slippage on entry
        fill_price = self.apply_slippage(entry_price, direction, is_entry=True)

        # Recalculate quantity at the actual fill
        if fill_price > 0:
            quantity = round(position_size_usd / fill_price, 6)

        # Apply trading fee
        fee_pct = config.TRADING_FEE_PCT / 100.0
        entry_fee = position_size_usd * fee_pct

        # Build trade record
        trade_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()

        trade_record: Dict[str, Any] = {
            "id": trade_id,
            "symbol": symbol,
            "direction": direction,
            "entry_price": round(fill_price, 2),
            "intended_entry": round(entry_price, 2),
            "stop_loss": round(stop_loss, 2),
            "take_profit": round(take_profit, 2),
            "quantity": round(quantity, 6),
            "position_size_usd": round(position_size_usd, 2),
            "entry_fee": round(entry_fee, 4),
            "entry_time": now,
            "status": "open",
            "regime_at_entry": regime,
            "event_name": event_name,
            "agent_consensus": agent_consensus or {},
            "current_price": round(fill_price, 2),
            "unrealized_pnl": 0.0,
            "trailing_stop": None,
        }

        # Persist to Supabase
        try:
            self.data_store.insert_trade(trade_record)
        except Exception:
            logger.exception("Failed to persist trade %s to Supabase", trade_id)

        # Update in-memory portfolio
        self.portfolio["open_positions"].append(trade_record)
        self.portfolio["balance"] -= entry_fee  # deduct entry fee immediately

        # Persist portfolio update
        self._persist_portfolio()

        # Set cooldown for this event
        cooldown_until = datetime.now(timezone.utc) + timedelta(
            minutes=config.POST_EVENT_COOLDOWN_MINUTES
        )
        self.cooldowns[event_name] = cooldown_until

        logger.info(
            "OPENED %s %s @ %.2f (intended %.2f) | qty=%.6f | size=$%.2f | fee=$%.4f | SL=%.2f | TP=%.2f",
            direction.upper(),
            symbol,
            fill_price,
            entry_price,
            quantity,
            position_size_usd,
            entry_fee,
            stop_loss,
            take_profit,
        )

        return trade_record

    # =======================================================================
    #  Close an existing position
    # =======================================================================

    def close_position(
        self,
        trade_id: str,
        exit_price: float,
        reason: str,
    ) -> Dict[str, Any]:
        """Close an open paper position and calculate realised PnL.

        Parameters
        ----------
        trade_id : str
            UUID of the trade to close.
        exit_price : float
            Market price at time of close (before slippage).
        reason : str
            Reason for closing (e.g. ``"stop_loss"``, ``"take_profit"``,
            ``"trailing_stop"``, ``"manual"``).

        Returns
        -------
        dict
            Updated trade record including PnL and a ``trigger_post_analysis``
            flag indicating whether a post-trade review should run.
        """
        # Find the position in memory
        position = None
        position_idx = None
        for idx, pos in enumerate(self.portfolio["open_positions"]):
            if pos.get("id") == trade_id:
                position = pos
                position_idx = idx
                break

        if position is None:
            logger.warning("close_position: trade %s not found in open_positions", trade_id)
            return {"error": f"Trade {trade_id} not found"}

        direction = position["direction"]

        # Apply slippage on exit
        fill_price = self.apply_slippage(exit_price, direction, is_entry=False)

        # Apply trading fee
        position_size_usd = float(position.get("position_size_usd", 0))
        fee_pct = config.TRADING_FEE_PCT / 100.0
        exit_fee = position_size_usd * fee_pct

        # Calculate PnL
        entry_price = float(position["entry_price"])
        quantity = float(position["quantity"])
        entry_fee = float(position.get("entry_fee", 0))

        if direction == "long":
            raw_pnl = (fill_price - entry_price) * quantity
        else:
            raw_pnl = (entry_price - fill_price) * quantity

        net_pnl = raw_pnl - entry_fee - exit_fee
        pnl_pct = (net_pnl / position_size_usd) * 100.0 if position_size_usd > 0 else 0.0

        now = datetime.now(timezone.utc).isoformat()

        # Build closed-trade update
        trade_update: Dict[str, Any] = {
            "exit_price": round(fill_price, 2),
            "intended_exit": round(exit_price, 2),
            "exit_fee": round(exit_fee, 4),
            "exit_time": now,
            "status": "closed",
            "close_reason": reason,
            "pnl": round(net_pnl, 4),
            "pnl_pct": round(pnl_pct, 4),
            "raw_pnl": round(raw_pnl, 4),
            "total_fees": round(entry_fee + exit_fee, 4),
        }

        # Persist trade close to Supabase
        try:
            self.data_store.update_trade(trade_id, trade_update)
        except Exception:
            logger.exception("Failed to update trade %s in Supabase", trade_id)

        # Remove from open_positions
        self.portfolio["open_positions"].pop(position_idx)

        # Update portfolio balance / equity
        self.portfolio["balance"] += (position_size_usd + raw_pnl - exit_fee)
        self.portfolio["total_trades"] += 1

        if net_pnl >= 0:
            self.portfolio["winning_trades"] += 1
        else:
            self.portfolio["losing_trades"] += 1

        # Recompute equity (balance + unrealised from remaining positions)
        self._recompute_equity()

        # Track peak equity and max drawdown
        if self.portfolio["equity"] > self.portfolio["peak_equity"]:
            self.portfolio["peak_equity"] = self.portfolio["equity"]

        peak = self.portfolio["peak_equity"]
        if peak > 0:
            current_dd = ((peak - self.portfolio["equity"]) / peak) * 100.0
            if current_dd > self.portfolio["max_drawdown_pct"]:
                self.portfolio["max_drawdown_pct"] = round(current_dd, 2)

        # Append to local trade history (keep last 100)
        closed_record = {**position, **trade_update}
        closed_record["cumulative_equity"] = round(self.portfolio["equity"], 2)
        self.portfolio["trade_history"].append(closed_record)
        self.portfolio["trade_history"] = self.portfolio["trade_history"][-100:]

        # Persist portfolio
        self._persist_portfolio()

        logger.info(
            "CLOSED %s %s @ %.2f (intended %.2f) | PnL=$%.4f (%.2f%%) | reason=%s | balance=$%.2f",
            direction.upper(),
            position["symbol"],
            fill_price,
            exit_price,
            net_pnl,
            pnl_pct,
            reason,
            self.portfolio["balance"],
        )

        # Flag for post-trade analysis
        result = {**closed_record, "trigger_post_analysis": True}
        return result

    # =======================================================================
    #  Update all open positions (price checks, trailing, max-pain)
    # =======================================================================

    def update_positions(
        self,
        current_prices: Dict[str, float],
        atr_values: Dict[str, float],
        max_pain: Optional[float] = None,
        hours_to_expiry: Optional[float] = None,
    ) -> List[Dict[str, Any]]:
        """Tick-update every open position: prices, stops, and auto-closes.

        Parameters
        ----------
        current_prices : dict[str, float]
            Latest prices keyed by symbol.
        atr_values : dict[str, float]
            Latest ATR values keyed by symbol.
        max_pain : float, optional
            Current options max-pain level.
        hours_to_expiry : float, optional
            Hours until nearest major expiry.

        Returns
        -------
        list[dict]
            List of close results for any positions that were auto-closed.
        """
        close_results: List[Dict[str, Any]] = []

        # Iterate over a copy since close_position mutates the list
        positions_snapshot = list(self.portfolio["open_positions"])

        for position in positions_snapshot:
            symbol = position["symbol"]
            trade_id = position["id"]
            direction = position["direction"]
            entry_price = float(position["entry_price"])
            stop_loss = float(position["stop_loss"])
            take_profit = float(position["take_profit"])
            quantity = float(position["quantity"])

            current_price = current_prices.get(symbol)
            if current_price is None:
                continue

            current_price = float(current_price)

            # --- Update current price and unrealised PnL ---
            if direction == "long":
                unrealized_pnl = (current_price - entry_price) * quantity
            else:
                unrealized_pnl = (entry_price - current_price) * quantity

            # Update in-memory
            for pos in self.portfolio["open_positions"]:
                if pos["id"] == trade_id:
                    pos["current_price"] = round(current_price, 2)
                    pos["unrealized_pnl"] = round(unrealized_pnl, 4)
                    break

            # --- Check stop-loss hit ---
            stop_hit = False
            if direction == "long" and current_price <= stop_loss:
                stop_hit = True
            elif direction == "short" and current_price >= stop_loss:
                stop_hit = True

            if stop_hit:
                result = self.close_position(trade_id, current_price, "stop_loss")
                close_results.append(result)
                continue

            # --- Check take-profit hit ---
            tp_hit = False
            if direction == "long" and current_price >= take_profit:
                tp_hit = True
            elif direction == "short" and current_price <= take_profit:
                tp_hit = True

            if tp_hit:
                result = self.close_position(trade_id, current_price, "take_profit")
                close_results.append(result)
                continue

            # --- Update trailing stop ---
            atr = atr_values.get(symbol)
            regime = position.get("regime_at_entry", "NEUTRAL")
            if atr is not None:
                new_trailing = self.risk_engine.calculate_trailing_stop(
                    entry_price, current_price, float(atr), direction, regime
                )
                if new_trailing is not None:
                    current_trailing = position.get("trailing_stop")
                    # Only update if the trailing stop moves in the protective direction
                    update_trailing = False
                    if current_trailing is None:
                        update_trailing = True
                    elif direction == "long" and new_trailing > float(current_trailing):
                        update_trailing = True
                    elif direction == "short" and new_trailing < float(current_trailing):
                        update_trailing = True

                    if update_trailing:
                        for pos in self.portfolio["open_positions"]:
                            if pos["id"] == trade_id:
                                pos["trailing_stop"] = round(new_trailing, 2)
                                # Tighten actual stop to trailing stop
                                if direction == "long" and new_trailing > stop_loss:
                                    pos["stop_loss"] = round(new_trailing, 2)
                                elif direction == "short" and new_trailing < stop_loss:
                                    pos["stop_loss"] = round(new_trailing, 2)
                                break

                        logger.debug(
                            "Trailing stop updated for %s %s: %.2f",
                            symbol,
                            trade_id[:8],
                            new_trailing,
                        )

            # --- Check trailing stop hit (after update) ---
            for pos in self.portfolio["open_positions"]:
                if pos["id"] == trade_id:
                    updated_sl = float(pos["stop_loss"])
                    trailing_hit = False
                    if direction == "long" and current_price <= updated_sl:
                        trailing_hit = True
                    elif direction == "short" and current_price >= updated_sl:
                        trailing_hit = True

                    if trailing_hit:
                        result = self.close_position(trade_id, current_price, "trailing_stop")
                        close_results.append(result)
                    break

            # --- Max-pain gravity adjustment on take-profit ---
            if max_pain is not None and hours_to_expiry is not None:
                for pos in self.portfolio["open_positions"]:
                    if pos["id"] == trade_id:
                        current_tp = float(pos["take_profit"])
                        adjusted_tp = self.risk_engine.check_max_pain_gravity(
                            current_tp, max_pain, direction, hours_to_expiry
                        )
                        if adjusted_tp != current_tp:
                            pos["take_profit"] = round(adjusted_tp, 2)
                            logger.info(
                                "Max-pain adjusted TP for %s %s: %.2f -> %.2f",
                                symbol,
                                trade_id[:8],
                                current_tp,
                                adjusted_tp,
                            )
                        break

        # Recompute equity after all updates
        self._recompute_equity()

        # Persist updated portfolio if anything changed
        if positions_snapshot:
            self._persist_portfolio()

        return close_results

    # =======================================================================
    #  Cooldown management
    # =======================================================================

    def check_cooldown(self, event_name: str) -> bool:
        """Return ``True`` if a post-event cooldown is still active for *event_name*.

        Parameters
        ----------
        event_name : str
            The event identifier to check.

        Returns
        -------
        bool
            ``True`` when the event is still in cooldown (trading should wait),
            ``False`` when the cooldown has expired or was never set.
        """
        expires = self.cooldowns.get(event_name)
        if expires is None:
            return False

        now = datetime.now(timezone.utc)
        if now < expires:
            remaining = (expires - now).total_seconds() / 60.0
            logger.debug(
                "Cooldown active for '%s': %.1f min remaining",
                event_name,
                remaining,
            )
            return True

        # Cooldown expired -- clean up
        del self.cooldowns[event_name]
        return False

    # =======================================================================
    #  Portfolio summary
    # =======================================================================

    def get_portfolio_summary(self) -> Dict[str, Any]:
        """Return a comprehensive portfolio summary.

        Returns
        -------
        dict
            All portfolio metrics including balance, equity, PnL, win-rate,
            open positions, drawdown, and PFI score.
        """
        balance = self.portfolio["balance"]
        equity = self.portfolio["equity"]
        initial = self.portfolio["initial_balance"]
        total_trades = self.portfolio["total_trades"]
        winning = self.portfolio["winning_trades"]
        losing = self.portfolio["losing_trades"]
        max_dd = self.portfolio["max_drawdown_pct"]
        open_positions = self.portfolio["open_positions"]

        # Win rate
        win_rate = winning / total_trades if total_trades > 0 else 0.0

        # Total return
        total_return_pct = ((balance - initial) / initial) * 100.0 if initial > 0 else 0.0

        # Unrealised PnL
        unrealized_pnl = sum(float(p.get("unrealized_pnl", 0)) for p in open_positions)

        # Sharpe estimate from trade history
        sharpe = self._estimate_sharpe()

        # Portfolio Fitness Index
        pfi = self.risk_engine.calculate_pfi(
            balance, initial, total_trades, win_rate, max_dd, sharpe
        )

        return {
            "balance": round(balance, 2),
            "equity": round(equity, 2),
            "initial_balance": round(initial, 2),
            "total_return_pct": round(total_return_pct, 2),
            "unrealized_pnl": round(unrealized_pnl, 4),
            "total_trades": total_trades,
            "winning_trades": winning,
            "losing_trades": losing,
            "win_rate": round(win_rate, 4),
            "max_drawdown_pct": round(max_dd, 2),
            "peak_equity": round(self.portfolio["peak_equity"], 2),
            "open_positions_count": len(open_positions),
            "open_positions": open_positions,
            "sharpe_ratio": round(sharpe, 2),
            "pfi_score": pfi,
            "active_cooldowns": {
                k: v.isoformat() for k, v in self.cooldowns.items()
                if v > datetime.now(timezone.utc)
            },
        }

    # =======================================================================
    #  Internal helpers
    # =======================================================================

    def _recompute_equity(self) -> None:
        """Recompute portfolio equity = balance + sum(unrealised PnL)."""
        unrealized = sum(
            float(p.get("unrealized_pnl", 0))
            for p in self.portfolio["open_positions"]
        )
        self.portfolio["equity"] = round(self.portfolio["balance"] + unrealized, 2)

    def _persist_portfolio(self) -> None:
        """Persist the current in-memory portfolio state to Supabase."""
        try:
            self.data_store.update_portfolio({
                "balance": round(self.portfolio["balance"], 2),
                "equity": round(self.portfolio["equity"], 2),
                "initial_balance": round(self.portfolio["initial_balance"], 2),
                "open_positions": self.portfolio["open_positions"],
                "trade_history": self.portfolio["trade_history"][-50:],
                "total_trades": self.portfolio["total_trades"],
                "winning_trades": self.portfolio["winning_trades"],
                "losing_trades": self.portfolio["losing_trades"],
                "max_drawdown_pct": round(self.portfolio["max_drawdown_pct"], 2),
                "peak_equity": round(self.portfolio["peak_equity"], 2),
            })
        except Exception:
            logger.exception("Failed to persist portfolio to Supabase")

    def _estimate_sharpe(self, risk_free_rate: float = 0.0) -> float:
        """Estimate the Sharpe ratio from recent trade PnL percentages.

        Uses closed trade returns. Returns 0.0 if insufficient data.
        """
        trades = self.portfolio.get("trade_history", [])
        returns = []
        for t in trades:
            pnl_pct = t.get("pnl_pct")
            if pnl_pct is not None:
                returns.append(float(pnl_pct) / 100.0)

        if len(returns) < 3:
            return 0.0

        mean_return = sum(returns) / len(returns)
        std_return = (sum((r - mean_return) ** 2 for r in returns) / len(returns)) ** 0.5

        if std_return == 0:
            return 0.0

        sharpe = (mean_return - risk_free_rate) / std_return
        return round(sharpe, 4)
