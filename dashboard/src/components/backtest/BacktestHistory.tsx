"use client";

import { useEffect, useState } from "react";
import { supabase } from "@/lib/supabase";
import { BacktestResult } from "@/lib/types";
import { formatCurrency, formatPct, classNames, timeAgo } from "@/lib/utils";

export default function BacktestHistory() {
  const [backtests, setBacktests] = useState<BacktestResult[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchHistory() {
      try {
        const { data, error } = await supabase
          .from("backtest_results")
          .select("*")
          .order("created_at", { ascending: false })
          .limit(20);

        if (!error && data) {
          setBacktests(data as BacktestResult[]);
        }
      } catch {
        // Silently fail
      } finally {
        setLoading(false);
      }
    }

    fetchHistory();
  }, []);

  if (loading) {
    return (
      <div className="card animate-pulse">
        <div className="card-header">Backtest History</div>
        <div className="space-y-3">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="h-10 rounded bg-gray-800" />
          ))}
        </div>
      </div>
    );
  }

  if (backtests.length === 0) {
    return (
      <div className="card">
        <div className="card-header">Backtest History</div>
        <p className="py-8 text-center text-sm text-gray-500">
          No previous backtests found
        </p>
      </div>
    );
  }

  return (
    <div className="card overflow-hidden p-0">
      <div className="px-4 pt-4">
        <div className="card-header">Backtest History</div>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full">
          <thead className="border-b border-gray-800 bg-gray-900/50">
            <tr>
              <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-400">
                Date
              </th>
              <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-400">
                Strategy
              </th>
              <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-400">
                Period
              </th>
              <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-400">
                Trades
              </th>
              <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-400">
                Win Rate
              </th>
              <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-400">
                Return
              </th>
              <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-400">
                Max DD
              </th>
              <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-400">
                Sharpe
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-800/50">
            {backtests.map((bt) => {
              const returnColor =
                bt.total_return_pct > 0
                  ? "text-green-400"
                  : bt.total_return_pct < 0
                    ? "text-red-400"
                    : "text-gray-400";

              return (
                <tr
                  key={bt.id}
                  className="transition-colors hover:bg-gray-800/30"
                >
                  <td className="px-4 py-3 text-xs text-gray-400">
                    {timeAgo(bt.created_at)}
                  </td>
                  <td className="px-4 py-3 text-sm font-medium text-white">
                    {bt.strategy_name}
                  </td>
                  <td className="px-4 py-3 text-xs text-gray-400">
                    {bt.start_date} to {bt.end_date}
                  </td>
                  <td className="px-4 py-3 font-mono text-sm text-white">
                    {bt.total_trades}
                  </td>
                  <td className="px-4 py-3">
                    <span
                      className={classNames(
                        "font-mono text-sm",
                        bt.win_rate >= 55
                          ? "text-green-400"
                          : bt.win_rate >= 45
                            ? "text-yellow-400"
                            : "text-red-400"
                      )}
                    >
                      {formatPct(bt.win_rate, 1)}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <span
                      className={classNames(
                        "font-mono text-sm font-semibold",
                        returnColor
                      )}
                    >
                      {formatPct(bt.total_return_pct, 2)}
                    </span>
                  </td>
                  <td className="px-4 py-3 font-mono text-sm text-red-400">
                    {formatPct(-bt.max_drawdown, 2)}
                  </td>
                  <td className="px-4 py-3 font-mono text-sm text-gray-300">
                    {bt.sharpe_ratio?.toFixed(2) ?? "\u2014"}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
