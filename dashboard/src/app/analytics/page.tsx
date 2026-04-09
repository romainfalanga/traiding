"use client";

import { useEffect, useState } from "react";
import { supabase } from "@/lib/supabase";
import { Trade, AIDecision, RegimeHistory } from "@/lib/types";
import PerformanceMatrix from "@/components/analytics/PerformanceMatrix";
import PnLDistribution from "@/components/analytics/PnLDistribution";
import ConfidenceCalibration from "@/components/analytics/ConfidenceCalibration";
import AgentAgreement from "@/components/analytics/AgentAgreement";
import RegimePerformance from "@/components/analytics/RegimePerformance";

export default function AnalyticsPage() {
  const [trades, setTrades] = useState<Trade[]>([]);
  const [decisions, setDecisions] = useState<AIDecision[]>([]);
  const [regimes, setRegimes] = useState<RegimeHistory[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchAll() {
      try {
        const [tradesRes, decisionsRes, regimesRes] = await Promise.all([
          supabase
            .from("trades")
            .select("*")
            .eq("status", "CLOSED")
            .order("exit_time", { ascending: false })
            .limit(500),
          supabase
            .from("ai_decisions")
            .select("*")
            .order("timestamp", { ascending: false })
            .limit(500),
          supabase
            .from("regime_history")
            .select("*")
            .order("timestamp", { ascending: false })
            .limit(200),
        ]);

        if (!tradesRes.error) setTrades(tradesRes.data as Trade[]);
        if (!decisionsRes.error) setDecisions(decisionsRes.data as AIDecision[]);
        if (!regimesRes.error) setRegimes(regimesRes.data as RegimeHistory[]);
      } catch {
        // Silently fail
      } finally {
        setLoading(false);
      }
    }

    fetchAll();
  }, []);

  if (loading) {
    return (
      <div className="mx-auto max-w-screen-2xl space-y-6">
        <h1 className="text-2xl font-bold text-white">Analytics</h1>
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="card h-72 animate-pulse">
              <div className="h-full rounded bg-gray-800/50" />
            </div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-screen-2xl space-y-6">
      <h1 className="text-2xl font-bold text-white">Analytics</h1>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <PerformanceMatrix trades={trades} />
        <PnLDistribution trades={trades} />
        <ConfidenceCalibration trades={trades} decisions={decisions} />
        <AgentAgreement trades={trades} decisions={decisions} />
      </div>

      <RegimePerformance trades={trades} />
    </div>
  );
}
