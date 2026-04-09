"""
Macro Pulse — Couche 5 : DeFi Scanner.

Captures DeFi ecosystem data from DeFiLlama API (100% free, no API key needed).
Tracks TVL, stablecoin flows, DEX volumes, and computes a composite
Liquidity Pulse Score to gauge on-chain liquidity conditions.
"""

import sys
import os
import json
import logging
from datetime import datetime, timezone

import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

logger = logging.getLogger(__name__)


class DefiScanner:
    """Fetches DeFi ecosystem data from DeFiLlama and computes a Liquidity Pulse Score."""

    # Seconds per time window — used to look back in the TVL history
    _SECONDS_1D = 86_400
    _SECONDS_7D = 86_400 * 7
    _SECONDS_30D = 86_400 * 30

    # Reference CEX daily volume (USD) for DEX/CEX ratio estimation.
    # Typical aggregate CEX spot volume sits in the $30-50 B range; we use
    # the midpoint as a conservative baseline.
    _CEX_DAILY_VOLUME_REF = 40_000_000_000  # $40 B

    # Historical average DEX/CEX ratio (%) — used to normalise the score.
    # Over 2023-2025 this has typically ranged from 8-20 %.
    _HIST_DEX_CEX_RATIO_LOW = 8.0
    _HIST_DEX_CEX_RATIO_HIGH = 25.0

    # Major stablecoins to track individually
    _MAJOR_STABLES = {"USDT", "USDC", "DAI", "BUSD", "TUSD"}

    # ------------------------------------------------------------------ init
    def __init__(self) -> None:
        self._session = requests.Session()
        self._session.headers.update({"Accept": "application/json"})
        logger.info("DefiScanner initialised (DeFiLlama public API).")

    # ================================================================== #
    #  1. Total Value Locked (TVL)                                       #
    # ================================================================== #

    def fetch_total_tvl(self) -> dict:
        """Fetch historical chain TVL from DeFiLlama and compute changes.

        Returns
        -------
        dict with keys:
            current_tvl, tvl_24h_ago, tvl_7d_ago, tvl_30d_ago,
            tvl_change_24h_pct, tvl_change_7d_pct
        """
        result = {
            "current_tvl": None,
            "tvl_24h_ago": None,
            "tvl_7d_ago": None,
            "tvl_30d_ago": None,
            "tvl_change_24h_pct": None,
            "tvl_change_7d_pct": None,
        }

        try:
            url = f"{config.DEFILLAMA_BASE_URL}/v2/historicalChainTvl"
            resp = self._session.get(url, timeout=15)
            resp.raise_for_status()
            data = resp.json()  # list of {"date": unix_ts, "tvl": float}

            if not data or not isinstance(data, list):
                logger.warning("fetch_total_tvl — empty or unexpected response")
                return result

            # Data is sorted chronologically; the last entry is the most recent.
            current_point = data[-1]
            current_tvl = float(current_point.get("tvl", 0))
            current_ts = int(current_point.get("date", 0))

            result["current_tvl"] = current_tvl

            # Find TVL at historical offsets by searching backwards
            target_offsets = {
                "tvl_24h_ago": self._SECONDS_1D,
                "tvl_7d_ago": self._SECONDS_7D,
                "tvl_30d_ago": self._SECONDS_30D,
            }

            for key, offset in target_offsets.items():
                target_ts = current_ts - offset
                closest = self._find_closest_tvl(data, target_ts)
                if closest is not None:
                    result[key] = closest

            # Calculate percentage changes
            if result["tvl_24h_ago"] and result["tvl_24h_ago"] > 0:
                result["tvl_change_24h_pct"] = round(
                    (current_tvl - result["tvl_24h_ago"]) / result["tvl_24h_ago"] * 100, 4
                )

            if result["tvl_7d_ago"] and result["tvl_7d_ago"] > 0:
                result["tvl_change_7d_pct"] = round(
                    (current_tvl - result["tvl_7d_ago"]) / result["tvl_7d_ago"] * 100, 4
                )

            logger.info(
                "TVL — current: $%.2fB, 24h: %s%%, 7d: %s%%",
                current_tvl / 1e9,
                result["tvl_change_24h_pct"],
                result["tvl_change_7d_pct"],
            )

        except requests.RequestException as exc:
            logger.error("fetch_total_tvl — HTTP error: %s", exc)
        except (ValueError, KeyError, TypeError) as exc:
            logger.error("fetch_total_tvl — parse error: %s", exc)
        except Exception as exc:
            logger.error("fetch_total_tvl — unexpected error: %s", exc)

        return result

    # ================================================================== #
    #  2. Stablecoin Data                                                #
    # ================================================================== #

    def fetch_stablecoin_data(self) -> dict:
        """Fetch stablecoin supply data from DeFiLlama.

        Returns
        -------
        dict with keys:
            total_supply, major_stables (dict), supply_change_7d,
            supply_change_7d_pct, mint_rate, burn_rate
        """
        result = {
            "total_supply": None,
            "major_stables": {},
            "supply_change_7d": None,
            "supply_change_7d_pct": None,
            "mint_rate": None,
            "burn_rate": None,
        }

        try:
            url = f"{config.STABLECOINS_URL}/stablecoins?includePrices=true"
            resp = self._session.get(url, timeout=15)
            resp.raise_for_status()
            data = resp.json()

            stablecoins = data.get("peggedAssets", [])
            if not stablecoins:
                logger.warning("fetch_stablecoin_data — no peggedAssets in response")
                return result

            total_supply = 0.0
            total_supply_prev_day = 0.0
            total_supply_prev_week = 0.0
            major_details: dict = {}

            for coin in stablecoins:
                symbol = coin.get("symbol", "")
                name = coin.get("name", "")

                # Current circulating supply
                circulating = coin.get("circulating", {})
                current = float(circulating.get("peggedUSD", 0) or 0)
                total_supply += current

                # Previous day supply
                prev_day_data = coin.get("circulatingPrevDay", {})
                prev_day = float(prev_day_data.get("peggedUSD", 0) or 0)
                total_supply_prev_day += prev_day

                # Previous week supply
                prev_week_data = coin.get("circulatingPrevWeek", {})
                prev_week = float(prev_week_data.get("peggedUSD", 0) or 0)
                total_supply_prev_week += prev_week

                # Track major stablecoins individually
                if symbol in self._MAJOR_STABLES:
                    week_change = current - prev_week if prev_week > 0 else 0.0
                    week_change_pct = (
                        round(week_change / prev_week * 100, 4)
                        if prev_week > 0
                        else None
                    )
                    major_details[symbol] = {
                        "name": name,
                        "supply": round(current, 2),
                        "supply_prev_week": round(prev_week, 2),
                        "change_7d": round(week_change, 2),
                        "change_7d_pct": week_change_pct,
                    }

            result["total_supply"] = round(total_supply, 2)
            result["major_stables"] = major_details

            # 7-day supply change
            supply_change_7d = total_supply - total_supply_prev_week
            result["supply_change_7d"] = round(supply_change_7d, 2)

            if total_supply_prev_week > 0:
                result["supply_change_7d_pct"] = round(
                    supply_change_7d / total_supply_prev_week * 100, 4
                )

            # Mint rate (positive inflows) vs burn rate (negative outflows)
            # Calculated from per-coin daily changes
            total_minted = 0.0
            total_burned = 0.0

            for coin in stablecoins:
                circulating = coin.get("circulating", {})
                current = float(circulating.get("peggedUSD", 0) or 0)
                prev_day_data = coin.get("circulatingPrevDay", {})
                prev_day = float(prev_day_data.get("peggedUSD", 0) or 0)

                daily_change = current - prev_day
                if daily_change > 0:
                    total_minted += daily_change
                elif daily_change < 0:
                    total_burned += abs(daily_change)

            result["mint_rate"] = round(total_minted, 2)
            result["burn_rate"] = round(total_burned, 2)

            logger.info(
                "Stablecoins — total supply: $%.2fB, 7d change: $%.2fB (%s%%), "
                "mint rate: $%.2fM/day, burn rate: $%.2fM/day",
                total_supply / 1e9,
                supply_change_7d / 1e9,
                result["supply_change_7d_pct"],
                total_minted / 1e6,
                total_burned / 1e6,
            )

        except requests.RequestException as exc:
            logger.error("fetch_stablecoin_data — HTTP error: %s", exc)
        except (ValueError, KeyError, TypeError) as exc:
            logger.error("fetch_stablecoin_data — parse error: %s", exc)
        except Exception as exc:
            logger.error("fetch_stablecoin_data — unexpected error: %s", exc)

        return result

    # ================================================================== #
    #  3. DEX Volumes                                                    #
    # ================================================================== #

    def fetch_dex_volumes(self) -> dict:
        """Fetch aggregate DEX volume data from DeFiLlama.

        Returns
        -------
        dict with keys:
            dex_volume_24h, dex_cex_ratio
        """
        result = {
            "dex_volume_24h": None,
            "dex_cex_ratio": None,
        }

        try:
            url = (
                f"{config.DEFILLAMA_BASE_URL}/overview/dexs"
                "?excludeTotalDataChart=true"
                "&excludeTotalDataChartBreakdown=true"
                "&dataType=dailyVolume"
            )
            resp = self._session.get(url, timeout=15)
            resp.raise_for_status()
            data = resp.json()

            # Try to get total 24h volume from different possible fields
            dex_volume = None

            # Primary: total24h field
            if "total24h" in data and data["total24h"] is not None:
                dex_volume = float(data["total24h"])

            # Fallback: sum the totalDataChart last entry
            if dex_volume is None and "totalDataChart" in data:
                chart = data["totalDataChart"]
                if chart and isinstance(chart, list) and len(chart) > 0:
                    last_entry = chart[-1]
                    if isinstance(last_entry, list) and len(last_entry) >= 2:
                        dex_volume = float(last_entry[1])
                    elif isinstance(last_entry, dict):
                        dex_volume = float(last_entry.get("volume", 0) or last_entry.get("dailyVolume", 0))

            # Fallback: sum individual protocol volumes
            if dex_volume is None and "protocols" in data:
                protocols = data["protocols"]
                if protocols and isinstance(protocols, list):
                    total = 0.0
                    for protocol in protocols:
                        vol = protocol.get("total24h")
                        if vol is not None:
                            try:
                                total += float(vol)
                            except (ValueError, TypeError):
                                continue
                    if total > 0:
                        dex_volume = total

            if dex_volume is not None and dex_volume > 0:
                result["dex_volume_24h"] = round(dex_volume, 2)

                # DEX/CEX ratio as percentage
                dex_cex_ratio = (dex_volume / self._CEX_DAILY_VOLUME_REF) * 100
                result["dex_cex_ratio"] = round(dex_cex_ratio, 4)

                logger.info(
                    "DEX volume 24h: $%.2fB, DEX/CEX ratio: %.2f%%",
                    dex_volume / 1e9,
                    dex_cex_ratio,
                )
            else:
                logger.warning("fetch_dex_volumes — could not extract 24h volume")

        except requests.RequestException as exc:
            logger.error("fetch_dex_volumes — HTTP error: %s", exc)
        except (ValueError, KeyError, TypeError) as exc:
            logger.error("fetch_dex_volumes — parse error: %s", exc)
        except Exception as exc:
            logger.error("fetch_dex_volumes — unexpected error: %s", exc)

        return result

    # ================================================================== #
    #  4. Liquidity Pulse Score                                          #
    # ================================================================== #

    def calculate_liquidity_pulse_score(
        self,
        tvl_data: dict,
        stablecoin_data: dict,
        dex_data: dict,
    ) -> int | None:
        """Composite score 0-100 measuring on-chain liquidity conditions.

        Components (each 0-25):
            1. TVL change 7d normalised          — positive = higher
            2. Stablecoin supply change 7d        — growth = higher
            3. Stablecoin mint rate               — minting = higher
            4. DEX/CEX ratio vs historical range  — higher = higher

        Interpretation:
            > 70  = liquidity flooding in (bullish)
            < 30  = liquidity drying up (bearish)

        Returns an integer score or None if insufficient data.
        """
        components: list[float | None] = []

        # ── 1. TVL change 7d normalised (0-25) ─────────────────────────
        tvl_change_7d = tvl_data.get("tvl_change_7d_pct")
        if tvl_change_7d is not None:
            # Map typical range [-10%, +10%] to [0, 25]
            clamped = max(-10.0, min(10.0, tvl_change_7d))
            normalised = ((clamped + 10.0) / 20.0) * 25.0
            components.append(normalised)
        else:
            components.append(None)

        # ── 2. Stablecoin supply change 7d normalised (0-25) ───────────
        supply_change_pct = stablecoin_data.get("supply_change_7d_pct")
        if supply_change_pct is not None:
            # Map typical range [-5%, +5%] to [0, 25]
            clamped = max(-5.0, min(5.0, supply_change_pct))
            normalised = ((clamped + 5.0) / 10.0) * 25.0
            components.append(normalised)
        else:
            components.append(None)

        # ── 3. Stablecoin mint rate (0-25) ──────────────────────────────
        mint_rate = stablecoin_data.get("mint_rate")
        burn_rate = stablecoin_data.get("burn_rate")
        if mint_rate is not None and burn_rate is not None:
            # Net minting = mint - burn.  Normalise to [0, 25].
            # Typical daily net ranges roughly from -$500M to +$500M.
            net_mint = mint_rate - burn_rate
            clamped = max(-500_000_000, min(500_000_000, net_mint))
            normalised = ((clamped + 500_000_000) / 1_000_000_000) * 25.0
            components.append(normalised)
        else:
            components.append(None)

        # ── 4. DEX/CEX ratio vs historical (0-25) ──────────────────────
        dex_cex_ratio = dex_data.get("dex_cex_ratio")
        if dex_cex_ratio is not None:
            # Map from [_HIST_DEX_CEX_RATIO_LOW, _HIST_DEX_CEX_RATIO_HIGH] to [0, 25]
            ratio_range = self._HIST_DEX_CEX_RATIO_HIGH - self._HIST_DEX_CEX_RATIO_LOW
            if ratio_range > 0:
                clamped = max(self._HIST_DEX_CEX_RATIO_LOW, min(self._HIST_DEX_CEX_RATIO_HIGH, dex_cex_ratio))
                normalised = ((clamped - self._HIST_DEX_CEX_RATIO_LOW) / ratio_range) * 25.0
            else:
                normalised = 12.5  # midpoint fallback
            components.append(normalised)
        else:
            components.append(None)

        # ── Weighted average (skip None, re-weight to 100) ─────────────
        valid = [c for c in components if c is not None]
        if not valid:
            logger.warning("calculate_liquidity_pulse_score — no valid components")
            return None

        # Scale up proportionally if some components are missing
        # so the score still ranges 0-100.
        scale_factor = 4.0 / len(valid)
        raw_score = sum(valid) * scale_factor
        score = int(round(max(0, min(100, raw_score))))

        label = "neutral"
        if score > 70:
            label = "BULLISH (liquidity flooding in)"
        elif score < 30:
            label = "BEARISH (liquidity drying up)"

        logger.info(
            "Liquidity Pulse Score: %d/100 [%s] — components: %s",
            score,
            label,
            [round(c, 2) if c is not None else None for c in components],
        )
        return score

    # ================================================================== #
    #  5. Aggregated fetch — main entry point                            #
    # ================================================================== #

    def fetch_all(self) -> dict:
        """Main entry point — fetches all DeFi data and computes the
        Liquidity Pulse Score.

        Returns
        -------
        dict matching the ``defi_flows`` table schema:
            total_tvl, tvl_change_24h_pct, tvl_change_7d_pct,
            stablecoin_total_supply, stablecoin_supply_change_7d,
            stablecoin_mint_rate, dex_volume_24h, dex_cex_ratio,
            liquidity_pulse_score, timestamp
        """
        logger.info("fetch_all — starting full DeFi scan")

        # 1. TVL
        tvl_data = self.fetch_total_tvl()

        # 2. Stablecoins
        stablecoin_data = self.fetch_stablecoin_data()

        # 3. DEX volumes
        dex_data = self.fetch_dex_volumes()

        # 4. Composite score
        liquidity_score = self.calculate_liquidity_pulse_score(
            tvl_data, stablecoin_data, dex_data
        )

        # Build record matching defi_flows table schema
        record = {
            "total_tvl": tvl_data.get("current_tvl"),
            "tvl_change_24h_pct": tvl_data.get("tvl_change_24h_pct"),
            "tvl_change_7d_pct": tvl_data.get("tvl_change_7d_pct"),
            "stablecoin_total_supply": stablecoin_data.get("total_supply"),
            "stablecoin_supply_change_7d": stablecoin_data.get("supply_change_7d"),
            "stablecoin_mint_rate": stablecoin_data.get("mint_rate"),
            "dex_volume_24h": dex_data.get("dex_volume_24h"),
            "dex_cex_ratio": dex_data.get("dex_cex_ratio"),
            "liquidity_pulse_score": liquidity_score,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        logger.info("fetch_all — complete: %s", record)
        return record

    # ================================================================== #
    #  Private helpers                                                    #
    # ================================================================== #

    @staticmethod
    def _find_closest_tvl(data: list[dict], target_ts: int) -> float | None:
        """Binary-search the TVL list for the entry closest to *target_ts*.

        The list is assumed to be sorted by ``date`` ascending.
        Returns the TVL value or None if the list is empty.
        """
        if not data:
            return None

        lo, hi = 0, len(data) - 1
        while lo < hi:
            mid = (lo + hi) // 2
            if int(data[mid].get("date", 0)) < target_ts:
                lo = mid + 1
            else:
                hi = mid

        # Check the neighbours for the closest match
        best_idx = lo
        best_diff = abs(int(data[lo].get("date", 0)) - target_ts)

        if lo > 0:
            diff_prev = abs(int(data[lo - 1].get("date", 0)) - target_ts)
            if diff_prev < best_diff:
                best_idx = lo - 1

        return float(data[best_idx].get("tvl", 0))


# ──────────────────────────── CLI quick-test ─────────────────────────────
if __name__ == "__main__":
    logging.basicConfig(
        level=getattr(logging, config.LOG_LEVEL, logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    )
    scanner = DefiScanner()

    print("\n=== Total TVL ===")
    tvl = scanner.fetch_total_tvl()
    for k, v in tvl.items():
        print(f"  {k}: {v}")

    print("\n=== Stablecoin Data ===")
    stable = scanner.fetch_stablecoin_data()
    for k, v in stable.items():
        if k == "major_stables":
            print(f"  {k}:")
            for sym, details in v.items():
                print(f"    {sym}: {details}")
        else:
            print(f"  {k}: {v}")

    print("\n=== DEX Volumes ===")
    dex = scanner.fetch_dex_volumes()
    for k, v in dex.items():
        print(f"  {k}: {v}")

    print("\n=== Liquidity Pulse Score ===")
    score = scanner.calculate_liquidity_pulse_score(tvl, stable, dex)
    print(f"  score: {score}/100")

    print("\n=== Full Scan (fetch_all) ===")
    full = scanner.fetch_all()
    for k, v in full.items():
        print(f"  {k}: {v}")
