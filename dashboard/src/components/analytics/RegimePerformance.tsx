"use client";

import { useMemo } from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
  ReferenceLine,
} from "recharts";
import { Trade, RegimeType } from "@/lib/types";
import { formatCurrency } from "@/lib/utils";

interface RegimePerformanceProps {
  trades: Trade[];
}

const REGIMES: RegimeType[] = [
  "CAPITULATION",
  "FEAR",
  "NEUTRAL",
  "OPTIMISM",
  "EUPHORIA",
];

const REGIME_COLORS: Record<RegimeType, string> = {
  CAPITULATION: "#ef4444",
  FEAR: "#eab308",
  NEUTRAL: "#3b82f6",
  OPTIMISM: "#22c55e",
  EUPHORIA: "#f97316",
};

export default function RegimePerformance({ trades }: RegimePerformanceProps) {
  const chartData = useMemo(() => {
    return REGIMES.map((regime) => {
      const regimeTrades = trades.filter((t) => t.regime_at_entry === regime);
      const totalPnl = regimeTrades.reduce((s, t) => s + (t.pnl ?? 0), 0);
      const wins = regimeTrades.filter((t) => (t.pnl ?? 0) > 0).length;
      const winRate =
        regimeTrades.length > 0 ? (wins / regimeTrades.length) * 100 : 0;

      return {
        regime,
        pnl: totalPnl,
        tradeCount: regimeTrades.length,
        winRate,
        color: REGIME_COLORS[regime],
      };
    }).filter((d) => d.tradeCount > 0);
  }, [trades]);

  if (chartData.length === 0) {
    return (
      <div className="card">
        <div className="card-header">PnL by Regime</div>
        <p className="py-8 text-center text-sm text-gray-500">
          No trades with regime data available
        </p>
      </div>
    );
  }

  return (
    <div className="card">
      <div className="card-header">PnL by Regime</div>

      <ResponsiveContainer width="100%" height={300}>
        <BarChart
          data={chartData}
          margin={{ top: 8, right: 8, bottom: 0, left: 0 }}
        >
          <XAxis
            dataKey="regime"
            tick={{ fill: "#6b7280", fontSize: 11 }}
            axisLine={false}
            tickLine={false}
          />
          <YAxis
            tick={{ fill: "#6b7280", fontSize: 11 }}
            axisLine={false}
            tickLine={false}
            tickFormatter={(v: number) => `$${(v / 1000).toFixed(0)}k`}
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
            formatter={(value: number, _: string, props: any) => [
              `${formatCurrency(value)} (${props.payload.tradeCount} trades, ${props.payload.winRate.toFixed(0)}% WR)`,
              "PnL",
            ]}
          />
          <ReferenceLine y={0} stroke="#6b7280" strokeDasharray="3 3" />
          <Bar dataKey="pnl" radius={[6, 6, 0, 0]}>
            {chartData.map((entry, index) => (
              <Cell
                key={index}
                fill={entry.color}
                fillOpacity={0.8}
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
