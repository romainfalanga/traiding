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
} from "recharts";
import { Trade, AIDecision } from "@/lib/types";

interface AgentAgreementProps {
  trades: Trade[];
  decisions: AIDecision[];
}

interface AgreementBucket {
  level: string;
  winRate: number;
  totalTrades: number;
  color: string;
}

export default function AgentAgreement({
  trades,
  decisions,
}: AgentAgreementProps) {
  const chartData = useMemo(() => {
    // Group decisions by timestamp proximity (within 5 minutes = same round)
    const rounds: Map<string, AIDecision[]> = new Map();

    const sortedDecisions = [...decisions].sort(
      (a, b) =>
        new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
    );

    for (const d of sortedDecisions) {
      const time = new Date(d.timestamp).getTime();
      let assigned = false;

      for (const [key, group] of rounds) {
        const groupTime = new Date(key).getTime();
        if (Math.abs(time - groupTime) < 5 * 60 * 1000) {
          group.push(d);
          assigned = true;
          break;
        }
      }

      if (!assigned) {
        rounds.set(d.timestamp, [d]);
      }
    }

    // For each round, determine consensus level and check if trade was a win
    const tradeMap: Record<string, boolean> = {};
    for (const trade of trades) {
      tradeMap[trade.id] = (trade.pnl ?? 0) > 0;
    }

    const buckets = {
      "3/3 Agree": { wins: 0, total: 0 },
      "2/3 Agree": { wins: 0, total: 0 },
      "No Consensus": { wins: 0, total: 0 },
    };

    for (const [, group] of rounds) {
      if (group.length < 2) continue;

      const directions = group.map((d) => d.direction);
      const longCount = directions.filter((d) => d === "LONG").length;
      const shortCount = directions.filter((d) => d === "SHORT").length;
      const maxAgreement = Math.max(longCount, shortCount);

      let level: keyof typeof buckets;
      if (maxAgreement >= 3 || maxAgreement === group.length) {
        level = "3/3 Agree";
      } else if (maxAgreement >= 2) {
        level = "2/3 Agree";
      } else {
        level = "No Consensus";
      }

      // Find associated trade
      const tradeDecision = group.find(
        (d) => d.trade_id && tradeMap[d.trade_id] !== undefined
      );
      if (tradeDecision && tradeDecision.trade_id) {
        buckets[level].total += 1;
        if (tradeMap[tradeDecision.trade_id]) {
          buckets[level].wins += 1;
        }
      }
    }

    const colors = {
      "3/3 Agree": "#22c55e",
      "2/3 Agree": "#eab308",
      "No Consensus": "#ef4444",
    };

    return Object.entries(buckets)
      .map(([level, data]) => ({
        level,
        winRate: data.total > 0 ? (data.wins / data.total) * 100 : 0,
        totalTrades: data.total,
        color: colors[level as keyof typeof colors],
      }))
      .filter((d) => d.totalTrades > 0);
  }, [trades, decisions]);

  if (chartData.length === 0) {
    return (
      <div className="card">
        <div className="card-header">Agent Agreement vs Win Rate</div>
        <p className="py-8 text-center text-sm text-gray-500">
          Insufficient decision data for agreement analysis
        </p>
      </div>
    );
  }

  return (
    <div className="card">
      <div className="card-header">Agent Agreement vs Win Rate</div>

      <ResponsiveContainer width="100%" height={260}>
        <BarChart
          data={chartData}
          margin={{ top: 8, right: 8, bottom: 0, left: 0 }}
        >
          <XAxis
            dataKey="level"
            tick={{ fill: "#6b7280", fontSize: 11 }}
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
            formatter={(value: number, _: string, props: any) => [
              `${value.toFixed(1)}% (${props.payload.totalTrades} trades)`,
              "Win Rate",
            ]}
          />
          <Bar dataKey="winRate" radius={[6, 6, 0, 0]}>
            {chartData.map((entry, index) => (
              <Cell key={index} fill={entry.color} fillOpacity={0.8} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
