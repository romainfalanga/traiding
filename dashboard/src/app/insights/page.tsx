"use client";

import { useEffect, useState } from "react";
import { supabase } from "@/lib/supabase";
import { PostTradeAnalysis, Trade } from "@/lib/types";
import PostTradeList from "@/components/insights/PostTradeList";
import RecurringPatterns from "@/components/insights/RecurringPatterns";
import SuggestedAdjustments from "@/components/insights/SuggestedAdjustments";

export interface PostTradeWithTrade extends PostTradeAnalysis {
  trade?: Trade;
}

export default function InsightsPage() {
  const [analyses, setAnalyses] = useState<PostTradeWithTrade[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchInsights() {
      try {
        const { data: ptaData, error: ptaError } = await supabase
          .from("post_trade_analyses")
          .select("*")
          .order("created_at", { ascending: false })
          .limit(100);

        if (ptaError) throw ptaError;

        const analyses = ptaData as PostTradeAnalysis[];

        // Fetch associated trades
        const tradeIds = analyses
          .map((a) => a.trade_id)
          .filter(Boolean) as string[];

        let tradesMap: Record<string, Trade> = {};
        if (tradeIds.length > 0) {
          const { data: tradesData } = await supabase
            .from("trades")
            .select("*")
            .in("id", tradeIds);

          if (tradesData) {
            for (const t of tradesData as Trade[]) {
              tradesMap[t.id] = t;
            }
          }
        }

        const enriched: PostTradeWithTrade[] = analyses.map((a) => ({
          ...a,
          trade: a.trade_id ? tradesMap[a.trade_id] : undefined,
        }));

        setAnalyses(enriched);
      } catch {
        // Silently fail
      } finally {
        setLoading(false);
      }
    }

    fetchInsights();
  }, []);

  if (loading) {
    return (
      <div className="mx-auto max-w-screen-2xl space-y-6">
        <h1 className="text-2xl font-bold text-white">Insights</h1>
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="card h-64 animate-pulse">
              <div className="h-full rounded bg-gray-800/50" />
            </div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-screen-2xl space-y-6">
      <h1 className="text-2xl font-bold text-white">Insights</h1>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Left Column: Post-Trade Analyses */}
        <div className="lg:col-span-2">
          <PostTradeList analyses={analyses} />
        </div>

        {/* Right Column: Patterns + Suggestions */}
        <div className="space-y-6 lg:col-span-1">
          <RecurringPatterns analyses={analyses} />
          <SuggestedAdjustments analyses={analyses} />
        </div>
      </div>
    </div>
  );
}
