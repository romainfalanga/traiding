"use client";

import { useState } from "react";
import { PostTradeAnalysis, Trade } from "@/lib/types";
import {
  formatCurrency,
  formatPct,
  classNames,
  timeAgo,
  getRegimeColor,
} from "@/lib/utils";

interface PostTradeWithTrade extends PostTradeAnalysis {
  trade?: Trade;
}

interface PostTradeListProps {
  analyses: PostTradeWithTrade[];
}

function ScoreBadge({
  label,
  score,
}: {
  label: string;
  score: number | null;
}) {
  if (score === null) return null;

  const color =
    score >= 7
      ? "text-green-400 bg-green-400/10"
      : score >= 4
        ? "text-yellow-400 bg-yellow-400/10"
        : "text-red-400 bg-red-400/10";

  return (
    <div
      className={classNames(
        "flex items-center gap-1.5 rounded-md px-2 py-1",
        color
      )}
    >
      <span className="text-[10px] uppercase tracking-wider opacity-70">
        {label}
      </span>
      <span className="font-mono text-xs font-bold">{score.toFixed(0)}/10</span>
    </div>
  );
}

export default function PostTradeList({ analyses }: PostTradeListProps) {
  const [expandedId, setExpandedId] = useState<string | null>(null);

  if (analyses.length === 0) {
    return (
      <div className="card">
        <div className="card-header">Post-Trade Analyses</div>
        <p className="py-12 text-center text-sm text-gray-500">
          No post-trade analyses available
        </p>
      </div>
    );
  }

  return (
    <div className="card p-0">
      <div className="px-4 pt-4">
        <div className="card-header">Post-Trade Analyses</div>
      </div>

      <div className="max-h-[600px] overflow-y-auto divide-y divide-gray-800/50">
        {analyses.map((analysis) => {
          const isExpanded = expandedId === analysis.id;
          const trade = analysis.trade;
          const pnl = trade?.pnl ?? 0;
          const pnlColor =
            pnl > 0
              ? "text-green-400"
              : pnl < 0
                ? "text-red-400"
                : "text-gray-400";

          return (
            <div key={analysis.id}>
              {/* Collapsed Row */}
              <div
                className="flex cursor-pointer items-center justify-between px-4 py-3 transition-colors hover:bg-gray-800/30"
                onClick={() =>
                  setExpandedId(isExpanded ? null : analysis.id)
                }
              >
                <div className="flex items-center gap-3 min-w-0">
                  {/* Expand indicator */}
                  <svg
                    className={classNames(
                      "h-4 w-4 flex-shrink-0 text-gray-500 transition-transform",
                      isExpanded ? "rotate-90" : ""
                    )}
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                    strokeWidth={2}
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      d="M9 5l7 7-7 7"
                    />
                  </svg>

                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      {trade && (
                        <span className="text-sm font-medium text-white">
                          {trade.symbol}
                        </span>
                      )}
                      {trade && (
                        <span
                          className={classNames(
                            "text-xs font-bold",
                            trade.side === "LONG"
                              ? "text-green-400"
                              : "text-red-400"
                          )}
                        >
                          {trade.side}
                        </span>
                      )}
                      {analysis.tags &&
                        analysis.tags.slice(0, 2).map((tag) => (
                          <span
                            key={tag}
                            className="rounded bg-gray-800 px-1.5 py-0.5 text-[10px] text-gray-400"
                          >
                            {tag}
                          </span>
                        ))}
                    </div>
                    <span className="text-xs text-gray-500">
                      {timeAgo(analysis.created_at)}
                    </span>
                  </div>
                </div>

                <span
                  className={classNames(
                    "font-mono text-sm font-semibold",
                    pnlColor
                  )}
                >
                  {pnl !== 0
                    ? `${pnl > 0 ? "+" : ""}${formatCurrency(pnl)}`
                    : "\u2014"}
                </span>
              </div>

              {/* Expanded Content */}
              {isExpanded && (
                <div className="border-t border-gray-800 bg-gray-900/30 px-4 py-4 space-y-3">
                  {/* Scores */}
                  <div className="flex flex-wrap gap-2">
                    <ScoreBadge
                      label="Entry"
                      score={analysis.entry_quality}
                    />
                    <ScoreBadge
                      label="Exit"
                      score={analysis.exit_quality}
                    />
                    <ScoreBadge
                      label="Timing"
                      score={analysis.timing_score}
                    />
                    <ScoreBadge
                      label="Risk Mgmt"
                      score={analysis.risk_management_score}
                    />
                  </div>

                  {/* Regime Alignment */}
                  {analysis.regime_alignment !== null && (
                    <div className="flex items-center gap-2 text-xs">
                      <span className="text-gray-500">Regime Aligned:</span>
                      <span
                        className={
                          analysis.regime_alignment
                            ? "text-green-400"
                            : "text-red-400"
                        }
                      >
                        {analysis.regime_alignment ? "Yes" : "No"}
                      </span>
                    </div>
                  )}

                  {/* Market Conditions */}
                  {analysis.market_conditions && (
                    <div>
                      <span className="text-[10px] uppercase tracking-wider text-gray-500">
                        Market Conditions
                      </span>
                      <p className="mt-1 text-xs text-gray-300 leading-relaxed">
                        {analysis.market_conditions}
                      </p>
                    </div>
                  )}

                  {/* Lessons Learned */}
                  {analysis.lessons_learned && (
                    <div>
                      <span className="text-[10px] uppercase tracking-wider text-gray-500">
                        Lessons Learned
                      </span>
                      <p className="mt-1 rounded-lg bg-gray-800/50 p-3 text-xs text-gray-300 leading-relaxed">
                        {analysis.lessons_learned}
                      </p>
                    </div>
                  )}

                  {/* Trade Info */}
                  {trade && (
                    <div className="grid grid-cols-3 gap-3 text-xs">
                      <div>
                        <span className="text-gray-500">Entry</span>
                        <p className="font-mono text-white">
                          {formatCurrency(trade.entry_price)}
                        </p>
                      </div>
                      <div>
                        <span className="text-gray-500">Exit</span>
                        <p className="font-mono text-white">
                          {trade.exit_price !== null
                            ? formatCurrency(trade.exit_price)
                            : "\u2014"}
                        </p>
                      </div>
                      <div>
                        <span className="text-gray-500">PnL</span>
                        <p
                          className={classNames(
                            "font-mono font-semibold",
                            pnlColor
                          )}
                        >
                          {trade.pnl !== null
                            ? formatCurrency(trade.pnl)
                            : "\u2014"}
                          {trade.pnl_pct !== null && (
                            <span className="ml-1 opacity-70">
                              ({formatPct(trade.pnl_pct)})
                            </span>
                          )}
                        </p>
                      </div>
                    </div>
                  )}

                  {/* Tags */}
                  {analysis.tags && analysis.tags.length > 0 && (
                    <div className="flex flex-wrap gap-1">
                      {analysis.tags.map((tag) => (
                        <span
                          key={tag}
                          className="rounded bg-gray-800 px-2 py-0.5 text-[10px] text-gray-400"
                        >
                          {tag}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
