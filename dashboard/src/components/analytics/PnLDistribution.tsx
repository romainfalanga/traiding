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
import { Trade } from "@/lib/types";
import { formatCurrency } from "@/lib/utils";

interface PnLDistributionProps {
  trades: Trade[];
}

export default function PnLDistribution({ trades }: PnLDistributionProps) {
  const chartData = useMemo(() => {
    if (trades.length === 0) return [];

    const pnls = trades.map((t) => t.pnl ?? 0).filter((p) => p !== 0);
    if (pnls.length === 0) return [];

    const min = Math.min(...pnls);
    const max = Math.max(...pnls);
    const range = max - min;
    const binCount = Math.min(20, Math.max(5, Math.ceil(Math.sqrt(pnls.length))));
    const binSize = range / binCount || 1;

    const bins: { range: string; count: number; midpoint: number }[] = [];
    for (let i = 0; i < binCount; i++) {
      const low = min + i * binSize;
      const high = low + binSize;
      const count = pnls.filter((p) => p >= low && (i === binCount - 1 ? p <= high : p < high)).length;
      bins.push({
        range: `${formatCurrency(low, 0)}`,
        count,
        midpoint: (low + high) / 2,
      });
    }

    return bins;
  }, [trades]);

  if (trades.length === 0 || chartData.length === 0) {
    return (
      <div className="card">
        <div className="card-header">PnL Distribution</div>
        <p className="py-8 text-center text-sm text-gray-500">
          No trade data available
        </p>
      </div>
    );
  }

  return (
    <div className="card">
      <div className="card-header">PnL Distribution</div>

      <ResponsiveContainer width="100%" height={260}>
        <BarChart data={chartData} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
          <XAxis
            dataKey="range"
            tick={{ fill: "#6b7280", fontSize: 10 }}
            axisLine={false}
            tickLine={false}
            interval="preserveStartEnd"
          />
          <YAxis
            tick={{ fill: "#6b7280", fontSize: 11 }}
            axisLine={false}
            tickLine={false}
            allowDecimals={false}
            width={30}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: "#1f2937",
              border: "1px solid #374151",
              borderRadius: "8px",
              color: "#f3f4f6",
              fontSize: "12px",
            }}
            formatter={(value: number) => [`${value} trades`, "Count"]}
          />
          <ReferenceLine x={0} stroke="#6b7280" strokeDasharray="3 3" />
          <Bar dataKey="count" radius={[4, 4, 0, 0]}>
            {chartData.map((entry, index) => (
              <Cell
                key={index}
                fill={entry.midpoint >= 0 ? "#22c55e" : "#ef4444"}
                fillOpacity={0.7}
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
