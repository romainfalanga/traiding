"use client";

import { useEffect, useState, useMemo } from "react";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from "recharts";
import { supabase } from "@/lib/supabase";
import { Portfolio } from "@/lib/types";
import { formatCurrency } from "@/lib/utils";
import { format } from "date-fns";

interface EquityPoint {
  timestamp: string;
  label: string;
  equity: number;
}

interface EquityCurveProps {
  /** Pre-loaded portfolio history (newest first). Falls back to own fetch. */
  history?: Portfolio[];
}

export default function EquityCurve({ history }: EquityCurveProps) {
  const [data, setData] = useState<EquityPoint[]>([]);
  const [loading, setLoading] = useState(!history);

  useEffect(() => {
    if (history && history.length > 0) {
      const points: EquityPoint[] = [...history]
        .reverse()
        .map((p) => ({
          timestamp: p.timestamp,
          label: format(new Date(p.timestamp), "MMM d HH:mm"),
          equity: p.total_value,
        }));
      setData(points);
      setLoading(false);
      return;
    }

    async function fetchEquity() {
      setLoading(true);
      const { data: rows, error } = await supabase
        .from("portfolio")
        .select("total_value, timestamp")
        .order("timestamp", { ascending: true })
        .limit(200);

      if (!error && rows) {
        setData(
          rows.map((r: any) => ({
            timestamp: r.timestamp,
            label: format(new Date(r.timestamp), "MMM d HH:mm"),
            equity: r.total_value,
          }))
        );
      }
      setLoading(false);
    }

    fetchEquity();
  }, [history]);

  const startingBalance = useMemo(() => {
    if (data.length === 0) return 0;
    return data[0].equity;
  }, [data]);

  if (loading) {
    return (
      <div className="card h-72 animate-pulse">
        <div className="card-header">Equity Curve</div>
        <div className="h-56 rounded bg-gray-800/50" />
      </div>
    );
  }

  if (data.length === 0) {
    return (
      <div className="card flex h-72 items-center justify-center">
        <span className="text-sm text-gray-500">No equity data available</span>
      </div>
    );
  }

  return (
    <div className="card">
      <div className="card-header">Equity Curve</div>
      <ResponsiveContainer width="100%" height={240}>
        <AreaChart data={data} margin={{ top: 4, right: 4, bottom: 0, left: 0 }}>
          <defs>
            <linearGradient id="equityGreen" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#22c55e" stopOpacity={0.4} />
              <stop offset="100%" stopColor="#22c55e" stopOpacity={0} />
            </linearGradient>
            <linearGradient id="equityRed" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#ef4444" stopOpacity={0.4} />
              <stop offset="100%" stopColor="#ef4444" stopOpacity={0} />
            </linearGradient>
          </defs>

          <XAxis
            dataKey="label"
            tick={{ fill: "#6b7280", fontSize: 11 }}
            axisLine={false}
            tickLine={false}
            interval="preserveStartEnd"
          />
          <YAxis
            tick={{ fill: "#6b7280", fontSize: 11 }}
            axisLine={false}
            tickLine={false}
            tickFormatter={(v: number) => `$${(v / 1000).toFixed(0)}k`}
            domain={["auto", "auto"]}
            width={60}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: "#1f2937",
              border: "1px solid #374151",
              borderRadius: "8px",
              color: "#f3f4f6",
              fontSize: "12px",
            }}
            formatter={(value: number) => [formatCurrency(value), "Equity"]}
            labelFormatter={(label: string) => label}
          />

          <ReferenceLine
            y={startingBalance}
            stroke="#6b7280"
            strokeDasharray="3 3"
            strokeOpacity={0.5}
          />

          {/* Green fill for above starting balance */}
          <Area
            type="monotone"
            dataKey="equity"
            stroke="#22c55e"
            strokeWidth={2}
            fill="url(#equityGreen)"
            baseValue={startingBalance}
            isAnimationActive={false}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
