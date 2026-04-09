"use client";

import { useState } from "react";
import { Trade } from "@/lib/types";
import { formatCurrency, classNames, timeAgo } from "@/lib/utils";
import TradeDetail from "@/components/trades/TradeDetail";

interface TradeTableProps {
  trades: Trade[];
  loading: boolean;
}

type SortKey =
  | "entry_time"
  | "symbol"
  | "side"
  | "entry_price"
  | "exit_price"
  | "pnl"
  | "status"
  | "regime_at_entry";
type SortDir = "asc" | "desc";

export default function TradeTable({ trades, loading }: TradeTableProps) {
  const [sortKey, setSortKey] = useState<SortKey>("entry_time");
  const [sortDir, setSortDir] = useState<SortDir>("desc");
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const handleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortDir(sortDir === "asc" ? "desc" : "asc");
    } else {
      setSortKey(key);
      setSortDir("desc");
    }
  };

  const sortedTrades = [...trades].sort((a, b) => {
    let aVal: any = a[sortKey];
    let bVal: any = b[sortKey];

    if (aVal === null || aVal === undefined) aVal = "";
    if (bVal === null || bVal === undefined) bVal = "";

    if (typeof aVal === "number" && typeof bVal === "number") {
      return sortDir === "asc" ? aVal - bVal : bVal - aVal;
    }

    const strA = String(aVal);
    const strB = String(bVal);
    return sortDir === "asc"
      ? strA.localeCompare(strB)
      : strB.localeCompare(strA);
  });

  const SortHeader = ({
    label,
    field,
  }: {
    label: string;
    field: SortKey;
  }) => (
    <th
      className="cursor-pointer px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-400 hover:text-gray-200 transition-colors"
      onClick={() => handleSort(field)}
    >
      <div className="flex items-center gap-1">
        {label}
        {sortKey === field && (
          <span className="text-blue-400">
            {sortDir === "asc" ? "\u2191" : "\u2193"}
          </span>
        )}
      </div>
    </th>
  );

  if (loading) {
    return (
      <div className="card overflow-hidden">
        <div className="animate-pulse space-y-3 p-4">
          {Array.from({ length: 8 }).map((_, i) => (
            <div key={i} className="h-10 rounded bg-gray-800" />
          ))}
        </div>
      </div>
    );
  }

  if (trades.length === 0) {
    return (
      <div className="card flex items-center justify-center py-16">
        <span className="text-sm text-gray-500">No trades found</span>
      </div>
    );
  }

  return (
    <div className="card overflow-hidden p-0">
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead className="border-b border-gray-800 bg-gray-900/50">
            <tr>
              <SortHeader label="Date" field="entry_time" />
              <SortHeader label="Symbol" field="symbol" />
              <SortHeader label="Direction" field="side" />
              <SortHeader label="Entry" field="entry_price" />
              <SortHeader label="Exit" field="exit_price" />
              <SortHeader label="PnL" field="pnl" />
              <SortHeader label="Status" field="status" />
              <SortHeader label="Regime" field="regime_at_entry" />
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-800/50">
            {sortedTrades.map((trade) => {
              const pnl = trade.pnl ?? 0;
              const pnlColor =
                pnl > 0
                  ? "text-green-400"
                  : pnl < 0
                    ? "text-red-400"
                    : "text-gray-400";

              const statusColor: Record<string, string> = {
                OPEN: "badge-blue",
                CLOSED: "badge-green",
                CANCELLED: "badge-red",
                PENDING: "badge-yellow",
              };

              const isExpanded = expandedId === trade.id;

              return (
                <tr key={trade.id} className="group">
                  <td colSpan={8} className="p-0">
                    <div
                      className="flex cursor-pointer items-center px-4 py-3 transition-colors hover:bg-gray-800/30"
                      onClick={() =>
                        setExpandedId(isExpanded ? null : trade.id)
                      }
                    >
                      {/* Date */}
                      <div className="w-[14%] min-w-[100px] text-xs text-gray-400">
                        {timeAgo(trade.entry_time)}
                      </div>
                      {/* Symbol */}
                      <div className="w-[12%] min-w-[80px] text-sm font-medium text-white">
                        {trade.symbol}
                      </div>
                      {/* Direction */}
                      <div className="w-[10%] min-w-[70px]">
                        <span
                          className={classNames(
                            "text-sm font-bold",
                            trade.side === "LONG"
                              ? "text-green-400"
                              : "text-red-400"
                          )}
                        >
                          {trade.side === "LONG" ? "\u2191 Long" : "\u2193 Short"}
                        </span>
                      </div>
                      {/* Entry */}
                      <div className="w-[12%] min-w-[90px] font-mono text-sm text-gray-300">
                        {formatCurrency(trade.entry_price)}
                      </div>
                      {/* Exit */}
                      <div className="w-[12%] min-w-[90px] font-mono text-sm text-gray-300">
                        {trade.exit_price !== null
                          ? formatCurrency(trade.exit_price)
                          : "\u2014"}
                      </div>
                      {/* PnL */}
                      <div
                        className={classNames(
                          "w-[12%] min-w-[90px] font-mono text-sm font-semibold",
                          pnlColor
                        )}
                      >
                        {pnl !== 0
                          ? `${pnl > 0 ? "+" : ""}${formatCurrency(pnl)}`
                          : "\u2014"}
                      </div>
                      {/* Status */}
                      <div className="w-[10%] min-w-[80px]">
                        <span
                          className={classNames(
                            "badge",
                            statusColor[trade.status] ?? "badge-blue"
                          )}
                        >
                          {trade.status}
                        </span>
                      </div>
                      {/* Regime */}
                      <div className="w-[18%] min-w-[100px] text-xs text-gray-400">
                        {trade.regime_at_entry ?? "\u2014"}
                      </div>
                    </div>

                    {/* Expanded Detail */}
                    {isExpanded && (
                      <div className="border-t border-gray-800 bg-gray-900/30 px-4 py-4">
                        <TradeDetail trade={trade} />
                      </div>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
