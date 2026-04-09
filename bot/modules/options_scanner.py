"""
Macro Pulse — Couche 6 : Options Scanner.

Captures options market data from the Deribit public API (no authentication
required).  Provides DVOL (implied-vol index), max-pain calculations,
put/call ratios, and volatility term-structure analysis for BTC and ETH.
"""

import sys
import os
import logging
import json
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
#  Deribit public base URL (from config)
# ---------------------------------------------------------------------------
DERIBIT_BASE_URL = config.DERIBIT_BASE_URL  # https://www.deribit.com/api/v2

REQUEST_TIMEOUT = 30  # seconds — Deribit can be slow


class OptionsScanner:
    """Fetches and analyses options data from the Deribit public API."""

    def __init__(self) -> None:
        self._session = requests.Session()
        self._session.headers.update({"Accept": "application/json"})
        # Cache book summaries so we don't fetch twice (max_pain + put/call)
        self._book_summary_cache: Dict[str, List[dict]] = {}
        logger.info("OptionsScanner initialised (Deribit public API).")

    # ===================================================================== #
    #  Internal helpers                                                      #
    # ===================================================================== #

    def _get(self, path: str, params: Optional[dict] = None) -> Optional[dict]:
        """Fire a GET request against the Deribit public API.

        Returns the parsed JSON *result* field, or None on any failure.
        """
        url = f"{DERIBIT_BASE_URL}{path}"
        try:
            resp = self._session.get(url, params=params, timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()
            data = resp.json()
            if "result" in data:
                return data["result"]
            logger.warning("Deribit response missing 'result' key for %s: %s", path, data)
            return None
        except requests.Timeout:
            logger.error("Deribit request timed out: %s", path)
            return None
        except requests.RequestException as exc:
            logger.error("Deribit request error for %s: %s", path, exc)
            return None
        except (ValueError, KeyError) as exc:
            logger.error("Deribit response parse error for %s: %s", path, exc)
            return None

    @staticmethod
    def _now_ms() -> int:
        """Current UTC time in milliseconds."""
        return int(datetime.now(timezone.utc).timestamp() * 1000)

    @staticmethod
    def _ms_ago(hours: float = 0, days: float = 0) -> int:
        """UTC timestamp in ms for a point in the past."""
        delta = timedelta(hours=hours, days=days)
        return int((datetime.now(timezone.utc) - delta).timestamp() * 1000)

    def _get_spot_price(self, currency: str = "BTC") -> Optional[float]:
        """Fetch the current index (spot) price for *currency*."""
        result = self._get("/public/get_index_price", params={"index_name": f"{currency.lower()}_usd"})
        if result and "index_price" in result:
            return float(result["index_price"])
        return None

    def _fetch_book_summary(self, currency: str = "BTC") -> List[dict]:
        """Fetch option book summaries, with per-currency caching."""
        cache_key = currency.upper()
        if cache_key in self._book_summary_cache:
            return self._book_summary_cache[cache_key]

        result = self._get(
            "/public/get_book_summary_by_currency",
            params={"currency": currency.upper(), "kind": "option"},
        )
        instruments = result if isinstance(result, list) else []
        self._book_summary_cache[cache_key] = instruments
        logger.info(
            "Fetched %d option book summaries for %s",
            len(instruments), currency.upper(),
        )
        return instruments

    # ===================================================================== #
    #  DVOL (Deribit Volatility Index)                                       #
    # ===================================================================== #

    def fetch_dvol(self, currency: str = "BTC") -> Dict[str, Any]:
        """Fetch the current DVOL value and its 24 h change.

        Returns
        -------
        dict  {"dvol": float|None, "dvol_change_24h": float|None,
               "history": list[float]}
        """
        out: Dict[str, Any] = {"dvol": None, "dvol_change_24h": None, "history": []}

        try:
            now_ms = self._now_ms()
            start_ms = self._ms_ago(hours=24)

            result = self._get(
                "/public/get_volatility_index_data",
                params={
                    "currency": currency.upper(),
                    "resolution": 3600,              # 1-hour candles
                    "start_timestamp": start_ms,
                    "end_timestamp": now_ms,
                },
            )

            if not result:
                logger.warning("No DVOL data returned for %s", currency)
                return out

            # result.data is a list of [timestamp, open, high, low, close]
            data_points = result.get("data", [])
            if not data_points:
                logger.warning("DVOL data array empty for %s", currency)
                return out

            # Extract close values (index 4)
            closes = [float(p[4]) for p in data_points if p and len(p) >= 5]
            if not closes:
                return out

            current_dvol = closes[-1]
            first_dvol = closes[0]

            out["dvol"] = round(current_dvol, 2)
            out["dvol_change_24h"] = round(current_dvol - first_dvol, 2)
            out["history"] = closes

            logger.info(
                "DVOL %s: %.2f (24h change: %+.2f)",
                currency, current_dvol, out["dvol_change_24h"],
            )

        except Exception as exc:
            logger.error("fetch_dvol error for %s: %s", currency, exc)

        return out

    # ===================================================================== #
    #  DVOL 90-day percentile                                                #
    # ===================================================================== #

    def calculate_dvol_percentile_90d(self, currency: str = "BTC") -> Optional[float]:
        """Percentile of current DVOL within its 90-day range.

        Uses daily resolution (86 400 000 ms) for the 90-day lookback.
        Returns a float 0-100 or None on failure.
        """
        try:
            now_ms = self._now_ms()
            start_ms = self._ms_ago(days=90)

            result = self._get(
                "/public/get_volatility_index_data",
                params={
                    "currency": currency.upper(),
                    "resolution": 86400000,          # daily
                    "start_timestamp": start_ms,
                    "end_timestamp": now_ms,
                },
            )

            if not result:
                logger.warning("No 90d DVOL data for %s", currency)
                return None

            data_points = result.get("data", [])
            if not data_points:
                return None

            closes = [float(p[4]) for p in data_points if p and len(p) >= 5]
            if len(closes) < 2:
                return None

            current_dvol = closes[-1]
            percentile = float(np.percentile(closes, 0))  # will be overridden
            # Compute the percentile rank of current_dvol
            arr = np.array(closes)
            percentile_rank = float(np.sum(arr < current_dvol) / len(arr) * 100)
            percentile_rank = round(percentile_rank, 2)

            logger.info(
                "DVOL 90d percentile for %s: %.2f (current=%.2f, n=%d days)",
                currency, percentile_rank, current_dvol, len(closes),
            )
            return percentile_rank

        except Exception as exc:
            logger.error("calculate_dvol_percentile_90d error for %s: %s", currency, exc)
            return None

    # ===================================================================== #
    #  Max Pain                                                              #
    # ===================================================================== #

    def _parse_instrument_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Parse a Deribit instrument name like ``BTC-28MAR25-90000-C``.

        Returns dict with keys: currency, expiry_str, strike, option_type
        or None if the name is not a standard option.
        """
        try:
            parts = name.split("-")
            if len(parts) != 4:
                return None
            return {
                "currency": parts[0],
                "expiry_str": parts[1],
                "strike": float(parts[2]),
                "option_type": parts[3].upper(),  # "C" or "P"
            }
        except (ValueError, IndexError):
            return None

    def _parse_expiry_str(self, expiry_str: str) -> Optional[datetime]:
        """Convert Deribit expiry string (e.g. ``28MAR25``) to datetime."""
        try:
            return datetime.strptime(expiry_str, "%d%b%y").replace(tzinfo=timezone.utc)
        except ValueError:
            return None

    def calculate_max_pain(self, currency: str = "BTC") -> Dict[str, Any]:
        """Calculate the max-pain strike for the nearest expiry.

        Returns
        -------
        dict  {"max_pain": float|None, "distance_pct": float|None,
               "expiry_date": str|None, "total_oi_usd": float|None}
        """
        out: Dict[str, Any] = {
            "max_pain": None,
            "distance_pct": None,
            "expiry_date": None,
            "total_oi_usd": None,
        }

        try:
            instruments = self._fetch_book_summary(currency)
            if not instruments:
                logger.warning("No option instruments for %s — cannot compute max pain", currency)
                return out

            spot_price = self._get_spot_price(currency)
            if spot_price is None:
                logger.warning("Cannot fetch spot price for %s", currency)
                return out

            # ── Group options by expiry ──────────────────────────────
            # Structure: {expiry_str: {"calls": {strike: OI}, "puts": {strike: OI}}}
            expiry_map: Dict[str, Dict[str, Dict[float, float]]] = {}

            for inst in instruments:
                name = inst.get("instrument_name", "")
                parsed = self._parse_instrument_name(name)
                if parsed is None:
                    continue

                expiry_str = parsed["expiry_str"]
                strike = parsed["strike"]
                opt_type = parsed["option_type"]
                oi = float(inst.get("open_interest", 0))

                if expiry_str not in expiry_map:
                    expiry_map[expiry_str] = {"calls": {}, "puts": {}}

                bucket = "calls" if opt_type == "C" else "puts"
                expiry_map[expiry_str][bucket][strike] = (
                    expiry_map[expiry_str][bucket].get(strike, 0.0) + oi
                )

            if not expiry_map:
                logger.warning("No parseable option instruments for %s", currency)
                return out

            # ── Find the nearest future expiry ───────────────────────
            now = datetime.now(timezone.utc)
            nearest_expiry_str: Optional[str] = None
            nearest_expiry_dt: Optional[datetime] = None

            for exp_str in expiry_map:
                exp_dt = self._parse_expiry_str(exp_str)
                if exp_dt is None:
                    continue
                if exp_dt <= now:
                    continue  # skip expired
                if nearest_expiry_dt is None or exp_dt < nearest_expiry_dt:
                    nearest_expiry_dt = exp_dt
                    nearest_expiry_str = exp_str

            if nearest_expiry_str is None:
                logger.warning("No future expiry found for %s", currency)
                return out

            calls = expiry_map[nearest_expiry_str]["calls"]
            puts = expiry_map[nearest_expiry_str]["puts"]

            # Gather all unique strikes across calls and puts
            all_strikes = sorted(set(list(calls.keys()) + list(puts.keys())))

            if not all_strikes:
                return out

            # ── Compute total pain at each possible settlement price ──
            min_pain = float("inf")
            max_pain_strike = all_strikes[0]

            for settlement in all_strikes:
                total_pain = 0.0
                # Call holders lose max(0, settlement - strike) * OI
                for strike, oi in calls.items():
                    total_pain += max(0.0, settlement - strike) * oi
                # Put holders lose max(0, strike - settlement) * OI
                for strike, oi in puts.items():
                    total_pain += max(0.0, strike - settlement) * oi

                if total_pain < min_pain:
                    min_pain = total_pain
                    max_pain_strike = settlement

            # ── Distance from spot price ──────────────────────────────
            distance_pct = round((max_pain_strike - spot_price) / spot_price * 100, 2)

            # ── Total OI in USD for this expiry ───────────────────────
            total_oi_contracts = sum(calls.values()) + sum(puts.values())
            total_oi_usd = round(total_oi_contracts * spot_price, 2)

            out["max_pain"] = max_pain_strike
            out["distance_pct"] = distance_pct
            out["expiry_date"] = nearest_expiry_dt.strftime("%Y-%m-%d")
            out["total_oi_usd"] = total_oi_usd

            logger.info(
                "Max pain %s: $%.0f (spot $%.0f, distance %+.2f%%, "
                "expiry %s, OI $%.0f)",
                currency, max_pain_strike, spot_price, distance_pct,
                out["expiry_date"], total_oi_usd,
            )

        except Exception as exc:
            logger.error("calculate_max_pain error for %s: %s", currency, exc)

        return out

    # ===================================================================== #
    #  Put / Call Ratio                                                       #
    # ===================================================================== #

    def calculate_put_call_ratio(self, currency: str = "BTC") -> Optional[float]:
        """Aggregate put/call open-interest ratio across all expirations.

        Returns put_OI / call_OI as a float, or None on failure.
        """
        try:
            instruments = self._fetch_book_summary(currency)
            if not instruments:
                logger.warning("No option instruments for %s — cannot compute P/C ratio", currency)
                return None

            total_put_oi = 0.0
            total_call_oi = 0.0

            for inst in instruments:
                name = inst.get("instrument_name", "")
                parsed = self._parse_instrument_name(name)
                if parsed is None:
                    continue

                oi = float(inst.get("open_interest", 0))
                if parsed["option_type"] == "P":
                    total_put_oi += oi
                elif parsed["option_type"] == "C":
                    total_call_oi += oi

            if total_call_oi == 0:
                logger.warning("Total call OI is 0 for %s — cannot compute ratio", currency)
                return None

            ratio = round(total_put_oi / total_call_oi, 4)
            logger.info(
                "Put/Call ratio %s: %.4f (puts=%.2f, calls=%.2f)",
                currency, ratio, total_put_oi, total_call_oi,
            )
            return ratio

        except Exception as exc:
            logger.error("calculate_put_call_ratio error for %s: %s", currency, exc)
            return None

    # ===================================================================== #
    #  Volatility Term Structure                                             #
    # ===================================================================== #

    def analyze_vol_term_structure(self, currency: str = "BTC") -> Optional[str]:
        """Compare near-term vs far-term implied volatility.

        Uses the mark_iv field from the book summary for instruments
        nearest to ATM for the two closest expiries.

        Returns
        -------
        "inverted"  — short-term IV > long-term IV (imminent event expected)
        "contango"  — short-term IV < long-term IV (normal)
        "flat"      — roughly equal (within 5 % relative difference)
        None        — not enough data
        """
        try:
            instruments = self._fetch_book_summary(currency)
            if not instruments:
                return None

            spot_price = self._get_spot_price(currency)
            if spot_price is None:
                return None

            # ── Collect (expiry_dt, mark_iv, distance_from_ATM) ──────
            now = datetime.now(timezone.utc)
            expiry_iv_map: Dict[str, List[Tuple[float, float]]] = {}
            # {expiry_str: [(abs_distance_from_spot, mark_iv), ...]}

            for inst in instruments:
                name = inst.get("instrument_name", "")
                parsed = self._parse_instrument_name(name)
                if parsed is None:
                    continue

                mark_iv = inst.get("mark_iv")
                if mark_iv is None or mark_iv == 0:
                    continue
                mark_iv = float(mark_iv)

                expiry_str = parsed["expiry_str"]
                strike = parsed["strike"]
                distance = abs(strike - spot_price)

                if expiry_str not in expiry_iv_map:
                    expiry_iv_map[expiry_str] = []
                expiry_iv_map[expiry_str].append((distance, mark_iv))

            if len(expiry_iv_map) < 2:
                logger.warning("Not enough expiries for vol term-structure (%s)", currency)
                return None

            # ── Sort expiries chronologically ────────────────────────
            sorted_expiries: List[Tuple[datetime, str]] = []
            for exp_str in expiry_iv_map:
                exp_dt = self._parse_expiry_str(exp_str)
                if exp_dt and exp_dt > now:
                    sorted_expiries.append((exp_dt, exp_str))
            sorted_expiries.sort(key=lambda x: x[0])

            if len(sorted_expiries) < 2:
                return None

            # ── Near-term ATM IV (closest expiry, closest-to-ATM strike)
            near_exp_str = sorted_expiries[0][1]
            far_exp_str = sorted_expiries[-1][1]

            def _atm_iv(entries: List[Tuple[float, float]]) -> float:
                """Weighted average IV of the 4 strikes closest to ATM."""
                entries_sorted = sorted(entries, key=lambda x: x[0])
                top = entries_sorted[:4]
                if not top:
                    return 0.0
                # Inverse-distance weighting
                total_weight = 0.0
                weighted_iv = 0.0
                for dist, iv in top:
                    w = 1.0 / (dist + 1.0)
                    weighted_iv += iv * w
                    total_weight += w
                return weighted_iv / total_weight if total_weight > 0 else 0.0

            near_iv = _atm_iv(expiry_iv_map[near_exp_str])
            far_iv = _atm_iv(expiry_iv_map[far_exp_str])

            if near_iv == 0 or far_iv == 0:
                return None

            relative_diff = (near_iv - far_iv) / far_iv

            if relative_diff > 0.05:
                structure = "inverted"
            elif relative_diff < -0.05:
                structure = "contango"
            else:
                structure = "flat"

            logger.info(
                "Vol term-structure %s: %s (near IV=%.2f, far IV=%.2f, diff=%.2f%%)",
                currency, structure, near_iv, far_iv, relative_diff * 100,
            )
            return structure

        except Exception as exc:
            logger.error("analyze_vol_term_structure error for %s: %s", currency, exc)
            return None

    # ===================================================================== #
    #  Main aggregated fetch                                                 #
    # ===================================================================== #

    def fetch_all(self) -> Dict[str, Any]:
        """Aggregate all options metrics into a single dict matching the
        ``options_data`` Supabase table schema.

        Returns
        -------
        dict with keys:
            btc_dvol, eth_dvol, btc_dvol_change_24h, dvol_percentile_90d,
            btc_max_pain, eth_max_pain, btc_max_pain_distance_pct,
            btc_put_call_ratio, eth_put_call_ratio, vol_term_structure,
            next_expiry_date, next_expiry_oi_usd, timestamp
        """
        logger.info("fetch_all — starting full options scan")

        # Clear book summary cache for fresh data each run
        self._book_summary_cache.clear()

        # ── DVOL ─────────────────────────────────────────────────────
        btc_dvol_data = self.fetch_dvol("BTC")
        eth_dvol_data = self.fetch_dvol("ETH")

        # ── DVOL 90-day percentile (BTC) ─────────────────────────────
        dvol_percentile = self.calculate_dvol_percentile_90d("BTC")

        # ── Max Pain ─────────────────────────────────────────────────
        btc_max_pain_data = self.calculate_max_pain("BTC")
        eth_max_pain_data = self.calculate_max_pain("ETH")

        # ── Put/Call Ratios ──────────────────────────────────────────
        btc_pc_ratio = self.calculate_put_call_ratio("BTC")
        eth_pc_ratio = self.calculate_put_call_ratio("ETH")

        # ── Vol Term Structure ───────────────────────────────────────
        vol_structure = self.analyze_vol_term_structure("BTC")

        # ── Build record ─────────────────────────────────────────────
        record = {
            "btc_dvol": btc_dvol_data.get("dvol"),
            "eth_dvol": eth_dvol_data.get("dvol"),
            "btc_dvol_change_24h": btc_dvol_data.get("dvol_change_24h"),
            "dvol_percentile_90d": dvol_percentile,
            "btc_max_pain": btc_max_pain_data.get("max_pain"),
            "eth_max_pain": eth_max_pain_data.get("max_pain"),
            "btc_max_pain_distance_pct": btc_max_pain_data.get("distance_pct"),
            "btc_put_call_ratio": btc_pc_ratio,
            "eth_put_call_ratio": eth_pc_ratio,
            "vol_term_structure": vol_structure,
            "next_expiry_date": btc_max_pain_data.get("expiry_date"),
            "next_expiry_oi_usd": btc_max_pain_data.get("total_oi_usd"),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        logger.info("fetch_all — options scan complete: %s", record)
        return record


# ── Standalone smoke test ───────────────────────────────────────────────
if __name__ == "__main__":
    logging.basicConfig(
        level=getattr(logging, config.LOG_LEVEL, logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    )
    scanner = OptionsScanner()

    print("\n=== BTC DVOL ===")
    dvol = scanner.fetch_dvol("BTC")
    for k, v in dvol.items():
        if k == "history":
            print(f"  history: {len(v)} data points")
        else:
            print(f"  {k}: {v}")

    print("\n=== ETH DVOL ===")
    dvol_eth = scanner.fetch_dvol("ETH")
    for k, v in dvol_eth.items():
        if k == "history":
            print(f"  history: {len(v)} data points")
        else:
            print(f"  {k}: {v}")

    print("\n=== BTC DVOL 90d Percentile ===")
    pct = scanner.calculate_dvol_percentile_90d("BTC")
    print(f"  percentile: {pct}")

    print("\n=== BTC Max Pain ===")
    mp = scanner.calculate_max_pain("BTC")
    for k, v in mp.items():
        print(f"  {k}: {v}")

    print("\n=== ETH Max Pain ===")
    mp_eth = scanner.calculate_max_pain("ETH")
    for k, v in mp_eth.items():
        print(f"  {k}: {v}")

    print("\n=== BTC Put/Call Ratio ===")
    pcr = scanner.calculate_put_call_ratio("BTC")
    print(f"  ratio: {pcr}")

    print("\n=== ETH Put/Call Ratio ===")
    pcr_eth = scanner.calculate_put_call_ratio("ETH")
    print(f"  ratio: {pcr_eth}")

    print("\n=== Vol Term Structure ===")
    vts = scanner.analyze_vol_term_structure("BTC")
    print(f"  structure: {vts}")

    print("\n=== Full Scan (fetch_all) ===")
    full = scanner.fetch_all()
    for k, v in full.items():
        print(f"  {k}: {v}")
