"use client";

import { useEffect, useState, useCallback } from "react";
import { supabase, subscribeToTable, unsubscribe } from "@/lib/supabase";
import { Trade } from "@/lib/types";
import { RealtimeChannel } from "@supabase/supabase-js";

const RECENT_CLOSED_LIMIT = 20;

export function useRealtimeTrades() {
  const [openTrades, setOpenTrades] = useState<Trade[]>([]);
  const [closedTrades, setClosedTrades] = useState<Trade[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchTrades = useCallback(async () => {
    try {
      setLoading(true);

      const [openResult, closedResult] = await Promise.all([
        supabase
          .from("trades")
          .select("*")
          .eq("status", "OPEN")
          .order("entry_time", { ascending: false }),
        supabase
          .from("trades")
          .select("*")
          .eq("status", "CLOSED")
          .order("exit_time", { ascending: false })
          .limit(RECENT_CLOSED_LIMIT),
      ]);

      if (openResult.error) throw openResult.error;
      if (closedResult.error) throw closedResult.error;

      setOpenTrades(openResult.data as Trade[]);
      setClosedTrades(closedResult.data as Trade[]);
      setError(null);
    } catch (err: any) {
      setError(err.message ?? "Failed to fetch trades");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchTrades();

    const channel: RealtimeChannel = subscribeToTable<Trade>(
      "trades",
      (payload) => {
        const trade = payload.new;

        switch (payload.eventType) {
          case "INSERT":
            if (trade.status === "OPEN") {
              setOpenTrades((prev) => [trade, ...prev]);
            } else if (trade.status === "CLOSED") {
              setClosedTrades((prev) =>
                [trade, ...prev].slice(0, RECENT_CLOSED_LIMIT)
              );
            }
            break;

          case "UPDATE":
            if (trade.status === "OPEN") {
              setOpenTrades((prev) =>
                prev.map((t) => (t.id === trade.id ? trade : t))
              );
            } else if (trade.status === "CLOSED") {
              // Trade was closed -- remove from open, add to closed
              setOpenTrades((prev) => prev.filter((t) => t.id !== trade.id));
              setClosedTrades((prev) =>
                [trade, ...prev.filter((t) => t.id !== trade.id)].slice(
                  0,
                  RECENT_CLOSED_LIMIT
                )
              );
            } else if (trade.status === "CANCELLED") {
              setOpenTrades((prev) => prev.filter((t) => t.id !== trade.id));
            }
            break;

          case "DELETE":
            setOpenTrades((prev) => prev.filter((t) => t.id !== trade.id));
            setClosedTrades((prev) => prev.filter((t) => t.id !== trade.id));
            break;
        }
      }
    );

    return () => {
      unsubscribe(channel);
    };
  }, [fetchTrades]);

  return {
    openTrades,
    closedTrades,
    loading,
    error,
    refetch: fetchTrades,
  };
}
