"use client";

import { formatCurrency, classNames } from "@/lib/utils";

interface ETFFlowCardProps {
  flow: number;
  summary: string;
}

export default function ETFFlowCard({ flow, summary }: ETFFlowCardProps) {
  const isPositive = flow >= 0;

  return (
    <div
      className={classNames(
        "card border",
        isPositive
          ? "border-green-400/20 bg-green-400/5"
          : "border-red-400/20 bg-red-400/5"
      )}
    >
      <div className="card-header">ETF Net Flows</div>

      <div className="flex items-end justify-between">
        <div>
          <span
            className={classNames(
              "stat-value",
              isPositive ? "text-green-400" : "text-red-400"
            )}
          >
            {isPositive ? "+" : ""}
            {formatCurrency(flow, 1)}
          </span>
          <span className="ml-1 text-xs text-gray-500">M</span>
        </div>

        {/* Arrow indicator */}
        <div
          className={classNames(
            "flex h-10 w-10 items-center justify-center rounded-full",
            isPositive ? "bg-green-400/15" : "bg-red-400/15"
          )}
        >
          <svg
            className={classNames(
              "h-5 w-5",
              isPositive ? "text-green-400" : "text-red-400 rotate-180"
            )}
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={2.5}
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M5 15l7-7 7 7"
            />
          </svg>
        </div>
      </div>

      {summary && (
        <p className="mt-2 text-xs text-gray-400 leading-relaxed">{summary}</p>
      )}
    </div>
  );
}
