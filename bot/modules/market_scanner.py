"""
Macro Pulse — Couche 3 : Market Scanner.

Scans crypto markets via CCXT (Binance) for prices, volumes, derivatives data,
Fear & Greed index, market breadth, and estimated liquidation levels.
"""

import sys
import os
import json
import logging
import time
from datetime import datetime, timezone

import ccxt
import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

logger = logging.getLogger(__name__)


class MarketScanner:
    """Fetches comprehensive market data from Binance and auxiliary APIs."""

    # ------------------------------------------------------------------ init
    def __init__(self):
        self.exchange = ccxt.binance({
            "enableRateLimit": True,
            "options": {
                "defaultType": "future",   # needed for funding / OI endpoints
            },
        })
        logger.info("MarketScanner initialised (Binance public data via CCXT).")

    # ------------------------------------------------- core market data
    def fetch_market_data(self, symbol: str = "BTC/USDT") -> dict:
        """
        Fetch ticker, funding rate and open interest for *symbol*.

        Returns
        -------
        dict with keys: price, volume_24h, change_24h, funding_rate, open_interest
        """
        result = {
            "price": None,
            "volume_24h": None,
            "change_24h": None,
            "funding_rate": None,
            "open_interest": None,
        }

        # --- ticker (last price, 24h volume, 24h change) ----------------
        try:
            ticker = self.exchange.fetch_ticker(symbol)
            result["price"] = ticker.get("last")
            result["volume_24h"] = ticker.get("quoteVolume")  # USDT volume
            result["change_24h"] = ticker.get("percentage")    # 24h % change
        except Exception as exc:
            logger.error("fetch_market_data — ticker error for %s: %s", symbol, exc)

        # --- funding rate ------------------------------------------------
        try:
            funding = self.exchange.fetch_funding_rate(symbol)
            result["funding_rate"] = funding.get("fundingRate")
        except Exception as exc:
            logger.error("fetch_market_data — funding rate error for %s: %s", symbol, exc)

        # --- open interest -----------------------------------------------
        try:
            oi = self.exchange.fetch_open_interest(symbol)
            result["open_interest"] = oi.get("openInterestAmount")
        except Exception as exc:
            logger.error("fetch_market_data — open interest error for %s: %s", symbol, exc)

        logger.info(
            "Market data for %s — price=%.2f, vol_24h=%s, change_24h=%s%%",
            symbol,
            result["price"] or 0,
            result["volume_24h"],
            result["change_24h"],
        )
        return result

    # ------------------------------------------------- long/short ratio
    def fetch_long_short_ratio(self, symbol: str = "BTCUSDT") -> float | None:
        """
        Fetch global long/short account ratio from Binance Futures public API.

        Returns the ratio as a float, or None on failure.
        """
        url = (
            "https://fapi.binance.com/futures/data/globalLongShortAccountRatio"
        )
        params = {"symbol": symbol, "period": "1h", "limit": 1}

        try:
            resp = requests.get(url, params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            if data and isinstance(data, list) and len(data) > 0:
                ratio = float(data[0].get("longShortRatio", 0))
                logger.info("Long/short ratio for %s: %.4f", symbol, ratio)
                return ratio
            logger.warning("Long/short ratio — empty response for %s", symbol)
            return None
        except Exception as exc:
            logger.error("fetch_long_short_ratio error for %s: %s", symbol, exc)
            return None

    # ------------------------------------------------- Fear & Greed
    def fetch_fear_greed(self) -> dict:
        """
        Fetch the Crypto Fear & Greed index from Alternative.me.

        Returns
        -------
        dict with keys: value (int 0-100), classification (str)
        """
        result = {"value": None, "classification": None}
        url = "https://api.alternative.me/fng/?limit=1"

        try:
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            if "data" in data and len(data["data"]) > 0:
                entry = data["data"][0]
                result["value"] = int(entry.get("value", 0))
                result["classification"] = entry.get("value_classification", "")
                logger.info(
                    "Fear & Greed index: %d (%s)",
                    result["value"],
                    result["classification"],
                )
        except Exception as exc:
            logger.error("fetch_fear_greed error: %s", exc)

        return result

    # ------------------------------------------------- market breadth
    def calculate_market_breadth(self) -> dict:
        """
        Calculate the percentage of top-30-by-volume USDT pairs trading
        above their SMA-50 and SMA-200.

        Returns
        -------
        dict with keys: pct_above_sma50, pct_above_sma200
        """
        result = {"pct_above_sma50": None, "pct_above_sma200": None}

        try:
            # Fetch all tickers in one call (spot market for breadth)
            spot_exchange = ccxt.binance({"enableRateLimit": True})
            all_tickers = spot_exchange.fetch_tickers()
        except Exception as exc:
            logger.error("calculate_market_breadth — fetch_tickers error: %s", exc)
            return result

        # Filter to */USDT pairs and pick the top 30 by 24h quote volume
        usdt_tickers = {
            sym: t
            for sym, t in all_tickers.items()
            if sym.endswith("/USDT")
            and t.get("quoteVolume") is not None
            and t["quoteVolume"] > 0
        }
        sorted_symbols = sorted(
            usdt_tickers.keys(),
            key=lambda s: usdt_tickers[s]["quoteVolume"],
            reverse=True,
        )[:30]

        above_sma50 = 0
        above_sma200 = 0
        valid_count = 0

        for sym in sorted_symbols:
            try:
                ohlcv = spot_exchange.fetch_ohlcv(sym, "1d", limit=200)
                if not ohlcv or len(ohlcv) < 50:
                    logger.debug("Skipping %s — not enough OHLCV data (%d bars).", sym, len(ohlcv) if ohlcv else 0)
                    continue

                closes = [candle[4] for candle in ohlcv]
                current_price = closes[-1]

                # SMA-50
                sma50 = sum(closes[-50:]) / 50
                if current_price > sma50:
                    above_sma50 += 1

                # SMA-200 (only if we have enough bars)
                if len(closes) >= 200:
                    sma200 = sum(closes[-200:]) / 200
                    if current_price > sma200:
                        above_sma200 += 1
                else:
                    # If we don't have 200 bars, use what we have as best-effort
                    sma200 = sum(closes) / len(closes)
                    if current_price > sma200:
                        above_sma200 += 1

                valid_count += 1

            except Exception as exc:
                logger.warning("calculate_market_breadth — error for %s: %s", sym, exc)

            # Rate-limit pause between OHLCV calls
            time.sleep(0.25)

        if valid_count > 0:
            result["pct_above_sma50"] = round((above_sma50 / valid_count) * 100, 2)
            result["pct_above_sma200"] = round((above_sma200 / valid_count) * 100, 2)
            logger.info(
                "Market breadth (%d symbols) — above SMA50: %.1f%%, above SMA200: %.1f%%",
                valid_count,
                result["pct_above_sma50"],
                result["pct_above_sma200"],
            )
        else:
            logger.warning("calculate_market_breadth — no valid symbols processed.")

        return result

    # ------------------------------------------------- liquidation levels
    def estimate_liquidation_levels(self, symbol: str = "BTC/USDT") -> dict:
        """
        Estimate liquidation price levels at common leverage multiples.

        Uses open interest and 24h volume to infer average market leverage,
        then computes theoretical liquidation prices for longs and shorts.

        Returns
        -------
        dict  {leverage: {"long": price, "short": price}, ...}
        """
        result = {}

        try:
            market_data = self.fetch_market_data(symbol)
            price = market_data.get("price")
            open_interest = market_data.get("open_interest")
            volume_24h = market_data.get("volume_24h")

            if price is None:
                logger.error("estimate_liquidation_levels — no price available for %s", symbol)
                return result

            # Estimate average leverage from OI / volume
            if open_interest and volume_24h and volume_24h > 0:
                avg_leverage = open_interest / volume_24h
                avg_leverage = max(2.0, min(50.0, avg_leverage))  # clamp [2, 50]
                logger.info(
                    "Estimated avg leverage for %s: %.2f (OI=%.2f, Vol=%.2f)",
                    symbol, avg_leverage, open_interest, volume_24h,
                )
            else:
                avg_leverage = None
                logger.warning(
                    "estimate_liquidation_levels — cannot compute avg leverage for %s "
                    "(OI=%s, Vol=%s). Using standard leverage grid only.",
                    symbol, open_interest, volume_24h,
                )

            # Compute theoretical liquidation prices at each leverage tier
            for leverage in [5, 10, 25, 50, 100]:
                liq_long = round(price * (1 - 1 / leverage), 2)
                liq_short = round(price * (1 + 1 / leverage), 2)
                result[leverage] = {"long": liq_long, "short": liq_short}

            logger.info("Estimated liquidation levels for %s: %s", symbol, result)

        except Exception as exc:
            logger.error("estimate_liquidation_levels error for %s: %s", symbol, exc)

        return result

    # ------------------------------------------------- aggregated fetch
    def fetch_all(self, symbol: str = "BTC/USDT") -> dict:
        """
        Main entry point — aggregates all sub-methods into a single dict
        matching the ``market_continuous`` table schema.

        Returns
        -------
        dict with keys:
            symbol, price, volume_24h, open_interest, funding_rate,
            long_short_ratio, fear_greed_index, market_breadth_above_sma50_pct,
            market_breadth_above_sma200_pct, estimated_liquidation_levels,
            timestamp
        """
        logger.info("fetch_all — starting full market scan for %s", symbol)

        # 1. Core market data (ticker + funding + OI)
        market = self.fetch_market_data(symbol)

        # 2. Long/short ratio (needs Binance-style symbol without slash)
        binance_symbol = symbol.replace("/", "")
        long_short = self.fetch_long_short_ratio(binance_symbol)

        # 3. Fear & Greed
        fng = self.fetch_fear_greed()

        # 4. Market breadth
        breadth = self.calculate_market_breadth()

        # 5. Estimated liquidation levels
        liq_levels = self.estimate_liquidation_levels(symbol)

        # Build unified record
        record = {
            "symbol": symbol,
            "price": market.get("price"),
            "volume_24h": market.get("volume_24h"),
            "open_interest": market.get("open_interest"),
            "funding_rate": market.get("funding_rate"),
            "long_short_ratio": long_short,
            "fear_greed_index": fng.get("value"),
            "market_breadth_above_sma50_pct": breadth.get("pct_above_sma50"),
            "market_breadth_above_sma200_pct": breadth.get("pct_above_sma200"),
            "estimated_liquidation_levels": json.dumps(liq_levels),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        logger.info("fetch_all — complete for %s: %s", symbol, record)
        return record


# ──────────────────────────── CLI quick-test ─────────────────────────────
if __name__ == "__main__":
    logging.basicConfig(
        level=getattr(logging, config.LOG_LEVEL, logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    )
    scanner = MarketScanner()

    print("\n=== Market Data ===")
    md = scanner.fetch_market_data()
    for k, v in md.items():
        print(f"  {k}: {v}")

    print("\n=== Long/Short Ratio ===")
    ls = scanner.fetch_long_short_ratio()
    print(f"  ratio: {ls}")

    print("\n=== Fear & Greed ===")
    fg = scanner.fetch_fear_greed()
    for k, v in fg.items():
        print(f"  {k}: {v}")

    print("\n=== Market Breadth ===")
    mb = scanner.calculate_market_breadth()
    for k, v in mb.items():
        print(f"  {k}: {v}")

    print("\n=== Liquidation Levels ===")
    ll = scanner.estimate_liquidation_levels()
    for lev, prices in ll.items():
        print(f"  {lev}x -> long liq: {prices['long']}, short liq: {prices['short']}")

    print("\n=== Full Scan (fetch_all) ===")
    full = scanner.fetch_all()
    for k, v in full.items():
        print(f"  {k}: {v}")
