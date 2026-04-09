"use client";

import { useEffect, useState } from "react";
import { supabase } from "@/lib/supabase";
import { TechnicalSnapshot } from "@/lib/types";
import { classNames, formatNumber } from "@/lib/utils";

function trendIcon(direction: string | null): { label: string; color: string } {
  switch (direction) {
    case "UP":
    case "BULLISH":
      return { label: "Bullish", color: "text-green-400" };
    case "DOWN":
    case "BEARISH":
      return { label: "Bearish", color: "text-red-400" };
    default:
      return { label: "Neutral", color: "text-gray-400" };
  }
}

function rsiColor(rsi: number): string {
  if (rsi >= 70) return "text-red-400";
  if (rsi <= 30) return "text-green-400";
  return "text-yellow-400";
}

function rsiLabel(rsi: number): string {
  if (rsi >= 70) return "Overbought";
  if (rsi <= 30) return "Oversold";
  return "Neutral";
}

function macdSignal(histogram: number | null): { label: string; color: string } {
  if (histogram === null) return { label: "--", color: "text-gray-500" };
  if (histogram > 0) return { label: "Bullish", color: "text-green-400" };
  if (histogram < 0) return { label: "Bearish", color: "text-red-400" };
  return { label: "Neutral", color: "text-gray-400" };
}

export default function TechnicalSummary() {
  const [snapshot, setSnapshot] = useState<TechnicalSnapshot | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetch() {
      try {
        const { data, error } = await supabase
          .from("technical_snapshots")
          .select("*")
          .eq("symbol", "BTCUSDT")
          .order("timestamp", { ascending: false })
          .limit(1)
          .single();

        if (!error && data) {
          setSnapshot(data as TechnicalSnapshot);
        }
      } catch {
        // Silently fail
      } finally {
        setLoading(false);
      }
    }

    fetch();
    const interval = setInterval(fetch, 15_000);
    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return (
      <div className="card animate-pulse">
        <div className="card-header">Technical Summary</div>
        <div className="grid grid-cols-2 gap-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="h-10 rounded bg-gray-800" />
          ))}
        </div>
      </div>
    );
  }

  if (!snapshot) {
    return (
      <div className="card">
        <div className="card-header">Technical Summary</div>
        <p className="text-center text-sm text-gray-500 py-4">
          No technical data available
        </p>
      </div>
    );
  }

  const rsi = snapshot.rsi;
  const macd = macdSignal(snapshot.macd_histogram);
  const trend = trendIcon(snapshot.trend_direction);
  const atr = snapshot.atr;
  const adx = snapshot.adx;
  const trendStrength = snapshot.trend_strength;

  // Compute a simple MTF score (-100 to 100) from available indicators
  let mtfScore = 0;
  if (rsi !== null) {
    if (rsi > 50) mtfScore += 20;
    else if (rsi < 50) mtfScore -= 20;
  }
  if (snapshot.macd_histogram !== null) {
    mtfScore += snapshot.macd_histogram > 0 ? 25 : -25;
  }
  if (snapshot.trend_direction === "UP" || snapshot.trend_direction === "BULLISH") {
    mtfScore += 30;
  } else if (snapshot.trend_direction === "DOWN" || snapshot.trend_direction === "BEARISH") {
    mtfScore -= 30;
  }
  if (trendStrength !== null) {
    mtfScore += trendStrength > 50 ? 25 : trendStrength > 25 ? 10 : -10;
  }
  mtfScore = Math.max(-100, Math.min(100, mtfScore));

  return (
    <div className="card">
      <div className="card-header">Technical Summary</div>

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
        {/* RSI */}
        <div className="rounded-lg bg-gray-800/50 p-3">
          <span className="text-[10px] uppercase tracking-wider text-gray-500">
            RSI (14)
          </span>
          <div className="mt-1 flex items-baseline gap-1.5">
            <span
              className={classNames(
                "font-mono text-lg font-bold",
                rsi !== null ? rsiColor(rsi) : "text-gray-500"
              )}
            >
              {rsi !== null ? rsi.toFixed(1) : "--"}
            </span>
            {rsi !== null && (
              <span className={classNames("text-[10px]", rsiColor(rsi))}>
                {rsiLabel(rsi)}
              </span>
            )}
          </div>
        </div>

        {/* MACD */}
        <div className="rounded-lg bg-gray-800/50 p-3">
          <span className="text-[10px] uppercase tracking-wider text-gray-500">
            MACD
          </span>
          <div className="mt-1">
            <span className={classNames("font-mono text-lg font-bold", macd.color)}>
              {macd.label}
            </span>
          </div>
        </div>

        {/* Trend */}
        <div className="rounded-lg bg-gray-800/50 p-3">
          <span className="text-[10px] uppercase tracking-wider text-gray-500">
            Trend
          </span>
          <div className="mt-1">
            <span className={classNames("font-mono text-lg font-bold", trend.color)}>
              {trend.label}
            </span>
          </div>
        </div>

        {/* ATR */}
        <div className="rounded-lg bg-gray-800/50 p-3">
          <span className="text-[10px] uppercase tracking-wider text-gray-500">
            ATR
          </span>
          <div className="mt-1">
            <span className="font-mono text-lg font-bold text-white">
              {atr !== null ? formatNumber(atr, 1) : "--"}
            </span>
          </div>
        </div>

        {/* ADX (Volatility / Trend Strength) */}
        <div className="rounded-lg bg-gray-800/50 p-3">
          <span className="text-[10px] uppercase tracking-wider text-gray-500">
            ADX
          </span>
          <div className="mt-1 flex items-baseline gap-1.5">
            <span className="font-mono text-lg font-bold text-white">
              {adx !== null ? adx.toFixed(1) : "--"}
            </span>
            {adx !== null && (
              <span
                className={classNames(
                  "text-[10px]",
                  adx >= 25 ? "text-green-400" : "text-gray-500"
                )}
              >
                {adx >= 25 ? "Trending" : "Ranging"}
              </span>
            )}
          </div>
        </div>

        {/* MTF Score */}
        <div className="rounded-lg bg-gray-800/50 p-3">
          <span className="text-[10px] uppercase tracking-wider text-gray-500">
            MTF Score
          </span>
          <div className="mt-1">
            <span
              className={classNames(
                "font-mono text-lg font-bold",
                mtfScore > 20
                  ? "text-green-400"
                  : mtfScore < -20
                    ? "text-red-400"
                    : "text-yellow-400"
              )}
            >
              {mtfScore > 0 ? "+" : ""}
              {mtfScore}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
