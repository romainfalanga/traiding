"use client";

import { useEffect, useState, useCallback } from "react";
import { supabase } from "@/lib/supabase";
import { Trade, TradeStatus, TradeSide } from "@/lib/types";
import TradeFilters from "@/components/trades/TradeFilters";
import TradeTable from "@/components/trades/TradeTable";

export interface TradeFilterValues {
  status: TradeStatus | "ALL";
  symbol: string;
  direction: TradeSide | "ALL";
  pnlFilter: "ALL" | "PROFIT" | "LOSS";
}

export default function TradesPage() {
  const [trades, setTrades] = useState<Trade[]>([]);
  const [loading, setLoading] = useState(true);
  const [filters, setFilters] = useState<TradeFilterValues>({
    status: "ALL",
    symbol: "ALL",
    direction: "ALL",
    pnlFilter: "ALL",
  });

  const fetchTrades = useCallback(async () => {
    setLoading(true);
    try {
      let query = supabase
        .from("trades")
        .select("*")
        .order("entry_time", { ascending: false })
        .limit(200);

      if (filters.status !== "ALL") {
        query = query.eq("status", filters.status);
      }
      if (filters.symbol !== "ALL") {
        query = query.eq("symbol", filters.symbol);
      }
      if (filters.direction !== "ALL") {
        query = query.eq("side", filters.direction);
      }

      const { data, error } = await query;

      if (error) throw error;

      let result = data as Trade[];

      // Client-side PnL filter
      if (filters.pnlFilter === "PROFIT") {
        result = result.filter((t) => (t.pnl ?? 0) > 0);
      } else if (filters.pnlFilter === "LOSS") {
        result = result.filter((t) => (t.pnl ?? 0) < 0);
      }

      setTrades(result);
    } catch {
      // Silently fail
    } finally {
      setLoading(false);
    }
  }, [filters]);

  useEffect(() => {
    fetchTrades();
  }, [fetchTrades]);

  // Collect unique symbols for filter dropdown
  const symbols = Array.from(new Set(trades.map((t) => t.symbol)));

  return (
    <div className="mx-auto max-w-screen-2xl space-y-6">
      <h1 className="text-2xl font-bold text-white">Trades</h1>

      <TradeFilters
        filters={filters}
        onFilterChange={setFilters}
        symbols={symbols}
      />

      <TradeTable trades={trades} loading={loading} />
    </div>
  );
}
