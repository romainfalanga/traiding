"use client";

import { useMemo } from "react";
import { PostTradeAnalysis } from "@/lib/types";
import { classNames } from "@/lib/utils";

interface PostTradeWithTrade extends PostTradeAnalysis {
  trade?: any;
}

interface RecurringPatternsProps {
  analyses: PostTradeWithTrade[];
}

interface PatternData {
  pattern: string;
  count: number;
  avgPnl: number;
}

export default function RecurringPatterns({
  analyses,
}: RecurringPatternsProps) {
  const patterns = useMemo(() => {
    // Count tag occurrences and compute avg PnL per tag
    const tagMap: Record<string, { count: number; totalPnl: number }> = {};

    for (const analysis of analyses) {
      if (!analysis.tags) continue;

      for (const tag of analysis.tags) {
        if (!tagMap[tag]) {
          tagMap[tag] = { count: 0, totalPnl: 0 };
        }
        tagMap[tag].count += 1;
        tagMap[tag].totalPnl += analysis.trade?.pnl ?? 0;
      }
    }

    // Also extract lessons_learned patterns
    const lessonsMap: Record<string, number> = {};
    for (const analysis of analyses) {
      if (!analysis.lessons_learned) continue;
      // Simple pattern extraction: look for repeated short phrases
      const words = analysis.lessons_learned
        .toLowerCase()
        .split(/[.!?]/)
        .map((s) => s.trim())
        .filter((s) => s.length > 10 && s.length < 100);

      for (const phrase of words) {
        lessonsMap[phrase] = (lessonsMap[phrase] ?? 0) + 1;
      }
    }

    // Combine tags into patterns, sorted by count
    const result: PatternData[] = Object.entries(tagMap)
      .map(([pattern, data]) => ({
        pattern,
        count: data.count,
        avgPnl: data.count > 0 ? data.totalPnl / data.count : 0,
      }))
      .sort((a, b) => b.count - a.count)
      .slice(0, 8);

    return result;
  }, [analyses]);

  if (patterns.length === 0) {
    return (
      <div className="card">
        <div className="card-header">Recurring Patterns</div>
        <p className="py-8 text-center text-sm text-gray-500">
          No recurring patterns identified yet
        </p>
      </div>
    );
  }

  return (
    <div className="card">
      <div className="card-header">Recurring Patterns</div>

      <div className="space-y-2">
        {patterns.map((pattern) => {
          const isNegative = pattern.avgPnl < 0;
          const borderColor = isNegative
            ? "border-red-500/20"
            : "border-yellow-500/20";
          const bgColor = isNegative
            ? "bg-red-500/5"
            : "bg-yellow-500/5";
          const dotColor = isNegative ? "bg-red-400" : "bg-yellow-400";

          return (
            <div
              key={pattern.pattern}
              className={classNames(
                "rounded-lg border p-3",
                borderColor,
                bgColor
              )}
            >
              <div className="flex items-start justify-between gap-2">
                <div className="flex items-center gap-2 min-w-0">
                  <div
                    className={classNames(
                      "mt-0.5 h-2 w-2 flex-shrink-0 rounded-full",
                      dotColor
                    )}
                  />
                  <span className="text-xs font-medium text-gray-300 truncate">
                    {pattern.pattern}
                  </span>
                </div>
                <span className="flex-shrink-0 rounded-full bg-gray-800 px-2 py-0.5 text-[10px] font-mono text-gray-400">
                  {pattern.count}x
                </span>
              </div>
              <p
                className={classNames(
                  "mt-1 ml-4 text-[10px]",
                  isNegative ? "text-red-400" : "text-yellow-400"
                )}
              >
                Avg impact: {pattern.avgPnl >= 0 ? "+" : ""}$
                {pattern.avgPnl.toFixed(2)}
              </p>
            </div>
          );
        })}
      </div>
    </div>
  );
}
