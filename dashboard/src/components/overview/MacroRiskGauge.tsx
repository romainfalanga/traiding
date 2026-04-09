"use client";

import { useEffect, useState } from "react";
import { supabase, subscribeToTable, unsubscribe } from "@/lib/supabase";
import { RegimeHistory } from "@/lib/types";
import { RealtimeChannel } from "@supabase/supabase-js";

function getRiskColor(score: number): string {
  if (score < 30) return "#ef4444"; // Red - high risk
  if (score < 70) return "#eab308"; // Yellow - moderate
  return "#22c55e"; // Green - low risk
}

function getRiskLabel(score: number): string {
  if (score < 30) return "High Risk";
  if (score < 70) return "Moderate";
  return "Low Risk";
}

interface MacroRiskGaugeProps {
  score?: number | null;
}

export default function MacroRiskGauge({ score: propScore }: MacroRiskGaugeProps) {
  const [score, setScore] = useState<number | null>(propScore ?? null);
  const [loading, setLoading] = useState(propScore == null);

  useEffect(() => {
    if (propScore != null) {
      setScore(propScore);
      setLoading(false);
      return;
    }

    let channel: RealtimeChannel | null = null;

    async function fetch() {
      const { data, error } = await supabase
        .from("regime_history")
        .select("composite_score")
        .not("composite_score", "is", null)
        .order("timestamp", { ascending: false })
        .limit(1)
        .single();

      if (!error && data) {
        setScore(data.composite_score);
      }
      setLoading(false);
    }

    fetch();

    channel = subscribeToTable<RegimeHistory>("regime_history", (payload) => {
      if (
        (payload.eventType === "INSERT" || payload.eventType === "UPDATE") &&
        payload.new.composite_score != null
      ) {
        setScore(payload.new.composite_score);
      }
    });

    return () => {
      if (channel) unsubscribe(channel);
    };
  }, [propScore]);

  if (loading || score == null) {
    return (
      <div className="card flex h-48 animate-pulse items-center justify-center">
        <div className="h-24 w-24 rounded-full bg-gray-800" />
      </div>
    );
  }

  const clamped = Math.max(0, Math.min(100, score));
  const angle = -90 + (clamped / 100) * 180;
  const color = getRiskColor(clamped);
  const label = getRiskLabel(clamped);

  // Build arc for the filled portion
  const startAngle = -90;
  const endAngle = angle;
  const cx = 100;
  const cy = 100;
  const r = 75;

  const startRad = (startAngle * Math.PI) / 180;
  const endRad = (endAngle * Math.PI) / 180;

  const x1 = cx + r * Math.cos(startRad);
  const y1 = cy + r * Math.sin(startRad);
  const x2 = cx + r * Math.cos(endRad);
  const y2 = cy + r * Math.sin(endRad);

  const largeArc = endAngle - startAngle > 180 ? 1 : 0;

  return (
    <div className="card flex flex-col items-center">
      <div className="card-header w-full">Macro Risk</div>

      <div className="relative h-28 w-48">
        <svg viewBox="0 0 200 110" className="h-full w-full">
          {/* Background track */}
          <path
            d="M 25 100 A 75 75 0 0 1 175 100"
            fill="none"
            stroke="#1f2937"
            strokeWidth="14"
            strokeLinecap="round"
          />

          {/* Filled arc */}
          {clamped > 0 && (
            <path
              d={`M ${x1} ${y1} A ${r} ${r} 0 ${largeArc} 1 ${x2} ${y2}`}
              fill="none"
              stroke={color}
              strokeWidth="14"
              strokeLinecap="round"
              opacity="0.8"
            />
          )}

          {/* Needle */}
          <g transform={`rotate(${angle}, ${cx}, ${cy})`}>
            <line
              x1={cx}
              y1={cy}
              x2={cx}
              y2="35"
              stroke="white"
              strokeWidth="2"
              strokeLinecap="round"
              opacity="0.9"
            />
          </g>

          {/* Center dot */}
          <circle cx={cx} cy={cy} r="4" fill="white" />

          {/* Score text */}
          <text
            x={cx}
            y="88"
            textAnchor="middle"
            fill="white"
            fontSize="22"
            fontWeight="bold"
            fontFamily="monospace"
          >
            {clamped.toFixed(0)}
          </text>
        </svg>
      </div>

      <span className="text-sm font-semibold" style={{ color }}>
        {label}
      </span>
    </div>
  );
}
