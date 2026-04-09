"use client";

import { classNames } from "@/lib/utils";

interface LiquidityPulseBarProps {
  score: number;
}

function getBarColor(score: number): string {
  if (score < 30) return "from-red-500 to-red-400";
  if (score < 60) return "from-yellow-500 to-yellow-400";
  return "from-green-500 to-green-400";
}

function getLabel(score: number): string {
  if (score < 20) return "Very Low";
  if (score < 40) return "Low";
  if (score < 60) return "Moderate";
  if (score < 80) return "Good";
  return "Excellent";
}

function getLabelColor(score: number): string {
  if (score < 30) return "text-red-400";
  if (score < 60) return "text-yellow-400";
  return "text-green-400";
}

export default function LiquidityPulseBar({ score }: LiquidityPulseBarProps) {
  const clamped = Math.max(0, Math.min(100, score));
  const label = getLabel(clamped);

  return (
    <div className="card">
      <div className="card-header">Liquidity Pulse</div>

      <div className="mb-2 flex items-center justify-between">
        <span className={classNames("text-sm font-semibold", getLabelColor(clamped))}>
          {label}
        </span>
        <span className="font-mono text-sm text-white">{clamped.toFixed(0)}</span>
      </div>

      <div className="relative h-3 w-full overflow-hidden rounded-full bg-gray-800">
        {/* Background gradient track for context */}
        <div className="absolute inset-0 bg-gradient-to-r from-red-500/20 via-yellow-500/20 to-green-500/20" />

        {/* Filled portion */}
        <div
          className={classNames(
            "h-full rounded-full bg-gradient-to-r transition-all duration-700",
            getBarColor(clamped)
          )}
          style={{ width: `${clamped}%` }}
        />
      </div>

      <div className="mt-1 flex justify-between text-[10px] text-gray-600">
        <span>0</span>
        <span>25</span>
        <span>50</span>
        <span>75</span>
        <span>100</span>
      </div>
    </div>
  );
}
