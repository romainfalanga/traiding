"use client";

import { TradeStatus, TradeSide } from "@/lib/types";

export interface TradeFilterValues {
  status: TradeStatus | "ALL";
  symbol: string;
  direction: TradeSide | "ALL";
  pnlFilter: "ALL" | "PROFIT" | "LOSS";
}

interface TradeFiltersProps {
  filters: TradeFilterValues;
  onFilterChange: (filters: TradeFilterValues) => void;
  symbols: string[];
}

export default function TradeFilters({
  filters,
  onFilterChange,
  symbols,
}: TradeFiltersProps) {
  const selectClass =
    "rounded-lg border border-gray-700 bg-gray-800 px-3 py-2 text-sm text-white focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500";

  return (
    <div className="card">
      <div className="flex flex-wrap items-center gap-4">
        {/* Status */}
        <div className="flex flex-col gap-1">
          <label className="text-[10px] font-semibold uppercase tracking-wider text-gray-500">
            Status
          </label>
          <select
            className={selectClass}
            value={filters.status}
            onChange={(e) =>
              onFilterChange({
                ...filters,
                status: e.target.value as TradeStatus | "ALL",
              })
            }
          >
            <option value="ALL">All Statuses</option>
            <option value="OPEN">Open</option>
            <option value="CLOSED">Closed</option>
            <option value="CANCELLED">Cancelled</option>
            <option value="PENDING">Pending</option>
          </select>
        </div>

        {/* Symbol */}
        <div className="flex flex-col gap-1">
          <label className="text-[10px] font-semibold uppercase tracking-wider text-gray-500">
            Symbol
          </label>
          <select
            className={selectClass}
            value={filters.symbol}
            onChange={(e) =>
              onFilterChange({ ...filters, symbol: e.target.value })
            }
          >
            <option value="ALL">All Symbols</option>
            {symbols.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </div>

        {/* Direction */}
        <div className="flex flex-col gap-1">
          <label className="text-[10px] font-semibold uppercase tracking-wider text-gray-500">
            Direction
          </label>
          <select
            className={selectClass}
            value={filters.direction}
            onChange={(e) =>
              onFilterChange({
                ...filters,
                direction: e.target.value as TradeSide | "ALL",
              })
            }
          >
            <option value="ALL">All Directions</option>
            <option value="LONG">Long</option>
            <option value="SHORT">Short</option>
          </select>
        </div>

        {/* PnL Filter */}
        <div className="flex flex-col gap-1">
          <label className="text-[10px] font-semibold uppercase tracking-wider text-gray-500">
            PnL
          </label>
          <select
            className={selectClass}
            value={filters.pnlFilter}
            onChange={(e) =>
              onFilterChange({
                ...filters,
                pnlFilter: e.target.value as "ALL" | "PROFIT" | "LOSS",
              })
            }
          >
            <option value="ALL">All</option>
            <option value="PROFIT">Profit Only</option>
            <option value="LOSS">Loss Only</option>
          </select>
        </div>
      </div>
    </div>
  );
}
