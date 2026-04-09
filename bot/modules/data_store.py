"""
Macro Pulse — DataStore
Supabase interface for all database operations.
Provides insert / query / update methods for every table used by the trading bot.
"""

import logging
import sys
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Config import — works both as package import and standalone execution
# ---------------------------------------------------------------------------
try:
    from .. import config
except ImportError:
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    import config

from supabase import create_client, Client

logger = logging.getLogger(__name__)


class DataStore:
    """Centralised Supabase persistence layer for Macro Pulse."""

    # ------------------------------------------------------------------ init
    def __init__(self) -> None:
        url: str = config.SUPABASE_URL
        key: str = config.SUPABASE_SERVICE_KEY

        if not url or not key:
            logger.error("SUPABASE_URL or SUPABASE_SERVICE_KEY is missing — DataStore will not work")
        self.client: Client = create_client(url, key)
        logger.info("DataStore initialised (Supabase client ready)")

    # =======================================================================
    #  Generic helpers
    # =======================================================================

    def _insert(self, table: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Insert a single row into *table* and return the inserted record."""
        try:
            response = self.client.table(table).insert(data).execute()
            logger.debug("Inserted row into '%s'", table)
            return response.data[0] if response.data else {}
        except Exception:
            logger.exception("Failed to insert into '%s'", table)
            raise

    def _get_latest(self, table: str, order_col: str = "timestamp", limit: int = 1) -> Optional[Dict[str, Any]]:
        """Return the most recent row(s) from *table* ordered by *order_col* desc."""
        try:
            response = (
                self.client.table(table)
                .select("*")
                .order(order_col, desc=True)
                .limit(limit)
                .execute()
            )
            if not response.data:
                return None
            return response.data[0] if limit == 1 else response.data
        except Exception:
            logger.exception("Failed to fetch latest from '%s'", table)
            raise

    # =======================================================================
    #  1. macro_events
    # =======================================================================

    def insert_macro_event(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Insert a macro economic event."""
        return self._insert("macro_events", data)

    def get_recent_events(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Return macro events from the last *hours* hours."""
        try:
            cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
            response = (
                self.client.table("macro_events")
                .select("*")
                .gte("timestamp", cutoff)
                .order("timestamp", desc=True)
                .execute()
            )
            return response.data or []
        except Exception:
            logger.exception("Failed to fetch recent macro events")
            raise

    # =======================================================================
    #  2. tradfi_context
    # =======================================================================

    def insert_tradfi_context(self, data: Dict[str, Any]) -> Dict[str, Any]:
        return self._insert("tradfi_context", data)

    def get_latest_tradfi_context(self) -> Optional[Dict[str, Any]]:
        return self._get_latest("tradfi_context")

    # =======================================================================
    #  3. market_continuous
    # =======================================================================

    def insert_market_continuous(self, data: Dict[str, Any]) -> Dict[str, Any]:
        return self._insert("market_continuous", data)

    def get_latest_market_continuous(self, symbol: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Return the latest market_continuous row, optionally filtered by symbol."""
        try:
            query = self.client.table("market_continuous").select("*")
            if symbol:
                query = query.eq("symbol", symbol)
            response = query.order("timestamp", desc=True).limit(1).execute()
            return response.data[0] if response.data else None
        except Exception:
            logger.exception("Failed to fetch latest market_continuous")
            raise

    # =======================================================================
    #  4. technical_snapshots
    # =======================================================================

    def insert_technical_snapshot(self, data: Dict[str, Any]) -> Dict[str, Any]:
        return self._insert("technical_snapshots", data)

    def get_latest_technical_snapshot(self, symbol: str, timeframe: str) -> Optional[Dict[str, Any]]:
        """Return the newest technical snapshot for a given symbol + timeframe."""
        try:
            response = (
                self.client.table("technical_snapshots")
                .select("*")
                .eq("symbol", symbol)
                .eq("timeframe", timeframe)
                .order("timestamp", desc=True)
                .limit(1)
                .execute()
            )
            return response.data[0] if response.data else None
        except Exception:
            logger.exception("Failed to fetch latest technical_snapshot for %s %s", symbol, timeframe)
            raise

    # =======================================================================
    #  5. defi_flows
    # =======================================================================

    def insert_defi_flows(self, data: Dict[str, Any]) -> Dict[str, Any]:
        return self._insert("defi_flows", data)

    def get_latest_defi_flows(self) -> Optional[Dict[str, Any]]:
        return self._get_latest("defi_flows")

    # =======================================================================
    #  6. options_data
    # =======================================================================

    def insert_options_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        return self._insert("options_data", data)

    def get_latest_options_data(self) -> Optional[Dict[str, Any]]:
        return self._get_latest("options_data")

    # =======================================================================
    #  7. sentiment_snapshots
    # =======================================================================

    def insert_sentiment_snapshot(self, data: Dict[str, Any]) -> Dict[str, Any]:
        return self._insert("sentiment_snapshots", data)

    def get_latest_sentiment_snapshot(self, source: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Return the latest sentiment snapshot, optionally filtered by source."""
        try:
            query = self.client.table("sentiment_snapshots").select("*")
            if source:
                query = query.eq("source", source)
            response = query.order("timestamp", desc=True).limit(1).execute()
            return response.data[0] if response.data else None
        except Exception:
            logger.exception("Failed to fetch latest sentiment_snapshot")
            raise

    # =======================================================================
    #  8. whale_movements
    # =======================================================================

    def insert_whale_movement(self, data: Dict[str, Any]) -> Dict[str, Any]:
        return self._insert("whale_movements", data)

    def get_recent_whale_movements(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Return whale movements from the last *hours* hours."""
        try:
            cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
            response = (
                self.client.table("whale_movements")
                .select("*")
                .gte("timestamp", cutoff)
                .order("timestamp", desc=True)
                .execute()
            )
            return response.data or []
        except Exception:
            logger.exception("Failed to fetch recent whale movements")
            raise

    # =======================================================================
    #  9. regime_history
    # =======================================================================

    def insert_regime_history(self, data: Dict[str, Any]) -> Dict[str, Any]:
        return self._insert("regime_history", data)

    def get_latest_regime_history(self) -> Optional[Dict[str, Any]]:
        return self._get_latest("regime_history")

    def get_regime_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Return the last *limit* regime entries."""
        try:
            response = (
                self.client.table("regime_history")
                .select("*")
                .order("timestamp", desc=True)
                .limit(limit)
                .execute()
            )
            return response.data or []
        except Exception:
            logger.exception("Failed to fetch regime history")
            raise

    # =======================================================================
    #  10. ai_decisions
    # =======================================================================

    def insert_ai_decision(self, data: Dict[str, Any]) -> Dict[str, Any]:
        return self._insert("ai_decisions", data)

    def get_ai_decisions(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Return the most recent AI decisions."""
        try:
            response = (
                self.client.table("ai_decisions")
                .select("*")
                .order("created_at", desc=True)
                .limit(limit)
                .execute()
            )
            return response.data or []
        except Exception:
            logger.exception("Failed to fetch AI decisions")
            raise

    def get_agent_calibration_data(self, agent_num: int) -> List[Dict[str, Any]]:
        """Return historical confidence/impact data for a specific agent (1-3).

        Useful for calibrating agent confidence scores over time.
        Returns rows with agent-specific columns plus vote_result context.
        """
        if agent_num not in (1, 2, 3):
            raise ValueError(f"agent_num must be 1, 2 or 3 — got {agent_num}")

        columns = (
            f"id, "
            f"agent_{agent_num}_model, "
            f"agent_{agent_num}_response, "
            f"agent_{agent_num}_impact, "
            f"agent_{agent_num}_confidence, "
            f"agent_{agent_num}_confidence_calibrated, "
            f"vote_result, consensus_direction, created_at"
        )
        if agent_num == 3:
            columns += f", agent_{agent_num}_contrarian_risk"

        try:
            response = (
                self.client.table("ai_decisions")
                .select(columns)
                .order("created_at", desc=True)
                .limit(200)
                .execute()
            )
            return response.data or []
        except Exception:
            logger.exception("Failed to fetch calibration data for agent %d", agent_num)
            raise

    # =======================================================================
    #  11. portfolio
    # =======================================================================

    def insert_portfolio(self, data: Dict[str, Any]) -> Dict[str, Any]:
        return self._insert("portfolio", data)

    def get_latest_portfolio(self) -> Optional[Dict[str, Any]]:
        return self._get_latest("portfolio", order_col="updated_at")

    def update_portfolio(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Upsert the single portfolio row.

        If a row already exists it is updated; otherwise a new row is created.
        The caller should include all fields that need refreshing — ``updated_at``
        is set automatically to *now* if not provided.
        """
        if "updated_at" not in data:
            data["updated_at"] = datetime.now(timezone.utc).isoformat()
        try:
            existing = self.get_latest_portfolio()
            if existing:
                response = (
                    self.client.table("portfolio")
                    .update(data)
                    .eq("id", existing["id"])
                    .execute()
                )
                logger.debug("Updated portfolio row %s", existing["id"])
            else:
                response = self.client.table("portfolio").insert(data).execute()
                logger.info("Created initial portfolio row")
            return response.data[0] if response.data else {}
        except Exception:
            logger.exception("Failed to update portfolio")
            raise

    # =======================================================================
    #  12. trades
    # =======================================================================

    def insert_trade(self, data: Dict[str, Any]) -> Dict[str, Any]:
        return self._insert("trades", data)

    def get_open_trades(self) -> List[Dict[str, Any]]:
        """Return all trades with status = 'open'."""
        try:
            response = (
                self.client.table("trades")
                .select("*")
                .eq("status", "open")
                .order("entry_time", desc=True)
                .execute()
            )
            return response.data or []
        except Exception:
            logger.exception("Failed to fetch open trades")
            raise

    def get_closed_trades(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Return the most recent closed trades."""
        try:
            response = (
                self.client.table("trades")
                .select("*")
                .eq("status", "closed")
                .order("exit_time", desc=True)
                .limit(limit)
                .execute()
            )
            return response.data or []
        except Exception:
            logger.exception("Failed to fetch closed trades")
            raise

    def get_trade_by_id(self, trade_id: str) -> Optional[Dict[str, Any]]:
        """Return a single trade by its id."""
        try:
            response = (
                self.client.table("trades")
                .select("*")
                .eq("id", trade_id)
                .limit(1)
                .execute()
            )
            return response.data[0] if response.data else None
        except Exception:
            logger.exception("Failed to fetch trade %s", trade_id)
            raise

    def update_trade(self, trade_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update an existing trade row (e.g. to close it or adjust SL/TP)."""
        try:
            response = (
                self.client.table("trades")
                .update(data)
                .eq("id", trade_id)
                .execute()
            )
            logger.debug("Updated trade %s", trade_id)
            return response.data[0] if response.data else {}
        except Exception:
            logger.exception("Failed to update trade %s", trade_id)
            raise

    # =======================================================================
    #  13. post_trade_analyses
    # =======================================================================

    def insert_post_trade_analysis(self, data: Dict[str, Any]) -> Dict[str, Any]:
        return self._insert("post_trade_analyses", data)

    def get_post_trade_analyses(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Return the most recent post-trade analyses."""
        try:
            response = (
                self.client.table("post_trade_analyses")
                .select("*")
                .order("created_at", desc=True)
                .limit(limit)
                .execute()
            )
            return response.data or []
        except Exception:
            logger.exception("Failed to fetch post-trade analyses")
            raise

    # =======================================================================
    #  14. backtest_results
    # =======================================================================

    def insert_backtest_result(self, data: Dict[str, Any]) -> Dict[str, Any]:
        return self._insert("backtest_results", data)

    def get_backtest_results(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Return the most recent backtest results."""
        try:
            response = (
                self.client.table("backtest_results")
                .select("*")
                .order("created_at", desc=True)
                .limit(limit)
                .execute()
            )
            return response.data or []
        except Exception:
            logger.exception("Failed to fetch backtest results")
            raise

    # =======================================================================
    #  15. bot_settings
    # =======================================================================

    def insert_bot_setting(self, data: Dict[str, Any]) -> Dict[str, Any]:
        return self._insert("bot_settings", data)

    def get_setting(self, key: str) -> Optional[Any]:
        """Return the JSON value for a given settings key, or None if not found."""
        try:
            response = (
                self.client.table("bot_settings")
                .select("value")
                .eq("key", key)
                .limit(1)
                .execute()
            )
            if response.data:
                return response.data[0].get("value")
            return None
        except Exception:
            logger.exception("Failed to fetch setting '%s'", key)
            raise

    def upsert_setting(self, key: str, value: Any) -> Dict[str, Any]:
        """Insert or update a bot setting.

        Uses Supabase upsert with ``key`` as the conflict column so that
        duplicate keys are updated rather than rejected.
        """
        payload = {
            "key": key,
            "value": value,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        try:
            response = (
                self.client.table("bot_settings")
                .upsert(payload, on_conflict="key")
                .execute()
            )
            logger.debug("Upserted setting '%s'", key)
            return response.data[0] if response.data else {}
        except Exception:
            logger.exception("Failed to upsert setting '%s'", key)
            raise
