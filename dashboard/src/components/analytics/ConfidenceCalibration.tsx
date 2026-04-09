"use client";

import { useMemo } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
  Legend,
} from "recharts";
import { Trade, AIDecision } from "@/lib/types";

interface ConfidenceCalibrationProps {
  trades: Trade[];
  decisions: AIDecision[];
}

interface CalibrationPoint {
  bucket: string;
  confidence: number;
  winRate: number;
}

export default function ConfidenceCalibration({
  trades,
  decisions,
}: ConfidenceCalibrationProps) {
  const chartData = useMemo(() => {
    // Map trade_id -> trade result
    const tradeMap: Record<string, boolean> = {};
    for (const trade of trades) {
      tradeMap[trade.id] = (trade.pnl ?? 0) > 0;
    }

    // Match decisions to trade outcomes
    const matchedDecisions = decisions
      .filter((d) => d.trade_id && tradeMap[d.trade_id] !== undefined)
      .map((d) => ({
        confidence: d.confidence,
        won: tradeMap[d.trade_id!],
      }));

    if (matchedDecisions.length === 0) return [];

    // Bucket into confidence ranges
    const buckets = [
      { min: 0, max: 0.4, label: "0-40%" },
      { min: 0.4, max: 0.5, label: "40-50%" },
      { min: 0.5, max: 0.6, label: "50-60%" },
      { min: 0.6, max: 0.7, label: "60-70%" },
      { min: 0.7, max: 0.8, label: "70-80%" },
      { min: 0.8, max: 0.9, label: "80-90%" },
      { min: 0.9, max: 1.01, label: "90-100%" },
    ];

    return buckets
      .map((bucket) => {
        const inBucket = matchedDecisions.filter(
          (d) => d.confidence >= bucket.min && d.confidence < bucket.max
        );
        if (inBucket.length === 0) return null;

        const wins = inBucket.filter((d) => d.won).length;
        return {
          bucket: bucket.label,
          confidence: ((bucket.min + bucket.max) / 2) * 100,
          winRate: (wins / inBucket.length) * 100,
        };
      })
      .filter(Boolean) as CalibrationPoint[];
  }, [trades, decisions]);

  if (chartData.length === 0) {
    return (
      <div className="card">
        <div className="card-header">Confidence Calibration</div>
        <p className="py-8 text-center text-sm text-gray-500">
          Insufficient data for calibration analysis
        </p>
      </div>
    );
  }

  return (
    <div className="card">
      <div className="card-header">Confidence Calibration</div>

      <ResponsiveContainer width="100%" height={260}>
        <LineChart
          data={chartData}
          margin={{ top: 8, right: 8, bottom: 0, left: 0 }}
        >
          <XAxis
            dataKey="bucket"
            tick={{ fill: "#6b7280", fontSize: 10 }}
            axisLine={false}
            tickLine={false}
          />
          <YAxis
            tick={{ fill: "#6b7280", fontSize: 11 }}
            axisLine={false}
            tickLine={false}
            domain={[0, 100]}
            tickFormatter={(v: number) => `${v}%`}
            width={45}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: "#1f2937",
              border: "1px solid #374151",
              borderRadius: "8px",
              color: "#f3f4f6",
              fontSize: "12px",
            }}
            formatter={(value: number, name: string) => [
              `${value.toFixed(1)}%`,
              name === "confidence" ? "Predicted" : "Actual Win Rate",
            ]}
          />
          <Legend
            wrapperStyle={{ fontSize: "11px", color: "#9ca3af" }}
          />

          {/* Perfect calibration line */}
          <ReferenceLine
            segment={[
              { x: chartData[0]?.bucket, y: 0 },
              { x: chartData[chartData.length - 1]?.bucket, y: 100 },
            ]}
            stroke="#6b7280"
            strokeDasharray="3 3"
            strokeOpacity={0.5}
          />

          <Line
            type="monotone"
            dataKey="confidence"
            name="Predicted"
            stroke="#3b82f6"
            strokeWidth={2}
            dot={{ r: 4, fill: "#3b82f6" }}
          />
          <Line
            type="monotone"
            dataKey="winRate"
            name="Actual Win Rate"
            stroke="#22c55e"
            strokeWidth={2}
            dot={{ r: 4, fill: "#22c55e" }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
