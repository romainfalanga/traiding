"use client";

import { useRealtimeTrades } from "@/hooks/useRealtimeTrades";
import { formatCurrency, formatPct, classNames } from "@/lib/utils";

export default function LivePnL() {
  const { openTrades, loading } = useRealtimeTrades();

  const totalUnrealizedPnl = openTrades.reduce(
    (sum, t) => sum + (t.pnl ?? 0),
    0
  );
  const totalUnrealizedPct = openTrades.reduce(
    (sum, t) => sum + (t.pnl_pct ?? 0),
    0
  );

  const pnlColor =
    totalUnrealizedPnl > 0
      ? "text-green-400"
      : totalUnrealizedPnl < 0
        ? "text-red-400"
        : "text-gray-400";

  const bgColor =
    totalUnrealizedPnl > 0
      ? "border-green-500/20 bg-green-500/5"
      : totalUnrealizedPnl < 0
        ? "border-red-500/20 bg-red-500/5"
        : "border-gray-800 bg-gray-900";

  if (loading) {
    return (
      <div className="rounded-xl border border-gray-800 bg-gray-900 p-4 animate-pulse">
        <div className="flex items-center justify-between">
          <div className="h-4 w-32 rounded bg-gray-800" />
          <div className="h-6 w-24 rounded bg-gray-800" />
        </div>
      </div>
    );
  }

  if (openTrades.length === 0) {
    return (
      <div className="rounded-xl border border-gray-800 bg-gray-900 p-4">
        <div className="flex items-center justify-between">
          <span className="text-sm font-semibold uppercase tracking-wider text-gray-400">
            Live PnL
          </span>
          <span className="text-sm text-gray-500">No open positions</span>
        </div>
      </div>
    );
  }

  return (
    <div className={classNames("rounded-xl border p-4", bgColor)}>
      {/* Summary Row */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <span className="text-sm font-semibold uppercase tracking-wider text-gray-400">
            Live PnL
          </span>
          <span className="text-xs text-gray-500">
            {openTrades.length} open position{openTrades.length !== 1 ? "s" : ""}
          </span>
        </div>
        <div className="flex items-center gap-4">
          <span className={classNames("font-mono text-xl font-bold", pnlColor)}>
            {totalUnrealizedPnl >= 0 ? "+" : ""}
            {formatCurrency(totalUnrealizedPnl)}
          </span>
          <span className={classNames("font-mono text-sm", pnlColor)}>
            {formatPct(totalUnrealizedPct)}
          </span>
        </div>
      </div>

      {/* Individual Positions */}
      {openTrades.length > 0 && (
        <div className="mt-3 grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {openTrades.map((trade) => {
            const tradePnl = trade.pnl ?? 0;
            const color =
              tradePnl > 0
                ? "text-green-400"
                : tradePnl < 0
                  ? "text-red-400"
                  : "text-gray-400";
            return (
              <div
                key={trade.id}
                className="flex items-center justify-between rounded-lg bg-gray-800/50 px-3 py-2"
              >
                <div className="flex items-center gap-2">
                  <span
                    className={classNames(
                      "text-xs font-bold",
                      trade.side === "LONG" ? "text-green-400" : "text-red-400"
                    )}
                  >
                    {trade.side === "LONG" ? "L" : "S"}
                  </span>
                  <span className="text-xs font-medium text-gray-300">
                    {trade.symbol}
                  </span>
                </div>
                <span className={classNames("font-mono text-xs font-semibold", color)}>
                  {tradePnl >= 0 ? "+" : ""}
                  {formatCurrency(tradePnl)}
                </span>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
