"use client";

import { useEffect, useState } from "react";
import { supabase, subscribeToTable, unsubscribe } from "@/lib/supabase";
import { SentimentSnapshot } from "@/lib/types";
import { RealtimeChannel } from "@supabase/supabase-js";

function getLabel(value: number): string {
  if (value <= 20) return "Extreme Fear";
  if (value <= 40) return "Fear";
  if (value <= 60) return "Neutral";
  if (value <= 80) return "Greed";
  return "Extreme Greed";
}

function getNeedleColor(value: number): string {
  if (value <= 20) return "#ef4444";
  if (value <= 40) return "#f97316";
  if (value <= 60) return "#eab308";
  if (value <= 80) return "#84cc16";
  return "#22c55e";
}

interface FearGreedGaugeProps {
  value?: number | null;
}

export default function FearGreedGauge({ value: propValue }: FearGreedGaugeProps) {
  const [value, setValue] = useState<number | null>(propValue ?? null);
  const [loading, setLoading] = useState(propValue == null);

  useEffect(() => {
    if (propValue != null) {
      setValue(propValue);
      setLoading(false);
      return;
    }

    let channel: RealtimeChannel | null = null;

    async function fetch() {
      const { data, error } = await supabase
        .from("sentiment_snapshots")
        .select("fear_greed_index")
        .not("fear_greed_index", "is", null)
        .order("timestamp", { ascending: false })
        .limit(1)
        .single();

      if (!error && data) {
        setValue(data.fear_greed_index);
      }
      setLoading(false);
    }

    fetch();

    channel = subscribeToTable<SentimentSnapshot>("sentiment_snapshots", (payload) => {
      if (
        (payload.eventType === "INSERT" || payload.eventType === "UPDATE") &&
        payload.new.fear_greed_index != null
      ) {
        setValue(payload.new.fear_greed_index);
      }
    });

    return () => {
      if (channel) unsubscribe(channel);
    };
  }, [propValue]);

  if (loading || value == null) {
    return (
      <div className="card flex h-48 animate-pulse items-center justify-center">
        <div className="h-24 w-24 rounded-full bg-gray-800" />
      </div>
    );
  }

  const clampedValue = Math.max(0, Math.min(100, value));
  const angle = -90 + (clampedValue / 100) * 180; // -90 to 90 degrees
  const label = getLabel(clampedValue);
  const needleColor = getNeedleColor(clampedValue);

  return (
    <div className="card flex flex-col items-center">
      <div className="card-header w-full">Fear & Greed</div>

      <div className="relative h-28 w-48">
        {/* Semicircle gauge using SVG */}
        <svg viewBox="0 0 200 110" className="h-full w-full">
          {/* Background arc segments */}
          {/* Extreme Fear - Red */}
          <path
            d="M 20 100 A 80 80 0 0 1 52 37"
            fill="none"
            stroke="#ef4444"
            strokeWidth="12"
            strokeLinecap="round"
            opacity="0.3"
          />
          {/* Fear - Orange */}
          <path
            d="M 52 37 A 80 80 0 0 1 100 20"
            fill="none"
            stroke="#f97316"
            strokeWidth="12"
            strokeLinecap="round"
            opacity="0.3"
          />
          {/* Neutral - Yellow */}
          <path
            d="M 100 20 A 80 80 0 0 1 148 37"
            fill="none"
            stroke="#eab308"
            strokeWidth="12"
            strokeLinecap="round"
            opacity="0.3"
          />
          {/* Greed - Lime */}
          <path
            d="M 148 37 A 80 80 0 0 1 180 100"
            fill="none"
            stroke="#84cc16"
            strokeWidth="12"
            strokeLinecap="round"
            opacity="0.3"
          />
          {/* Extreme Greed - Green (overlay on greed) */}
          <path
            d="M 165 70 A 80 80 0 0 1 180 100"
            fill="none"
            stroke="#22c55e"
            strokeWidth="12"
            strokeLinecap="round"
            opacity="0.3"
          />

          {/* Needle */}
          <g transform={`rotate(${angle}, 100, 100)`}>
            <line
              x1="100"
              y1="100"
              x2="100"
              y2="30"
              stroke={needleColor}
              strokeWidth="2.5"
              strokeLinecap="round"
            />
          </g>

          {/* Center dot */}
          <circle cx="100" cy="100" r="5" fill={needleColor} />

          {/* Value text */}
          <text
            x="100"
            y="88"
            textAnchor="middle"
            fill="white"
            fontSize="22"
            fontWeight="bold"
            fontFamily="monospace"
          >
            {clampedValue}
          </text>
        </svg>
      </div>

      <span
        className="text-sm font-semibold"
        style={{ color: needleColor }}
      >
        {label}
      </span>
    </div>
  );
}
