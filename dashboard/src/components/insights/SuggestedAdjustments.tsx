"use client";

import { useMemo, useState } from "react";
import { PostTradeAnalysis } from "@/lib/types";
import { classNames } from "@/lib/utils";

interface PostTradeWithTrade extends PostTradeAnalysis {
  trade?: any;
}

interface SuggestedAdjustmentsProps {
  analyses: PostTradeWithTrade[];
}

interface Adjustment {
  id: string;
  parameter: string;
  currentValue: string;
  suggestedValue: string;
  reason: string;
  impact: "high" | "medium" | "low";
}

export default function SuggestedAdjustments({
  analyses,
}: SuggestedAdjustmentsProps) {
  const [appliedIds, setAppliedIds] = useState<Set<string>>(new Set());

  const adjustments = useMemo(() => {
    if (analyses.length === 0) return [];

    // Analyze patterns to generate suggestions
    const suggestions: Adjustment[] = [];

    // Check for poor exit quality
    const poorExits = analyses.filter(
      (a) => a.exit_quality !== null && a.exit_quality < 5
    );
    if (poorExits.length >= 3) {
      suggestions.push({
        id: "exit-quality",
        parameter: "Take Profit Strategy",
        currentValue: "Fixed R:R",
        suggestedValue: "Trailing Stop + ATR",
        reason: `${poorExits.length} trades had poor exit quality (< 5/10). Consider trailing stops.`,
        impact: "high",
      });
    }

    // Check for poor timing
    const poorTiming = analyses.filter(
      (a) => a.timing_score !== null && a.timing_score < 5
    );
    if (poorTiming.length >= 3) {
      suggestions.push({
        id: "timing-score",
        parameter: "Entry Timing",
        currentValue: "Immediate",
        suggestedValue: "Limit Order with 0.3% offset",
        reason: `${poorTiming.length} trades had poor timing scores. Use limit orders for better fills.`,
        impact: "medium",
      });
    }

    // Check for regime misalignment
    const misaligned = analyses.filter(
      (a) => a.regime_alignment === false
    );
    if (misaligned.length >= 2) {
      suggestions.push({
        id: "regime-alignment",
        parameter: "Regime Filter",
        currentValue: "Disabled",
        suggestedValue: "Enable strict regime filtering",
        reason: `${misaligned.length} trades were misaligned with the market regime.`,
        impact: "high",
      });
    }

    // Check for poor risk management
    const poorRisk = analyses.filter(
      (a) => a.risk_management_score !== null && a.risk_management_score < 5
    );
    if (poorRisk.length >= 2) {
      suggestions.push({
        id: "risk-mgmt",
        parameter: "Position Size",
        currentValue: "2% of portfolio",
        suggestedValue: "1.5% of portfolio",
        reason: `${poorRisk.length} trades had poor risk management scores. Reduce position sizing.`,
        impact: "medium",
      });
    }

    // Default suggestion if nothing else
    if (suggestions.length === 0) {
      suggestions.push({
        id: "confidence",
        parameter: "Confidence Threshold",
        currentValue: "65%",
        suggestedValue: "70%",
        reason:
          "Consider raising the confidence threshold to filter out marginal setups.",
        impact: "low",
      });
    }

    return suggestions;
  }, [analyses]);

  const handleApply = (id: string) => {
    setAppliedIds((prev) => new Set([...prev, id]));
  };

  const impactColor: Record<string, { text: string; bg: string }> = {
    high: { text: "text-red-400", bg: "bg-red-400/10" },
    medium: { text: "text-yellow-400", bg: "bg-yellow-400/10" },
    low: { text: "text-blue-400", bg: "bg-blue-400/10" },
  };

  return (
    <div className="card">
      <div className="card-header">Suggested Adjustments</div>

      <div className="space-y-3">
        {adjustments.map((adj) => {
          const isApplied = appliedIds.has(adj.id);
          const colors = impactColor[adj.impact];

          return (
            <div
              key={adj.id}
              className={classNames(
                "rounded-lg border p-3 transition-all",
                isApplied
                  ? "border-green-500/20 bg-green-500/5 opacity-60"
                  : "border-gray-700 bg-gray-800/30"
              )}
            >
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-semibold text-white">
                      {adj.parameter}
                    </span>
                    <span
                      className={classNames(
                        "rounded-full px-1.5 py-0.5 text-[10px] font-semibold uppercase",
                        colors.text,
                        colors.bg
                      )}
                    >
                      {adj.impact}
                    </span>
                  </div>

                  <div className="mt-1.5 flex items-center gap-2 text-xs">
                    <span className="text-gray-500 line-through">
                      {adj.currentValue}
                    </span>
                    <svg
                      className="h-3 w-3 text-gray-600"
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                      strokeWidth={2}
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        d="M13 7l5 5m0 0l-5 5m5-5H6"
                      />
                    </svg>
                    <span className="font-medium text-blue-400">
                      {adj.suggestedValue}
                    </span>
                  </div>

                  <p className="mt-1.5 text-[10px] text-gray-400 leading-relaxed">
                    {adj.reason}
                  </p>
                </div>
              </div>

              <button
                onClick={() => handleApply(adj.id)}
                disabled={isApplied}
                className={classNames(
                  "mt-2 w-full rounded-md px-3 py-1.5 text-xs font-semibold transition-colors",
                  isApplied
                    ? "bg-green-600/20 text-green-400 cursor-not-allowed"
                    : "bg-blue-600 text-white hover:bg-blue-500"
                )}
              >
                {isApplied ? "Applied" : "Apply"}
              </button>
            </div>
          );
        })}
      </div>
    </div>
  );
}
