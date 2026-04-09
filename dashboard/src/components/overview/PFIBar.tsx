"use client";

import { classNames } from "@/lib/utils";

interface PFIBarProps {
  score: number;
}

function getBarColor(score: number): string {
  if (score >= 80) return "bg-green-400";
  if (score >= 60) return "bg-lime-400";
  if (score >= 40) return "bg-yellow-400";
  if (score >= 20) return "bg-orange-400";
  return "bg-red-400";
}

function getLabelColor(score: number): string {
  if (score >= 80) return "text-green-400";
  if (score >= 60) return "text-lime-400";
  if (score >= 40) return "text-yellow-400";
  if (score >= 20) return "text-orange-400";
  return "text-red-400";
}

function getLabel(score: number): string {
  if (score >= 80) return "Excellent";
  if (score >= 60) return "Good";
  if (score >= 40) return "Fair";
  if (score >= 20) return "Poor";
  return "Critical";
}

export default function PFIBar({ score }: PFIBarProps) {
  const clamped = Math.max(0, Math.min(100, score));

  return (
    <div className="card">
      <div className="card-header">Portfolio Fitness Index</div>

      <div className="mb-2 flex items-center justify-between">
        <span className={classNames("text-sm font-semibold", getLabelColor(clamped))}>
          {getLabel(clamped)}
        </span>
        <span className="font-mono text-lg font-bold text-white">
          {clamped.toFixed(0)}
        </span>
      </div>

      <div className="h-3 w-full overflow-hidden rounded-full bg-gray-800">
        <div
          className={classNames(
            "h-full rounded-full transition-all duration-700",
            getBarColor(clamped)
          )}
          style={{ width: `${clamped}%` }}
        />
      </div>

      <div className="mt-1 flex justify-between text-[10px] text-gray-600">
        <span>Critical</span>
        <span>Poor</span>
        <span>Fair</span>
        <span>Good</span>
        <span>Excellent</span>
      </div>
    </div>
  );
}
