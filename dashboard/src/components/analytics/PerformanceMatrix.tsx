"use client";

import { useMemo } from "react";
import { Trade, RegimeType } from "@/lib/types";
import { formatCurrency, classNames } from "@/lib/utils";

interface PerformanceMatrixProps {
  trades: Trade[];
}

const REGIMES: RegimeType[] = [
  "EUPHORIA",
  "OPTIMISM",
  "NEUTRAL",
  "FEAR",
  "CAPITULATION",
];

export default function PerformanceMatrix({ trades }: PerformanceMatrixProps) {
  const matrix = useMemo(() => {
    // Group trades by regime
    const regimeMap: Record<string, { totalPnl: number; count: number }> = {};

    for (const regime of REGIMES) {
      regimeMap[regime] = { totalPnl: 0, count: 0 };
    }

    for (const trade of trades) {
      const regime = trade.regime_at_entry;
      if (regime && regimeMap[regime]) {
        regimeMap[regime].totalPnl += trade.pnl ?? 0;
        regimeMap[regime].count += 1;
      }
    }

    return regimeMap;
  }, [trades]);

  // Find max absolute PnL for color scaling
  const maxPnl = Math.max(
    1,
    ...Object.values(matrix).map((v) => Math.abs(v.totalPnl))
  );

  function getCellColor(pnl: number): string {
    if (pnl === 0) return "bg-gray-800";
    const intensity = Math.min(Math.abs(pnl) / maxPnl, 1);
    if (pnl > 0) {
      const opacity = Math.round(intensity * 40 + 10);
      return `bg-green-500/${opacity}`;
    }
    const opacity = Math.round(intensity * 40 + 10);
    return `bg-red-500/${opacity}`;
  }

  if (trades.length === 0) {
    return (
      <div className="card">
        <div className="card-header">Performance Matrix</div>
        <p className="py-8 text-center text-sm text-gray-500">
          No closed trades to analyze
        </p>
      </div>
    );
  }

  return (
    <div className="card">
      <div className="card-header">Performance by Regime</div>

      <div className="grid grid-cols-1 gap-2">
        {REGIMES.map((regime) => {
          const data = matrix[regime];
          const pnlColor =
            data.totalPnl > 0
              ? "text-green-400"
              : data.totalPnl < 0
                ? "text-red-400"
                : "text-gray-500";

          return (
            <div
              key={regime}
              className={classNames(
                "flex items-center justify-between rounded-lg px-4 py-3",
                data.totalPnl > 0
                  ? "bg-green-500/10"
                  : data.totalPnl < 0
                    ? "bg-red-500/10"
                    : "bg-gray-800/50"
              )}
            >
              <div className="flex items-center gap-3">
                <span className="text-sm font-medium text-gray-300 w-28">
                  {regime}
                </span>
                <span className="text-xs text-gray-500">
                  {data.count} trade{data.count !== 1 ? "s" : ""}
                </span>
              </div>
              <span
                className={classNames("font-mono text-sm font-semibold", pnlColor)}
              >
                {data.totalPnl !== 0
                  ? `${data.totalPnl > 0 ? "+" : ""}${formatCurrency(data.totalPnl)}`
                  : "\u2014"}
              </span>
            </div>
          );
        })}
      </div>

      {/* Summary */}
      <div className="mt-4 flex items-center justify-between border-t border-gray-800 pt-3">
        <span className="text-xs text-gray-500">
          Total: {trades.length} trades across all regimes
        </span>
        <span
          className={classNames(
            "font-mono text-sm font-bold",
            trades.reduce((s, t) => s + (t.pnl ?? 0), 0) > 0
              ? "text-green-400"
              : "text-red-400"
          )}
        >
          {formatCurrency(trades.reduce((s, t) => s + (t.pnl ?? 0), 0))}
        </span>
      </div>
    </div>
  );
}
