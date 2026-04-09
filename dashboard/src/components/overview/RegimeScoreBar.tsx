"use client";

import { RegimeHistory, RegimeType } from "@/lib/types";
import { getRegimeColor, getRegimeBgColor, timeAgo, classNames } from "@/lib/utils";

interface RegimeScoreBarProps {
  regime: RegimeHistory | null;
  loading?: boolean;
}

const regimeLabelMap: Record<RegimeType, string> = {
  EUPHORIA: "Euphoria",
  OPTIMISM: "Optimism",
  NEUTRAL: "Neutral",
  FEAR: "Fear",
  CAPITULATION: "Capitulation",
};

/** Maps regime to a 0-100 position on the bar */
function regimeToPosition(regime: RegimeType): number {
  const map: Record<RegimeType, number> = {
    CAPITULATION: 10,
    FEAR: 30,
    NEUTRAL: 50,
    OPTIMISM: 70,
    EUPHORIA: 90,
  };
  return map[regime] ?? 50;
}

/** Returns bar gradient color class based on regime */
function regimeBarBg(regime: RegimeType): string {
  const map: Record<RegimeType, string> = {
    CAPITULATION: "bg-gradient-to-r from-red-600 to-red-400",
    FEAR: "bg-gradient-to-r from-yellow-600 to-yellow-400",
    NEUTRAL: "bg-gradient-to-r from-blue-600 to-blue-400",
    OPTIMISM: "bg-gradient-to-r from-green-600 to-green-400",
    EUPHORIA: "bg-gradient-to-r from-orange-600 to-orange-400",
  };
  return map[regime] ?? "bg-gray-600";
}

export default function RegimeScoreBar({ regime, loading }: RegimeScoreBarProps) {
  if (loading || !regime) {
    return (
      <div className="card animate-pulse">
        <div className="card-header">Market Regime</div>
        <div className="h-6 rounded-full bg-gray-800" />
      </div>
    );
  }

  const position = regimeToPosition(regime.regime);
  const confidence = regime.confidence ?? 0;

  return (
    <div className="card">
      <div className="card-header">Market Regime</div>

      {/* Regime label and confidence */}
      <div className="mb-3 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span
            className={classNames(
              "rounded-full px-3 py-0.5 text-sm font-semibold",
              getRegimeBgColor(regime.regime),
              getRegimeColor(regime.regime)
            )}
          >
            {regimeLabelMap[regime.regime]}
          </span>
          <span className="text-xs text-gray-500">
            {confidence.toFixed(0)}% confidence
          </span>
        </div>
        <span className="text-xs text-gray-500">
          since {timeAgo(regime.timestamp)}
        </span>
      </div>

      {/* Bar */}
      <div className="relative h-3 w-full overflow-hidden rounded-full bg-gray-800">
        {/* Gradient track */}
        <div
          className="absolute inset-0 bg-gradient-to-r from-red-500 via-yellow-400 via-blue-400 via-green-400 to-orange-400 opacity-30"
        />
        {/* Filled portion */}
        <div
          className={classNames("h-full rounded-full transition-all duration-700", regimeBarBg(regime.regime))}
          style={{ width: `${position}%` }}
        />
        {/* Indicator marker */}
        <div
          className="absolute top-1/2 h-5 w-1.5 -translate-y-1/2 rounded-full bg-white shadow-md transition-all duration-700"
          style={{ left: `${position}%` }}
        />
      </div>

      {/* Labels under bar */}
      <div className="mt-1 flex justify-between text-[10px] text-gray-600">
        <span>Capitulation</span>
        <span>Fear</span>
        <span>Neutral</span>
        <span>Optimism</span>
        <span>Euphoria</span>
      </div>
    </div>
  );
}
