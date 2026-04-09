"use client";

import { useEffect, useState } from "react";
import { supabase } from "@/lib/supabase";
import { Trade, AIDecision, PostTradeAnalysis } from "@/lib/types";
import {
  formatCurrency,
  formatPct,
  classNames,
  timeAgo,
  getRegimeColor,
} from "@/lib/utils";
import PostTradeCard from "@/components/trades/PostTradeCard";

interface TradeDetailProps {
  trade: Trade;
}

export default function TradeDetail({ trade }: TradeDetailProps) {
  const [decision, setDecision] = useState<AIDecision | null>(null);
  const [analysis, setAnalysis] = useState<PostTradeAnalysis | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchDetails() {
      try {
        const promises: PromiseLike<any>[] = [];

        if (trade.decision_id) {
          promises.push(
            supabase
              .from("ai_decisions")
              .select("*")
              .eq("id", trade.decision_id)
              .single()
              .then((res) => res)
          );
        } else {
          promises.push(Promise.resolve({ data: null, error: null }));
        }

        promises.push(
          supabase
            .from("post_trade_analyses")
            .select("*")
            .eq("trade_id", trade.id)
            .limit(1)
            .single()
            .then((res) => res)
        );

        const [decisionRes, analysisRes] = await Promise.all(promises);

        if (!decisionRes.error && decisionRes.data) {
          setDecision(decisionRes.data as AIDecision);
        }
        if (!analysisRes.error && analysisRes.data) {
          setAnalysis(analysisRes.data as PostTradeAnalysis);
        }
      } catch {
        // Silently fail
      } finally {
        setLoading(false);
      }
    }

    fetchDetails();
  }, [trade.id, trade.decision_id]);

  const pnl = trade.pnl ?? 0;
  const pnlColor = pnl > 0 ? "text-green-400" : pnl < 0 ? "text-red-400" : "text-gray-400";

  return (
    <div className="space-y-4">
      {/* Trade Details Grid */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
        <div>
          <span className="text-[10px] uppercase tracking-wider text-gray-500">
            Symbol
          </span>
          <p className="mt-0.5 text-sm font-semibold text-white">{trade.symbol}</p>
        </div>
        <div>
          <span className="text-[10px] uppercase tracking-wider text-gray-500">
            Side
          </span>
          <p
            className={classNames(
              "mt-0.5 text-sm font-semibold",
              trade.side === "LONG" ? "text-green-400" : "text-red-400"
            )}
          >
            {trade.side}
          </p>
        </div>
        <div>
          <span className="text-[10px] uppercase tracking-wider text-gray-500">
            Quantity
          </span>
          <p className="mt-0.5 text-sm font-semibold text-white">
            {trade.quantity}
          </p>
        </div>
        <div>
          <span className="text-[10px] uppercase tracking-wider text-gray-500">
            Entry Price
          </span>
          <p className="mt-0.5 font-mono text-sm text-white">
            {formatCurrency(trade.entry_price)}
          </p>
        </div>
        <div>
          <span className="text-[10px] uppercase tracking-wider text-gray-500">
            Exit Price
          </span>
          <p className="mt-0.5 font-mono text-sm text-white">
            {trade.exit_price !== null ? formatCurrency(trade.exit_price) : "\u2014"}
          </p>
        </div>
        <div>
          <span className="text-[10px] uppercase tracking-wider text-gray-500">
            Stop Loss
          </span>
          <p className="mt-0.5 font-mono text-sm text-red-400">
            {trade.stop_loss !== null ? formatCurrency(trade.stop_loss) : "\u2014"}
          </p>
        </div>
        <div>
          <span className="text-[10px] uppercase tracking-wider text-gray-500">
            Take Profit
          </span>
          <p className="mt-0.5 font-mono text-sm text-green-400">
            {trade.take_profit !== null
              ? formatCurrency(trade.take_profit)
              : "\u2014"}
          </p>
        </div>
        <div>
          <span className="text-[10px] uppercase tracking-wider text-gray-500">
            PnL
          </span>
          <p className={classNames("mt-0.5 font-mono text-sm font-semibold", pnlColor)}>
            {pnl !== 0 ? `${pnl > 0 ? "+" : ""}${formatCurrency(pnl)}` : "\u2014"}
            {trade.pnl_pct !== null && (
              <span className="ml-1 text-xs">({formatPct(trade.pnl_pct)})</span>
            )}
          </p>
        </div>
        <div>
          <span className="text-[10px] uppercase tracking-wider text-gray-500">
            Fees
          </span>
          <p className="mt-0.5 font-mono text-sm text-gray-400">
            {trade.fees !== null ? formatCurrency(trade.fees) : "\u2014"}
          </p>
        </div>
        <div>
          <span className="text-[10px] uppercase tracking-wider text-gray-500">
            Duration
          </span>
          <p className="mt-0.5 text-sm text-gray-300">
            {trade.duration_minutes !== null
              ? `${trade.duration_minutes} min`
              : "\u2014"}
          </p>
        </div>
        <div>
          <span className="text-[10px] uppercase tracking-wider text-gray-500">
            Entry Regime
          </span>
          <p
            className={classNames(
              "mt-0.5 text-sm font-semibold",
              trade.regime_at_entry
                ? getRegimeColor(trade.regime_at_entry)
                : "text-gray-500"
            )}
          >
            {trade.regime_at_entry ?? "\u2014"}
          </p>
        </div>
        <div>
          <span className="text-[10px] uppercase tracking-wider text-gray-500">
            Exit Regime
          </span>
          <p
            className={classNames(
              "mt-0.5 text-sm font-semibold",
              trade.regime_at_exit
                ? getRegimeColor(trade.regime_at_exit)
                : "text-gray-500"
            )}
          >
            {trade.regime_at_exit ?? "\u2014"}
          </p>
        </div>
        <div>
          <span className="text-[10px] uppercase tracking-wider text-gray-500">
            Entry Time
          </span>
          <p className="mt-0.5 text-xs text-gray-400">
            {timeAgo(trade.entry_time)}
          </p>
        </div>
        <div>
          <span className="text-[10px] uppercase tracking-wider text-gray-500">
            Exit Time
          </span>
          <p className="mt-0.5 text-xs text-gray-400">
            {trade.exit_time ? timeAgo(trade.exit_time) : "\u2014"}
          </p>
        </div>
      </div>

      {/* Notes */}
      {trade.notes && (
        <div>
          <span className="text-[10px] uppercase tracking-wider text-gray-500">
            Notes
          </span>
          <p className="mt-1 rounded-lg bg-gray-800/50 p-3 text-xs text-gray-300 leading-relaxed">
            {trade.notes}
          </p>
        </div>
      )}

      {/* AI Decision Info */}
      {loading ? (
        <div className="flex items-center gap-2 text-xs text-gray-500">
          <div className="h-3 w-3 animate-spin rounded-full border border-gray-600 border-t-blue-400" />
          Loading decision data...
        </div>
      ) : (
        decision && (
          <div className="rounded-lg border border-blue-500/20 bg-blue-500/5 p-3">
            <span className="text-[10px] font-semibold uppercase tracking-wider text-blue-400">
              AI Decision
            </span>
            <div className="mt-2 grid grid-cols-2 gap-3 sm:grid-cols-4">
              <div>
                <span className="text-[10px] text-gray-500">Agent</span>
                <p className="text-xs font-medium text-white">
                  {decision.decision_type}
                </p>
              </div>
              <div>
                <span className="text-[10px] text-gray-500">Confidence</span>
                <p className="text-xs font-mono font-medium text-white">
                  {(decision.confidence * 100).toFixed(0)}%
                </p>
              </div>
              <div>
                <span className="text-[10px] text-gray-500">Risk Score</span>
                <p className="text-xs font-mono font-medium text-white">
                  {decision.risk_score?.toFixed(1) ?? "\u2014"}
                </p>
              </div>
              <div>
                <span className="text-[10px] text-gray-500">Expected Return</span>
                <p className="text-xs font-mono font-medium text-white">
                  {decision.expected_return !== null
                    ? formatPct(decision.expected_return)
                    : "\u2014"}
                </p>
              </div>
            </div>
            {decision.reasoning && (
              <p className="mt-2 rounded bg-gray-800/50 p-2 text-xs text-gray-300 leading-relaxed">
                {decision.reasoning}
              </p>
            )}
          </div>
        )
      )}

      {/* Post-Trade Analysis */}
      {analysis && (
        <PostTradeCard
          whatWorked={
            analysis.entry_quality !== null && analysis.entry_quality >= 7
              ? "Good entry quality and timing"
              : null
          }
          whatFailed={
            analysis.exit_quality !== null && analysis.exit_quality < 5
              ? "Exit quality could be improved"
              : null
          }
          alternativeAction={
            analysis.lessons_learned
              ? analysis.lessons_learned
              : null
          }
          recurringPattern={
            analysis.tags && analysis.tags.length > 0
              ? analysis.tags.join(", ")
              : null
          }
        />
      )}
    </div>
  );
}
