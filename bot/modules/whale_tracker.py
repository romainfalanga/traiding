"""
Macro Pulse — Couche 8 : Whale Tracker.

Tracks large crypto whale movements via the Whale Alert API (free tier).
Classifies transactions by type (exchange inflow/outflow, transfers),
computes a Whale Flow Index, and detects pre-event correlation patterns.
"""

import sys
import os
import logging
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Tuple

import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

logger = logging.getLogger(__name__)

# ──────────────────────────── Constants ──────────────────────────────────
# Free tier: 10 requests per minute, data limited to the last 1 hour.
_RATE_LIMIT_MAX_REQUESTS = 10
_RATE_LIMIT_WINDOW_SECONDS = 60
_FREE_TIER_MAX_LOOKBACK_SECONDS = 3600  # 1 hour


class WhaleTracker:
    """Fetches and analyses large crypto whale transactions from Whale Alert."""

    # ------------------------------------------------------------------ init
    def __init__(self) -> None:
        self._session = requests.Session()
        self._session.headers.update({"Accept": "application/json"})

        # Rate-limiting state: timestamps of recent requests
        self._request_timestamps: List[float] = []

        # Cache for recent movements (avoids redundant API calls)
        self._cached_transactions: List[Dict] = []
        self._cache_timestamp: Optional[float] = None
        self._cache_ttl_seconds: float = 120.0  # 2-minute cache

        logger.info("WhaleTracker initialised (Whale Alert free tier).")

    # ================================================================== #
    #  Rate-limiting helper                                               #
    # ================================================================== #

    def _wait_for_rate_limit(self) -> None:
        """Block until we are allowed to make another request within the
        free-tier limit of 10 requests per 60 seconds."""
        now = time.monotonic()

        # Purge timestamps older than the window
        self._request_timestamps = [
            ts for ts in self._request_timestamps
            if now - ts < _RATE_LIMIT_WINDOW_SECONDS
        ]

        if len(self._request_timestamps) >= _RATE_LIMIT_MAX_REQUESTS:
            oldest = self._request_timestamps[0]
            wait = _RATE_LIMIT_WINDOW_SECONDS - (now - oldest) + 0.5
            if wait > 0:
                logger.debug(
                    "Rate-limiting Whale Alert — sleeping %.1fs (%d requests in window)",
                    wait,
                    len(self._request_timestamps),
                )
                time.sleep(wait)

        self._request_timestamps.append(time.monotonic())

    # ================================================================== #
    #  1. Fetch recent transactions                                       #
    # ================================================================== #

    def fetch_recent_transactions(self, min_usd: int = 1_000_000) -> List[Dict]:
        """Fetch whale transactions from the last hour via Whale Alert API.

        Parameters
        ----------
        min_usd : int
            Minimum transaction value in USD (default $1 M).

        Returns
        -------
        list[dict]
            Each dict matches the ``whale_movements`` table schema.
        """
        # Return cached data if still fresh
        if (
            self._cache_timestamp is not None
            and (time.monotonic() - self._cache_timestamp) < self._cache_ttl_seconds
            and self._cached_transactions
        ):
            logger.debug(
                "Returning %d cached transactions (cache age %.0fs)",
                len(self._cached_transactions),
                time.monotonic() - self._cache_timestamp,
            )
            return self._cached_transactions

        api_key = config.WHALE_ALERT_API_KEY
        if not api_key:
            logger.error(
                "WHALE_ALERT_API_KEY is not set — cannot fetch transactions."
            )
            return []

        now_utc = datetime.now(timezone.utc)
        start_ts = int((now_utc - timedelta(seconds=_FREE_TIER_MAX_LOOKBACK_SECONDS)).timestamp())

        url = (
            f"{config.WHALE_ALERT_BASE_URL}/transactions"
            f"?api_key={api_key}"
            f"&min_value={min_usd}"
            f"&start={start_ts}"
        )

        transactions: List[Dict] = []

        try:
            self._wait_for_rate_limit()

            resp = self._session.get(url, timeout=20)
            resp.raise_for_status()
            data = resp.json()

            if data.get("result") != "success":
                error_msg = data.get("message", "unknown error")
                logger.warning(
                    "Whale Alert API returned non-success: %s", error_msg
                )
                return []

            raw_txs = data.get("transactions", [])
            logger.info(
                "Whale Alert — fetched %d raw transactions (min_usd=%s)",
                len(raw_txs),
                f"${min_usd:,}",
            )

            for tx in raw_txs:
                parsed = self._parse_transaction(tx)
                if parsed is not None:
                    transactions.append(parsed)

        except requests.exceptions.HTTPError as exc:
            status_code = exc.response.status_code if exc.response is not None else None
            if status_code == 429:
                logger.warning(
                    "Whale Alert rate limit hit (HTTP 429). "
                    "Will retry on next call."
                )
            else:
                logger.error("Whale Alert HTTP error: %s", exc)
        except requests.RequestException as exc:
            logger.error("Whale Alert request failed: %s", exc)
        except (ValueError, KeyError, TypeError) as exc:
            logger.error("Whale Alert response parsing error: %s", exc)
        except Exception as exc:
            logger.error("Unexpected error in fetch_recent_transactions: %s", exc)

        # Update cache
        self._cached_transactions = transactions
        self._cache_timestamp = time.monotonic()

        logger.info(
            "Parsed %d whale transactions from the last hour.", len(transactions)
        )
        return transactions

    # ================================================================== #
    #  2. Whale Flow Index                                                #
    # ================================================================== #

    def calculate_whale_flow_index(self) -> float:
        """Compute a Whale Flow Index from recent transactions.

        The index measures the net direction of whale capital flow
        relative to exchanges:

        - **Positive** (+1): net outflow from exchanges (bullish — accumulation)
        - **Negative** (-1): net inflow to exchanges (bearish — selling pressure)
        - **Zero**: balanced or no data

        Returns
        -------
        float in [-1, 1]
        """
        transactions = self._cached_transactions or self.fetch_recent_transactions()

        if not transactions:
            logger.info("calculate_whale_flow_index — no transactions, returning 0.0")
            return 0.0

        outflow_usd = 0.0   # exchange -> external (bullish)
        inflow_usd = 0.0    # external -> exchange (bearish)
        total_volume = 0.0

        for tx in transactions:
            amount_usd = tx.get("amount_usd") or 0.0
            tx_type = tx.get("transaction_type", "")
            total_volume += amount_usd

            if tx_type == "exchange_outflow":
                outflow_usd += amount_usd
            elif tx_type == "exchange_inflow":
                inflow_usd += amount_usd

        if total_volume <= 0:
            return 0.0

        net_flow = outflow_usd - inflow_usd
        whale_flow_index = net_flow / total_volume

        # Clamp to [-1, 1]
        whale_flow_index = max(-1.0, min(1.0, whale_flow_index))

        label = "neutral"
        if whale_flow_index > 0.2:
            label = "BULLISH (net outflow from exchanges — accumulation)"
        elif whale_flow_index < -0.2:
            label = "BEARISH (net inflow to exchanges — selling pressure)"

        logger.info(
            "Whale Flow Index: %.4f [%s] — outflow=$%.2fM, inflow=$%.2fM, total=$%.2fM",
            whale_flow_index,
            label,
            outflow_usd / 1e6,
            inflow_usd / 1e6,
            total_volume / 1e6,
        )

        return round(whale_flow_index, 6)

    # ================================================================== #
    #  3. Pre-event correlation detection                                 #
    # ================================================================== #

    def detect_pre_event_correlation(
        self,
        event_time: datetime,
        lookback_hours: int = 2,
    ) -> Tuple[bool, float]:
        """Check whether whale activity increased significantly before a
        macro event.

        Compares the transaction count and volume in the *lookback_hours*
        period before *event_time* against the average activity level
        from the cached transactions.

        Parameters
        ----------
        event_time : datetime
            The UTC timestamp of the macro event.
        lookback_hours : int
            How many hours before the event to inspect (default 2).

        Returns
        -------
        tuple[bool, float]
            (unusual_activity, activity_vs_normal_ratio)
            - ``unusual_activity`` is True when the ratio >= 2.0 (i.e.
              activity at least double the norm).
            - ``activity_vs_normal_ratio`` expresses observed / expected.
        """
        transactions = self._cached_transactions or self.fetch_recent_transactions()

        if not transactions:
            logger.info("detect_pre_event_correlation — no transactions available")
            return False, 1.0

        # Ensure event_time is timezone-aware (UTC)
        if event_time.tzinfo is None:
            event_time = event_time.replace(tzinfo=timezone.utc)

        lookback_start = event_time - timedelta(hours=lookback_hours)

        # Partition transactions
        pre_event_txs: List[Dict] = []
        all_txs: List[Dict] = []

        for tx in transactions:
            try:
                tx_time = datetime.fromisoformat(tx["timestamp"])
                if tx_time.tzinfo is None:
                    tx_time = tx_time.replace(tzinfo=timezone.utc)
            except (ValueError, KeyError):
                continue

            all_txs.append(tx)
            if lookback_start <= tx_time <= event_time:
                pre_event_txs.append(tx)

        if not all_txs:
            return False, 1.0

        # Average volume and count across the full cached window (1 hour)
        total_count = len(all_txs)
        total_volume = sum(tx.get("amount_usd", 0) for tx in all_txs)

        # Expected activity in the lookback window proportional to window size
        # Cached data covers ~1 hour; lookback is `lookback_hours` hours.
        # Scale the average to match the lookback duration.
        window_fraction = min(lookback_hours, 1.0)  # free tier caps at 1h of data
        expected_count = max(total_count * window_fraction, 1)
        expected_volume = max(total_volume * window_fraction, 1.0)

        pre_event_count = len(pre_event_txs)
        pre_event_volume = sum(tx.get("amount_usd", 0) for tx in pre_event_txs)

        # Ratio blends count and volume ratios (equal weight)
        count_ratio = pre_event_count / expected_count if expected_count > 0 else 1.0
        volume_ratio = pre_event_volume / expected_volume if expected_volume > 0 else 1.0
        activity_ratio = round((count_ratio + volume_ratio) / 2.0, 4)

        unusual = activity_ratio >= 2.0

        logger.info(
            "Pre-event correlation — event=%s, lookback=%dh, "
            "pre_event_txs=%d (expected ~%.1f), volume=$%.2fM (expected ~$%.2fM), "
            "ratio=%.2f, unusual=%s",
            event_time.isoformat(),
            lookback_hours,
            pre_event_count,
            expected_count,
            pre_event_volume / 1e6,
            expected_volume / 1e6,
            activity_ratio,
            unusual,
        )

        return unusual, activity_ratio

    # ================================================================== #
    #  4. Significant movements filter                                    #
    # ================================================================== #

    def get_significant_movements(self, min_usd: int = 5_000_000) -> List[Dict]:
        """Return only the really large whale movements, sorted by value
        descending.

        Parameters
        ----------
        min_usd : int
            Minimum transaction value in USD (default $5 M).

        Returns
        -------
        list[dict]
            Filtered and sorted list of transaction dicts.
        """
        transactions = self._cached_transactions or self.fetch_recent_transactions()

        significant = [
            tx for tx in transactions
            if (tx.get("amount_usd") or 0) >= min_usd
        ]

        significant.sort(key=lambda tx: tx.get("amount_usd", 0), reverse=True)

        logger.info(
            "Significant movements (>=$%sM): %d of %d total transactions",
            min_usd / 1e6,
            len(significant),
            len(transactions),
        )

        return significant

    # ================================================================== #
    #  5. Aggregated fetch — main entry point                             #
    # ================================================================== #

    def fetch_all(self) -> Dict:
        """Main entry point — fetches all whale data and computes derived
        metrics.

        Returns
        -------
        dict with keys:
            transactions, whale_flow_index, significant_movements,
            total_inflow_usd, total_outflow_usd, net_flow_usd,
            transaction_count, timestamp
        """
        logger.info("fetch_all — starting full whale scan")

        # 1. Fetch recent transactions (populates cache)
        transactions = self.fetch_recent_transactions(
            min_usd=config.WHALE_MIN_USD,
        )

        # 2. Whale Flow Index
        whale_flow_index = self.calculate_whale_flow_index()

        # 3. Significant movements
        significant = self.get_significant_movements(min_usd=5_000_000)

        # 4. Aggregate USD flows
        total_inflow_usd = 0.0
        total_outflow_usd = 0.0

        for tx in transactions:
            amount_usd = tx.get("amount_usd") or 0.0
            tx_type = tx.get("transaction_type", "")

            if tx_type == "exchange_inflow":
                total_inflow_usd += amount_usd
            elif tx_type == "exchange_outflow":
                total_outflow_usd += amount_usd

        net_flow_usd = total_outflow_usd - total_inflow_usd

        record = {
            "transactions": transactions,
            "whale_flow_index": whale_flow_index,
            "significant_movements": significant,
            "total_inflow_usd": round(total_inflow_usd, 2),
            "total_outflow_usd": round(total_outflow_usd, 2),
            "net_flow_usd": round(net_flow_usd, 2),
            "transaction_count": len(transactions),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        logger.info(
            "fetch_all — complete: %d txs, flow_index=%.4f, "
            "inflow=$%.2fM, outflow=$%.2fM, net=$%.2fM, significant=%d",
            record["transaction_count"],
            whale_flow_index,
            total_inflow_usd / 1e6,
            total_outflow_usd / 1e6,
            net_flow_usd / 1e6,
            len(significant),
        )

        return record

    # ================================================================== #
    #  Private helpers                                                    #
    # ================================================================== #

    @staticmethod
    def _classify_transaction_type(from_owner_type: str, to_owner_type: str) -> str:
        """Classify a transaction based on the owner types of the sender
        and recipient.

        Classification logic:
            - exchange -> exchange : "exchange_to_exchange"
            - * -> exchange       : "exchange_inflow" (bearish — selling)
            - exchange -> *       : "exchange_outflow" (bullish — accumulation)
            - unknown -> unknown  : "unknown_to_unknown"
        """
        from_is_exchange = from_owner_type == "exchange"
        to_is_exchange = to_owner_type == "exchange"

        if from_is_exchange and to_is_exchange:
            return "exchange_to_exchange"
        elif to_is_exchange:
            return "exchange_inflow"
        elif from_is_exchange:
            return "exchange_outflow"
        else:
            return "unknown_to_unknown"

    @staticmethod
    def _safe_owner(side: dict) -> Tuple[str, str]:
        """Extract (owner_type, owner) from a transaction side dict.

        Returns ("unknown", "unknown") if fields are missing.
        """
        owner_type = str(side.get("owner_type", "unknown")).lower().strip()
        owner = str(side.get("owner", "unknown")).strip()

        if not owner_type:
            owner_type = "unknown"
        if not owner:
            owner = "unknown"

        return owner_type, owner

    def _parse_transaction(self, raw_tx: dict) -> Optional[Dict]:
        """Parse a single raw Whale Alert transaction into the
        ``whale_movements`` table schema.

        Returns None if the transaction cannot be parsed.
        """
        try:
            blockchain = str(raw_tx.get("blockchain", "unknown"))
            symbol = str(raw_tx.get("symbol", "unknown")).upper()
            tx_hash = str(raw_tx.get("hash", ""))
            amount = float(raw_tx.get("amount", 0))
            amount_usd = float(raw_tx.get("amount_usd", 0))

            # Timestamp: Whale Alert returns Unix epoch
            raw_ts = raw_tx.get("timestamp")
            if raw_ts is not None:
                tx_time = datetime.fromtimestamp(int(raw_ts), tz=timezone.utc)
            else:
                tx_time = datetime.now(timezone.utc)

            # From / To sides
            from_side = raw_tx.get("from", {}) or {}
            to_side = raw_tx.get("to", {}) or {}

            from_owner_type, from_owner = self._safe_owner(from_side)
            to_owner_type, to_owner = self._safe_owner(to_side)

            transaction_type = self._classify_transaction_type(
                from_owner_type, to_owner_type
            )

            return {
                "blockchain": blockchain,
                "symbol": symbol,
                "tx_hash": tx_hash,
                "from_owner": f"{from_owner_type}:{from_owner}",
                "to_owner": f"{to_owner_type}:{to_owner}",
                "amount": amount,
                "amount_usd": round(amount_usd, 2),
                "transaction_type": transaction_type,
                "whale_flow_index": None,  # populated later at aggregate level
                "timestamp": tx_time.isoformat(),
            }

        except (ValueError, TypeError, KeyError) as exc:
            logger.debug("Skipping unparseable transaction: %s — %s", exc, raw_tx)
            return None


# ──────────────────────────── CLI quick-test ─────────────────────────────
if __name__ == "__main__":
    logging.basicConfig(
        level=getattr(logging, config.LOG_LEVEL, logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    )
    tracker = WhaleTracker()

    print("\n=== Recent Transactions ===")
    txs = tracker.fetch_recent_transactions()
    print(f"  Total: {len(txs)}")
    for tx in txs[:5]:
        print(
            f"  [{tx['blockchain']}] {tx['symbol']} "
            f"${tx['amount_usd']:,.0f} — {tx['transaction_type']} "
            f"({tx['from_owner']} -> {tx['to_owner']})"
        )
    if len(txs) > 5:
        print(f"  ... and {len(txs) - 5} more")

    print("\n=== Whale Flow Index ===")
    wfi = tracker.calculate_whale_flow_index()
    print(f"  Index: {wfi}")

    print("\n=== Significant Movements (>$5M) ===")
    big = tracker.get_significant_movements()
    print(f"  Count: {len(big)}")
    for tx in big[:5]:
        print(
            f"  [{tx['blockchain']}] {tx['symbol']} "
            f"${tx['amount_usd']:,.0f} — {tx['transaction_type']}"
        )

    print("\n=== Pre-event Correlation (example: now) ===")
    unusual, ratio = tracker.detect_pre_event_correlation(
        datetime.now(timezone.utc)
    )
    print(f"  Unusual: {unusual}, Ratio: {ratio}")

    print("\n=== Full Scan (fetch_all) ===")
    full = tracker.fetch_all()
    for k, v in full.items():
        if k == "transactions":
            print(f"  {k}: [{len(v)} transactions]")
        elif k == "significant_movements":
            print(f"  {k}: [{len(v)} movements]")
        else:
            print(f"  {k}: {v}")
