"use client";

import { useEffect, useState, useCallback } from "react";
import { supabase, subscribeToTable, unsubscribe } from "@/lib/supabase";
import { Portfolio } from "@/lib/types";
import { RealtimeChannel } from "@supabase/supabase-js";

export function usePortfolio() {
  const [portfolio, setPortfolio] = useState<Portfolio | null>(null);
  const [history, setHistory] = useState<Portfolio[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchPortfolio = useCallback(async () => {
    try {
      setLoading(true);

      const [latestResult, historyResult] = await Promise.all([
        supabase
          .from("portfolio")
          .select("*")
          .order("timestamp", { ascending: false })
          .limit(1)
          .single(),
        supabase
          .from("portfolio")
          .select("*")
          .order("timestamp", { ascending: false })
          .limit(100),
      ]);

      if (latestResult.error && latestResult.error.code !== "PGRST116") {
        throw latestResult.error;
      }
      if (historyResult.error) throw historyResult.error;

      setPortfolio((latestResult.data as Portfolio) ?? null);
      setHistory(historyResult.data as Portfolio[]);
      setError(null);
    } catch (err: any) {
      setError(err.message ?? "Failed to fetch portfolio");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchPortfolio();

    const channel: RealtimeChannel = subscribeToTable<Portfolio>(
      "portfolio",
      (payload) => {
        if (payload.eventType === "INSERT" || payload.eventType === "UPDATE") {
          const newPortfolio = payload.new;
          setPortfolio(newPortfolio);
          setHistory((prev) => [newPortfolio, ...prev].slice(0, 100));
        }
      }
    );

    return () => {
      unsubscribe(channel);
    };
  }, [fetchPortfolio]);

  return {
    portfolio,
    history,
    loading,
    error,
    refetch: fetchPortfolio,
  };
}
