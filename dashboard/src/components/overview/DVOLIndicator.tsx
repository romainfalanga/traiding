"use client";

import { classNames } from "@/lib/utils";

interface DVOLIndicatorProps {
  dvol: number;
  percentile: number;
}

function getPercentileColor(percentile: number): string {
  if (percentile >= 80) return "text-red-400";
  if (percentile >= 60) return "text-orange-400";
  if (percentile >= 40) return "text-yellow-400";
  if (percentile >= 20) return "text-green-400";
  return "text-blue-400";
}

function getPercentileLabel(percentile: number): string {
  if (percentile >= 80) return "Extreme";
  if (percentile >= 60) return "High";
  if (percentile >= 40) return "Moderate";
  if (percentile >= 20) return "Low";
  return "Very Low";
}

export default function DVOLIndicator({ dvol, percentile }: DVOLIndicatorProps) {
  const clampedPercentile = Math.max(0, Math.min(100, percentile));

  return (
    <div className="card">
      <div className="card-header">BTC DVOL</div>

      <div className="flex items-end justify-between">
        <div>
          <span className="stat-value text-white">{dvol.toFixed(1)}</span>
          <span className="ml-1 text-xs text-gray-500">IV</span>
        </div>
        <div className="text-right">
          <span
            className={classNames(
              "text-lg font-bold",
              getPercentileColor(clampedPercentile)
            )}
          >
            {clampedPercentile.toFixed(0)}th
          </span>
          <span className="ml-1 text-xs text-gray-500">pctl</span>
        </div>
      </div>

      {/* Percentile bar */}
      <div className="mt-3 relative h-2 w-full overflow-hidden rounded-full bg-gray-800">
        <div
          className={classNames(
            "h-full rounded-full transition-all duration-500",
            clampedPercentile >= 80
              ? "bg-red-400"
              : clampedPercentile >= 60
                ? "bg-orange-400"
                : clampedPercentile >= 40
                  ? "bg-yellow-400"
                  : "bg-green-400"
          )}
          style={{ width: `${clampedPercentile}%` }}
        />
      </div>

      <div className="mt-1.5 flex items-center justify-between text-xs">
        <span className="text-gray-500">Volatility Regime</span>
        <span className={classNames("font-semibold", getPercentileColor(clampedPercentile))}>
          {getPercentileLabel(clampedPercentile)}
        </span>
      </div>
    </div>
  );
}
