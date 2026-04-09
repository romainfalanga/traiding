"""
Macro Pulse — Couche 4 : Technical Analysis Engine.
Multi-timeframe technical analysis using pandas-ta on OHLCV from CCXT.
"""

import sys
import os
import logging
from datetime import datetime, timezone

import ccxt
import pandas as pd
import numpy as np

try:
    import pandas_ta as ta
except ImportError:
    ta = None

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

logger = logging.getLogger("technical_engine")


class TechnicalEngine:
    """Compute technical indicators across multiple timeframes."""

    def __init__(self):
        self.exchange = ccxt.binance({"enableRateLimit": True})

    # ──────────────────────── Data fetching ────────────────────────

    def fetch_ohlcv(self, symbol: str = "BTC/USDT", timeframe: str = "1h", limit: int = 500) -> pd.DataFrame | None:
        try:
            raw = self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            if not raw:
                return None
            df = pd.DataFrame(raw, columns=["timestamp", "open", "high", "low", "close", "volume"])
            df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
            df.set_index("timestamp", inplace=True)
            return df
        except Exception:
            logger.exception("fetch_ohlcv failed for %s %s", symbol, timeframe)
            return None

    # ──────────────────────── Main analysis ────────────────────────

    def analyze(self, symbol: str = "BTC/USDT", timeframe: str = "1h") -> dict:
        df = self.fetch_ohlcv(symbol, timeframe)
        if df is None or len(df) < 200:
            logger.warning("Insufficient data for %s %s", symbol, timeframe)
            return {}

        result: dict = {"symbol": symbol, "timeframe": timeframe}

        # --- RSI ---
        rsi_series = self._rsi(df)
        result["rsi"] = round(float(rsi_series.iloc[-1]), 2) if rsi_series is not None else None
        result["rsi_divergence"] = self._detect_rsi_divergence(df, rsi_series)

        # --- MACD ---
        macd_data = self._macd(df)
        result.update(macd_data)

        # --- SMAs ---
        for period in (20, 50, 200):
            val = df["close"].rolling(period).mean().iloc[-1]
            result[f"sma_{period}"] = round(float(val), 2)

        # --- EMAs ---
        result["ema_12"] = round(float(df["close"].ewm(span=12).mean().iloc[-1]), 2)
        result["ema_26"] = round(float(df["close"].ewm(span=26).mean().iloc[-1]), 2)

        # --- ATR ---
        atr_series = self._atr(df)
        result["atr"] = round(float(atr_series.iloc[-1]), 2) if atr_series is not None else None

        # --- Bollinger Bands ---
        bb = self._bollinger(df)
        result.update(bb)

        # --- Keltner Squeeze ---
        result["keltner_squeeze"] = self._keltner_squeeze(df, atr_series)

        # --- OBV ---
        result["obv"] = self._obv(df)

        # --- VWAP ---
        result["vwap"] = self._vwap(df)

        # --- CVD ---
        result["cvd"] = self._cvd(df)

        # --- Pivot Points ---
        pivots = self._pivots(df)
        result.update(pivots)

        # --- Trend Strength Score ---
        result["trend_strength_score"] = self._trend_strength(df, result)

        # --- Momentum Exhaustion ---
        result["momentum_exhaustion"] = self._momentum_exhaustion(result)

        # --- Volatility Regime ---
        result["volatility_regime"] = self._volatility_regime(df, atr_series)

        # --- MTF Confluence (placeholder — needs multi-TF data) ---
        result["mtf_confluence_score"] = 0

        result["timestamp"] = datetime.now(timezone.utc).isoformat()
        return result

    # ──────────────────────── Indicators ───────────────────────────

    def _rsi(self, df: pd.DataFrame, period: int = 14) -> pd.Series | None:
        try:
            if ta:
                return df.ta.rsi(length=period)
            delta = df["close"].diff()
            gain = delta.where(delta > 0, 0.0).rolling(period).mean()
            loss = (-delta.where(delta < 0, 0.0)).rolling(period).mean()
            rs = gain / loss.replace(0, np.nan)
            return 100 - (100 / (1 + rs))
        except Exception:
            logger.exception("RSI calculation failed")
            return None

    def _detect_rsi_divergence(self, df: pd.DataFrame, rsi: pd.Series | None) -> str:
        if rsi is None or len(df) < 30:
            return "none"
        try:
            close = df["close"].values
            rsi_vals = rsi.values
            # Find last two swing lows (simple approach: local minima in 10-bar windows)
            lows_idx = []
            for i in range(20, len(close) - 1):
                window = close[max(0, i - 5):i + 6]
                if close[i] == window.min():
                    lows_idx.append(i)
            if len(lows_idx) < 2:
                return "none"
            i1, i2 = lows_idx[-2], lows_idx[-1]
            if close[i2] < close[i1] and rsi_vals[i2] > rsi_vals[i1]:
                return "bullish"
            # Swing highs for bearish divergence
            highs_idx = []
            for i in range(20, len(close) - 1):
                window = close[max(0, i - 5):i + 6]
                if close[i] == window.max():
                    highs_idx.append(i)
            if len(highs_idx) >= 2:
                h1, h2 = highs_idx[-2], highs_idx[-1]
                if close[h2] > close[h1] and rsi_vals[h2] < rsi_vals[h1]:
                    return "bearish"
            return "none"
        except Exception:
            return "none"

    def _macd(self, df: pd.DataFrame) -> dict:
        try:
            ema12 = df["close"].ewm(span=12).mean()
            ema26 = df["close"].ewm(span=26).mean()
            macd_line = ema12 - ema26
            signal_line = macd_line.ewm(span=9).mean()
            histogram = macd_line - signal_line
            hist_vals = histogram.values
            # Detect cross
            if len(hist_vals) >= 2:
                if hist_vals[-1] > 0 and hist_vals[-2] <= 0:
                    signal = "bullish_cross"
                elif hist_vals[-1] < 0 and hist_vals[-2] >= 0:
                    signal = "bearish_cross"
                else:
                    signal = "bullish" if hist_vals[-1] > 0 else "bearish"
            else:
                signal = "neutral"
            return {
                "macd_signal": signal,
                "macd_histogram": round(float(histogram.iloc[-1]), 4),
            }
        except Exception:
            return {"macd_signal": "neutral", "macd_histogram": 0.0}

    def _atr(self, df: pd.DataFrame, period: int = 14) -> pd.Series | None:
        try:
            high = df["high"]
            low = df["low"]
            close = df["close"]
            tr1 = high - low
            tr2 = (high - close.shift(1)).abs()
            tr3 = (low - close.shift(1)).abs()
            tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            return tr.rolling(period).mean()
        except Exception:
            logger.exception("ATR calculation failed")
            return None

    def _bollinger(self, df: pd.DataFrame, period: int = 20, std_dev: float = 2.0) -> dict:
        try:
            sma = df["close"].rolling(period).mean()
            std = df["close"].rolling(period).std()
            upper = sma + std_dev * std
            lower = sma - std_dev * std
            return {
                "bollinger_upper": round(float(upper.iloc[-1]), 2),
                "bollinger_lower": round(float(lower.iloc[-1]), 2),
            }
        except Exception:
            return {"bollinger_upper": None, "bollinger_lower": None}

    def _keltner_squeeze(self, df: pd.DataFrame, atr_series: pd.Series | None) -> bool:
        try:
            if atr_series is None:
                return False
            ema20 = df["close"].ewm(span=20).mean()
            kelt_upper = ema20 + 1.5 * atr_series
            kelt_lower = ema20 - 1.5 * atr_series
            sma20 = df["close"].rolling(20).mean()
            std20 = df["close"].rolling(20).std()
            bb_upper = sma20 + 2 * std20
            bb_lower = sma20 - 2 * std20
            # Squeeze = BB inside Keltner
            return bool(bb_upper.iloc[-1] < kelt_upper.iloc[-1] and bb_lower.iloc[-1] > kelt_lower.iloc[-1])
        except Exception:
            return False

    def _obv(self, df: pd.DataFrame) -> float:
        try:
            direction = np.sign(df["close"].diff())
            obv = (direction * df["volume"]).cumsum()
            return round(float(obv.iloc[-1]), 2)
        except Exception:
            return 0.0

    def _vwap(self, df: pd.DataFrame) -> float:
        try:
            typical = (df["high"] + df["low"] + df["close"]) / 3
            cumvol = df["volume"].cumsum()
            cumtp = (typical * df["volume"]).cumsum()
            vwap = cumtp / cumvol.replace(0, np.nan)
            return round(float(vwap.iloc[-1]), 2)
        except Exception:
            return 0.0

    def _cvd(self, df: pd.DataFrame) -> float:
        try:
            delta = df["volume"].copy()
            delta[df["close"] < df["open"]] *= -1
            delta[df["close"] == df["open"]] = 0
            return round(float(delta.cumsum().iloc[-1]), 2)
        except Exception:
            return 0.0

    def _pivots(self, df: pd.DataFrame) -> dict:
        try:
            # Use previous day's data
            daily = df.resample("1D").agg({"high": "max", "low": "min", "close": "last"}).dropna()
            if len(daily) < 2:
                return {"pivot_point": None, "support_1": None, "resistance_1": None}
            prev = daily.iloc[-2]
            pp = (prev["high"] + prev["low"] + prev["close"]) / 3
            s1 = 2 * pp - prev["high"]
            r1 = 2 * pp - prev["low"]
            return {
                "pivot_point": round(float(pp), 2),
                "support_1": round(float(s1), 2),
                "resistance_1": round(float(r1), 2),
            }
        except Exception:
            return {"pivot_point": None, "support_1": None, "resistance_1": None}

    def _trend_strength(self, df: pd.DataFrame, indicators: dict) -> int:
        try:
            score = 50  # baseline
            close = float(df["close"].iloc[-1])
            # Price vs SMAs
            sma50 = indicators.get("sma_50")
            sma200 = indicators.get("sma_200")
            if sma50 and close > sma50:
                score += 10
            elif sma50:
                score -= 10
            if sma200 and close > sma200:
                score += 10
            elif sma200:
                score -= 10
            # Golden/Death cross
            if sma50 and sma200 and sma50 > sma200:
                score += 10
            elif sma50 and sma200:
                score -= 10
            # EMA alignment
            ema12 = indicators.get("ema_12", 0)
            ema26 = indicators.get("ema_26", 0)
            if ema12 > ema26:
                score += 5
            else:
                score -= 5
            # MACD
            if indicators.get("macd_signal") in ("bullish", "bullish_cross"):
                score += 5
            elif indicators.get("macd_signal") in ("bearish", "bearish_cross"):
                score -= 5
            # ADX approximation via directional movement
            try:
                high = df["high"].values
                low = df["low"].values
                plus_dm = np.maximum(high[1:] - high[:-1], 0)
                minus_dm = np.maximum(low[:-1] - low[1:], 0)
                mask = plus_dm > minus_dm
                plus_dm[~mask] = 0
                minus_dm[mask] = 0
                avg_plus = pd.Series(plus_dm).rolling(14).mean().iloc[-1]
                avg_minus = pd.Series(minus_dm).rolling(14).mean().iloc[-1]
                if avg_plus + avg_minus > 0:
                    dx = abs(avg_plus - avg_minus) / (avg_plus + avg_minus) * 100
                    if dx > 25:
                        score += 10
                    elif dx < 15:
                        score -= 5
            except Exception:
                pass

            return max(0, min(100, score))
        except Exception:
            return 50

    def _momentum_exhaustion(self, indicators: dict) -> str:
        rsi = indicators.get("rsi")
        macd_hist = indicators.get("macd_histogram", 0)
        if rsi is None:
            return "none"
        if rsi > 80 and macd_hist < 0:
            return "bearish_exhaustion"
        if rsi < 20 and macd_hist > 0:
            return "bullish_exhaustion"
        return "none"

    def _volatility_regime(self, df: pd.DataFrame, atr_series: pd.Series | None) -> str:
        if atr_series is None or len(atr_series) < 100:
            return "normal"
        try:
            recent = atr_series.dropna()
            if len(recent) < 50:
                return "normal"
            current = float(recent.iloc[-1])
            pct = float((recent < current).sum() / len(recent) * 100)
            if pct > 95:
                return "extreme"
            if pct > 75:
                return "high"
            if pct < 25:
                return "low"
            return "normal"
        except Exception:
            return "normal"

    # ──────────────────── Multi-Timeframe Confluence ───────────────

    @staticmethod
    def calculate_mtf_confluence(analyses: dict[str, dict]) -> int:
        """Count how many timeframes agree on direction. Input: {tf: analysis_result}."""
        if not analyses:
            return 0
        bullish = 0
        bearish = 0
        for _tf, a in analyses.items():
            signals = 0
            # MACD direction
            ms = a.get("macd_signal", "")
            if "bullish" in ms:
                signals += 1
            elif "bearish" in ms:
                signals -= 1
            # RSI position
            rsi = a.get("rsi")
            if rsi and rsi > 50:
                signals += 1
            elif rsi and rsi < 50:
                signals -= 1
            # Price vs SMA50
            close_val = None
            if a.get("symbol"):
                # We don't have close in the analysis, use SMA comparison
                sma50 = a.get("sma_50", 0)
                sma20 = a.get("sma_20", 0)
                if sma20 and sma50 and sma20 > sma50:
                    signals += 1
                elif sma20 and sma50:
                    signals -= 1
            if signals > 0:
                bullish += 1
            elif signals < 0:
                bearish += 1
        return max(bullish, bearish)

    # ──────────────────────── Serialization ────────────────────────

    def to_dict(self, analysis: dict) -> dict:
        return {
            "symbol": analysis.get("symbol"),
            "timeframe": analysis.get("timeframe"),
            "rsi": analysis.get("rsi"),
            "rsi_divergence": analysis.get("rsi_divergence"),
            "macd_signal": analysis.get("macd_signal"),
            "macd_histogram": analysis.get("macd_histogram"),
            "sma_20": analysis.get("sma_20"),
            "sma_50": analysis.get("sma_50"),
            "sma_200": analysis.get("sma_200"),
            "ema_12": analysis.get("ema_12"),
            "ema_26": analysis.get("ema_26"),
            "atr": analysis.get("atr"),
            "bollinger_upper": analysis.get("bollinger_upper"),
            "bollinger_lower": analysis.get("bollinger_lower"),
            "keltner_squeeze": analysis.get("keltner_squeeze"),
            "obv": analysis.get("obv"),
            "vwap": analysis.get("vwap"),
            "cvd": analysis.get("cvd"),
            "pivot_point": analysis.get("pivot_point"),
            "support_1": analysis.get("support_1"),
            "resistance_1": analysis.get("resistance_1"),
            "trend_strength_score": analysis.get("trend_strength_score"),
            "momentum_exhaustion": analysis.get("momentum_exhaustion"),
            "volatility_regime": analysis.get("volatility_regime"),
            "mtf_confluence_score": analysis.get("mtf_confluence_score"),
            "timestamp": analysis.get("timestamp"),
        }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    engine = TechnicalEngine()
    result = engine.analyze("BTC/USDT", "1h")
    for k, v in result.items():
        print(f"  {k}: {v}")
