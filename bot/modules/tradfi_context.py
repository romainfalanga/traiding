"""
Macro Pulse — Couche 2 : TradFi Context.
Captures traditional finance indicators that correlate with crypto markets.
Uses yfinance for DXY, VIX, S&P500, US10Y, Gold, and BTC-SPX correlation.
"""

import sys
import os
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import numpy as np
import pandas as pd
import yfinance as yf

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

logger = logging.getLogger(__name__)


class TradFiContext:
    """Fetches and aggregates traditional finance data relevant to crypto trading."""

    # ── Ticker symbols ───────────────────────────────────────────────
    TICKER_DXY = "DX-Y.NYB"
    TICKER_VIX = "^VIX"
    TICKER_SP500 = "^GSPC"
    TICKER_US10Y = "^TNX"
    TICKER_GOLD = "GC=F"
    TICKER_BTC = "BTC-USD"

    def __init__(self) -> None:
        self._cache: Dict[str, pd.DataFrame] = {}
        self._results: Dict[str, Any] = {}

    # ── Public API ───────────────────────────────────────────────────

    def fetch_all(self) -> Dict[str, Any]:
        """Fetch every TradFi data point and return a complete dict."""
        self._results = {}

        dxy = self.get_dxy()
        vix = self.get_vix()
        sp500 = self.get_sp500()
        us10y = self.get_us10y()
        gold = self.get_gold()
        btc_spx_corr = self.calculate_btc_spx_correlation()
        macro_score = self.calculate_macro_risk_score()

        self._results.update(
            {
                "dxy": dxy,
                "vix": vix,
                "sp500": sp500,
                "us10y": us10y,
                "gold": gold,
                "btc_spx_correlation_30d": btc_spx_corr,
                "macro_risk_score": macro_score,
            }
        )
        return self._results

    def to_dict(self) -> Dict[str, Any]:
        """Return a flat dict matching the ``tradfi_context`` Supabase table schema."""
        if not self._results:
            self.fetch_all()

        dxy = self._results.get("dxy") or {}
        vix = self._results.get("vix") or {}
        sp500 = self._results.get("sp500") or {}
        us10y = self._results.get("us10y") or {}
        gold = self._results.get("gold") or {}

        return {
            "dxy_price": dxy.get("price"),
            "dxy_change_24h": dxy.get("change_24h"),
            "vix_value": vix.get("value"),
            "vix_percentile_90d": vix.get("percentile_90d"),
            "sp500_price": sp500.get("price"),
            "sp500_change_24h": sp500.get("change_24h"),
            "us10y_yield": us10y.get("yield"),
            "us10y_change_24h": us10y.get("change_24h"),
            "gold_price": gold.get("price"),
            "gold_change_24h": gold.get("change_24h"),
            "btc_spx_correlation_30d": self._results.get("btc_spx_correlation_30d"),
            "macro_risk_score": self._results.get("macro_risk_score"),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    # ── Data fetching ────────────────────────────────────────────────

    def _fetch_ticker_data(
        self,
        ticker: str,
        period: str = "90d",
        interval: str = "1h",
    ) -> Optional[pd.DataFrame]:
        """Download OHLCV data via yfinance and cache the result.

        Returns *None* if the download fails or yields an empty frame.
        """
        cache_key = f"{ticker}_{period}_{interval}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        try:
            df = yf.download(
                ticker,
                period=period,
                interval=interval,
                progress=False,
                auto_adjust=True,
            )
            if df is None or df.empty:
                logger.warning("yfinance returned empty data for %s", ticker)
                return None

            # Flatten multi-level columns when downloading a single ticker
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)

            self._cache[cache_key] = df
            return df
        except Exception:
            logger.exception("Failed to fetch ticker data for %s", ticker)
            return None

    # ── Helpers ──────────────────────────────────────────────────────

    @staticmethod
    def _safe_last_close(df: Optional[pd.DataFrame]) -> Optional[float]:
        """Return the last Close value or None."""
        if df is None or df.empty:
            return None
        try:
            return float(df["Close"].iloc[-1])
        except Exception:
            return None

    @staticmethod
    def _pct_change_n_bars(df: Optional[pd.DataFrame], n: int) -> Optional[float]:
        """Percentage change between the last close and *n* bars ago.

        Returns value as a percentage (e.g. 1.5 means +1.5 %).
        """
        if df is None or df.empty or len(df) < n + 1:
            return None
        try:
            current = float(df["Close"].iloc[-1])
            previous = float(df["Close"].iloc[-n - 1])
            if previous == 0:
                return None
            return round((current - previous) / previous * 100, 4)
        except Exception:
            return None

    @staticmethod
    def _percentile(series: pd.Series, current_value: float) -> Optional[float]:
        """Return the percentile rank (0-100) of *current_value* within *series*."""
        try:
            clean = series.dropna()
            if clean.empty:
                return None
            rank = (clean < current_value).sum() / len(clean) * 100
            return round(float(rank), 2)
        except Exception:
            return None

    # ── Individual indicator methods ─────────────────────────────────

    def get_dxy(self) -> Dict[str, Any]:
        """US Dollar Index — price and multi-timeframe changes."""
        df = self._fetch_ticker_data(self.TICKER_DXY, period="90d", interval="1h")
        price = self._safe_last_close(df)
        return {
            "price": price,
            "change_1h": self._pct_change_n_bars(df, 1),
            "change_4h": self._pct_change_n_bars(df, 4),
            "change_24h": self._pct_change_n_bars(df, 24),
            "change_7d": self._pct_change_n_bars(df, 24 * 7),
        }

    def get_vix(self) -> Dict[str, Any]:
        """CBOE Volatility Index — value, 30d average, 90d percentile."""
        df = self._fetch_ticker_data(self.TICKER_VIX, period="90d", interval="1h")
        value = self._safe_last_close(df)

        avg_30d: Optional[float] = None
        percentile_90d: Optional[float] = None

        if df is not None and not df.empty:
            try:
                # Last 30 calendar-days of hourly bars (~720 bars max)
                cutoff_30d = df.index[-1] - pd.Timedelta(days=30)
                last_30d = df.loc[df.index >= cutoff_30d, "Close"]
                avg_30d = round(float(last_30d.mean()), 4) if not last_30d.empty else None
            except Exception:
                logger.debug("Could not compute VIX 30d average", exc_info=True)

            try:
                percentile_90d = self._percentile(df["Close"], value) if value is not None else None
            except Exception:
                logger.debug("Could not compute VIX 90d percentile", exc_info=True)

        return {
            "value": value,
            "avg_30d": avg_30d,
            "percentile_90d": percentile_90d,
        }

    def get_sp500(self) -> Dict[str, Any]:
        """S&P 500 — current price and 24 h change."""
        df = self._fetch_ticker_data(self.TICKER_SP500, period="90d", interval="1h")
        return {
            "price": self._safe_last_close(df),
            "change_24h": self._pct_change_n_bars(df, 24),
        }

    def get_us10y(self) -> Dict[str, Any]:
        """US 10-Year Treasury yield — current yield and 24 h change."""
        df = self._fetch_ticker_data(self.TICKER_US10Y, period="90d", interval="1h")
        return {
            "yield": self._safe_last_close(df),
            "change_24h": self._pct_change_n_bars(df, 24),
        }

    def get_gold(self) -> Dict[str, Any]:
        """Gold futures — current price and 24 h change."""
        df = self._fetch_ticker_data(self.TICKER_GOLD, period="90d", interval="1h")
        return {
            "price": self._safe_last_close(df),
            "change_24h": self._pct_change_n_bars(df, 24),
        }

    # ── Derived analytics ────────────────────────────────────────────

    def calculate_btc_spx_correlation(self, days: int = 30) -> Optional[float]:
        """Pearson correlation between BTC and S&P 500 daily closes.

        Returns a float in [-1, 1] or *None* on failure.
        """
        try:
            period = f"{days + 10}d"  # small buffer for weekends/holidays
            btc_df = self._fetch_ticker_data(self.TICKER_BTC, period=period, interval="1d")
            spx_df = self._fetch_ticker_data(self.TICKER_SP500, period=period, interval="1d")

            if btc_df is None or spx_df is None:
                logger.warning("Cannot compute BTC/SPX correlation — missing data")
                return None

            # Align on common dates
            btc_close = btc_df["Close"].rename("btc")
            spx_close = spx_df["Close"].rename("spx")
            merged = pd.concat([btc_close, spx_close], axis=1).dropna()

            if len(merged) < 10:
                logger.warning(
                    "Not enough overlapping data points for correlation (%d)", len(merged)
                )
                return None

            # Trim to the requested number of days
            merged = merged.iloc[-days:]

            corr = float(np.corrcoef(merged["btc"].values, merged["spx"].values)[0, 1])
            return round(corr, 4)
        except Exception:
            logger.exception("BTC/SPX correlation calculation failed")
            return None

    def calculate_macro_risk_score(self) -> Optional[int]:
        """Composite score 0-100 combining DXY, VIX, S&P 500, and US10Y.

        Weights:
            DXY percentile (inverted)      — 25 %
            VIX percentile (inverted)       — 25 %
            S&P 500 24 h change (normalized)— 25 %
            US10Y change (inverted)         — 25 %

        >70 = risk-on (bullish crypto), <30 = risk-off (bearish crypto).
        """
        components: list[Optional[float]] = []

        # ── 1. DXY — high DXY is bearish for crypto → invert ────────
        dxy_df = self._fetch_ticker_data(self.TICKER_DXY, period="90d", interval="1h")
        if dxy_df is not None and not dxy_df.empty:
            dxy_price = self._safe_last_close(dxy_df)
            if dxy_price is not None:
                dxy_pct = self._percentile(dxy_df["Close"], dxy_price)
                components.append(100.0 - dxy_pct if dxy_pct is not None else None)
            else:
                components.append(None)
        else:
            components.append(None)

        # ── 2. VIX — high VIX is bearish → invert ───────────────────
        vix_df = self._fetch_ticker_data(self.TICKER_VIX, period="90d", interval="1h")
        if vix_df is not None and not vix_df.empty:
            vix_value = self._safe_last_close(vix_df)
            if vix_value is not None:
                vix_pct = self._percentile(vix_df["Close"], vix_value)
                components.append(100.0 - vix_pct if vix_pct is not None else None)
            else:
                components.append(None)
        else:
            components.append(None)

        # ── 3. S&P 500 24 h change — normalize to 0-100 ─────────────
        #  Map typical daily range [-3%, +3%] to [0, 100].
        sp500_change = self._pct_change_n_bars(
            self._fetch_ticker_data(self.TICKER_SP500, period="90d", interval="1h"), 24
        )
        if sp500_change is not None:
            # Clamp to [-3, 3] then scale to [0, 100]
            clamped = max(-3.0, min(3.0, sp500_change))
            normalized = (clamped + 3.0) / 6.0 * 100.0
            components.append(normalized)
        else:
            components.append(None)

        # ── 4. US10Y change — rising yields are bearish → invert ─────
        us10y_change = self._pct_change_n_bars(
            self._fetch_ticker_data(self.TICKER_US10Y, period="90d", interval="1h"), 24
        )
        if us10y_change is not None:
            # Clamp to [-5, 5] then invert and scale to [0, 100]
            clamped = max(-5.0, min(5.0, us10y_change))
            normalized = (1.0 - (clamped + 5.0) / 10.0) * 100.0
            components.append(normalized)
        else:
            components.append(None)

        # ── Weighted average (skip None components) ──────────────────
        valid = [c for c in components if c is not None]
        if not valid:
            logger.warning("No valid components for macro risk score")
            return None

        score = sum(valid) / len(valid)
        return int(round(max(0, min(100, score))))


# ── Standalone smoke test ────────────────────────────────────────────
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(name)s  %(message)s")
    ctx = TradFiContext()
    data = ctx.fetch_all()
    flat = ctx.to_dict()

    print("\n=== TradFi Context — Raw ===")
    for key, val in data.items():
        print(f"  {key}: {val}")

    print("\n=== TradFi Context — Flat (Supabase schema) ===")
    for key, val in flat.items():
        print(f"  {key}: {val}")
