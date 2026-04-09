"use client";

import { classNames } from "@/lib/utils";

interface MarketBreadthBarsProps {
  sma50: number;
  sma200: number;
}

function barColor(pct: number): string {
  if (pct >= 60) return "bg-green-400";
  if (pct >= 40) return "bg-yellow-400";
  return "bg-red-400";
}

function labelColor(pct: number): string {
  if (pct >= 60) return "text-green-400";
  if (pct >= 40) return "text-yellow-400";
  return "text-red-400";
}

export default function MarketBreadthBars({
  sma50,
  sma200,
}: MarketBreadthBarsProps) {
  const clampedSma50 = Math.max(0, Math.min(100, sma50));
  const clampedSma200 = Math.max(0, Math.min(100, sma200));

  return (
    <div className="card">
      <div className="card-header">Market Breadth</div>

      <div className="space-y-4">
        {/* SMA 50 Bar */}
        <div>
          <div className="mb-1.5 flex items-center justify-between text-xs">
            <span className="text-gray-400">Above SMA 50</span>
            <span className={classNames("font-mono font-semibold", labelColor(clampedSma50))}>
              {clampedSma50.toFixed(1)}%
            </span>
          </div>
          <div className="h-2.5 w-full overflow-hidden rounded-full bg-gray-800">
            <div
              className={classNames(
                "h-full rounded-full transition-all duration-500",
                barColor(clampedSma50)
              )}
              style={{ width: `${clampedSma50}%` }}
            />
          </div>
        </div>

        {/* SMA 200 Bar */}
        <div>
          <div className="mb-1.5 flex items-center justify-between text-xs">
            <span className="text-gray-400">Above SMA 200</span>
            <span className={classNames("font-mono font-semibold", labelColor(clampedSma200))}>
              {clampedSma200.toFixed(1)}%
            </span>
          </div>
          <div className="h-2.5 w-full overflow-hidden rounded-full bg-gray-800">
            <div
              className={classNames(
                "h-full rounded-full transition-all duration-500",
                barColor(clampedSma200)
              )}
              style={{ width: `${clampedSma200}%` }}
            />
          </div>
        </div>
      </div>
    </div>
  );
}
