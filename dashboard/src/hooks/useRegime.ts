"use client";

import { useEffect, useState, useCallback } from "react";
import { supabase, subscribeToTable, unsubscribe } from "@/lib/supabase";
import { RegimeHistory } from "@/lib/types";
import { RealtimeChannel } from "@supabase/supabase-js";

const HISTORY_LIMIT = 50;

export function useRegime() {
  const [currentRegime, setCurrentRegime] = useState<RegimeHistory | null>(
    null
  );
  const [history, setHistory] = useState<RegimeHistory[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchRegime = useCallback(async () => {
    try {
      setLoading(true);

      const { data, error: queryError } = await supabase
        .from("regime_history")
        .select("*")
        .order("timestamp", { ascending: false })
        .limit(HISTORY_LIMIT);

      if (queryError) throw queryError;

      const regimes = data as RegimeHistory[];
      setCurrentRegime(regimes.length > 0 ? regimes[0] : null);
      setHistory(regimes);
      setError(null);
    } catch (err: any) {
      setError(err.message ?? "Failed to fetch regime history");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchRegime();

    const channel: RealtimeChannel = subscribeToTable<RegimeHistory>(
      "regime_history",
      (payload) => {
        if (payload.eventType === "INSERT") {
          const newRegime = payload.new;
          setCurrentRegime(newRegime);
          setHistory((prev) => [newRegime, ...prev].slice(0, HISTORY_LIMIT));
        }
      }
    );

    return () => {
      unsubscribe(channel);
    };
  }, [fetchRegime]);

  return {
    currentRegime,
    history,
    loading,
    error,
    refetch: fetchRegime,
  };
}
