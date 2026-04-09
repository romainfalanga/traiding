"use client";

import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from "recharts";
import { BacktestResult } from "@/lib/types";
import { formatCurrency, formatPct, classNames } from "@/lib/utils";

interface BacktestResultsProps {
  result: BacktestResult | null;
  running: boolean;
}

export default function BacktestResults({
  result,
  running,
}: BacktestResultsProps) {
  if (running) {
    return (
      <div className="card flex items-center justify-center py-24">
        <div className="flex flex-col items-center gap-3">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-gray-600 border-t-blue-400" />
          <span className="text-sm text-gray-400">Running backtest...</span>
        </div>
      </div>
    );
  }

  if (!result) {
    return (
      <div className="card flex items-center justify-center py-24">
        <div className="text-center">
          <svg
            className="mx-auto h-12 w-12 text-gray-600"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={1}
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
            />
          </svg>
          <p className="mt-3 text-sm text-gray-500">
            Configure parameters and run a backtest to see results
          </p>
        </div>
      </div>
    );
  }

  const returnPnl = result.final_capital - result.initial_capital;
  const returnColor =
    returnPnl > 0
      ? "text-green-400"
      : returnPnl < 0
        ? "text-red-400"
        : "text-gray-400";

  // Build equity curve chart data
  const equityData =
    result.equity_curve?.map((value, i) => ({
      index: i,
      label: `Trade ${i}`,
      equity: value,
    })) ?? [];

  const stats = [
    {
      label: "Total Trades",
      value: String(result.total_trades),
      color: "text-white",
    },
    {
      label: "Win Rate",
      value: formatPct(result.win_rate, 1),
      color:
        result.win_rate >= 55
          ? "text-green-400"
          : result.win_rate >= 45
            ? "text-yellow-400"
            : "text-red-400",
    },
    {
      label: "Total Return",
      value: formatPct(result.total_return_pct, 2),
      color: returnColor,
    },
    {
      label: "Final Capital",
      value: formatCurrency(result.final_capital),
      color: returnColor,
    },
    {
      label: "Max Drawdown",
      value: formatPct(-result.max_drawdown, 2),
      color: "text-red-400",
    },
    {
      label: "Sharpe Ratio",
      value: result.sharpe_ratio?.toFixed(2) ?? "\u2014",
      color:
        (result.sharpe_ratio ?? 0) >= 1.5
          ? "text-green-400"
          : (result.sharpe_ratio ?? 0) >= 1.0
            ? "text-yellow-400"
            : "text-red-400",
    },
    {
      label: "Profit Factor",
      value: result.profit_factor?.toFixed(2) ?? "\u2014",
      color:
        (result.profit_factor ?? 0) >= 1.5
          ? "text-green-400"
          : "text-yellow-400",
    },
    {
      label: "Avg Trade PnL",
      value:
        result.avg_trade_pnl !== null
          ? formatCurrency(result.avg_trade_pnl)
          : "\u2014",
      color:
        (result.avg_trade_pnl ?? 0) > 0
          ? "text-green-400"
          : "text-red-400",
    },
    {
      label: "Avg Win",
      value:
        result.avg_win !== null ? formatCurrency(result.avg_win) : "\u2014",
      color: "text-green-400",
    },
    {
      label: "Avg Loss",
      value:
        result.avg_loss !== null ? formatCurrency(result.avg_loss) : "\u2014",
      color: "text-red-400",
    },
    {
      label: "Best Trade",
      value:
        result.best_trade !== null
          ? formatCurrency(result.best_trade)
          : "\u2014",
      color: "text-green-400",
    },
    {
      label: "Worst Trade",
      value:
        result.worst_trade !== null
          ? formatCurrency(result.worst_trade)
          : "\u2014",
      color: "text-red-400",
    },
  ];

  return (
    <div className="space-y-6">
      {/* Stats Grid */}
      <div className="card">
        <div className="card-header">Results Summary</div>
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
          {stats.map((stat) => (
            <div key={stat.label}>
              <span className="text-[10px] uppercase tracking-wider text-gray-500">
                {stat.label}
              </span>
              <p
                className={classNames(
                  "mt-0.5 font-mono text-lg font-bold",
                  stat.color
                )}
              >
                {stat.value}
              </p>
            </div>
          ))}
        </div>
      </div>

      {/* Equity Curve */}
      {equityData.length > 0 && (
        <div className="card">
          <div className="card-header">Backtest Equity Curve</div>
          <ResponsiveContainer width="100%" height={240}>
            <AreaChart
              data={equityData}
              margin={{ top: 4, right: 4, bottom: 0, left: 0 }}
            >
              <defs>
                <linearGradient id="btEquity" x1="0" y1="0" x2="0" y2="1">
                  <stop
                    offset="0%"
                    stopColor={returnPnl >= 0 ? "#22c55e" : "#ef4444"}
                    stopOpacity={0.4}
                  />
                  <stop
                    offset="100%"
                    stopColor={returnPnl >= 0 ? "#22c55e" : "#ef4444"}
                    stopOpacity={0}
                  />
                </linearGradient>
              </defs>
              <XAxis
                dataKey="label"
                tick={{ fill: "#6b7280", fontSize: 10 }}
                axisLine={false}
                tickLine={false}
                interval="preserveStartEnd"
              />
              <YAxis
                tick={{ fill: "#6b7280", fontSize: 11 }}
                axisLine={false}
                tickLine={false}
                tickFormatter={(v: number) => `$${(v / 1000).toFixed(1)}k`}
                domain={["auto", "auto"]}
                width={55}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: "#1f2937",
                  border: "1px solid #374151",
                  borderRadius: "8px",
                  color: "#f3f4f6",
                  fontSize: "12px",
                }}
                formatter={(value: number) => [
                  formatCurrency(value),
                  "Equity",
                ]}
              />
              <ReferenceLine
                y={result.initial_capital}
                stroke="#6b7280"
                strokeDasharray="3 3"
                strokeOpacity={0.5}
              />
              <Area
                type="monotone"
                dataKey="equity"
                stroke={returnPnl >= 0 ? "#22c55e" : "#ef4444"}
                strokeWidth={2}
                fill="url(#btEquity)"
                isAnimationActive={false}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}
