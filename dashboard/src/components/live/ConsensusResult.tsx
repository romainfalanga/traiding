"use client";

import { useEffect, useState } from "react";
import { supabase } from "@/lib/supabase";
import { AIDecision } from "@/lib/types";
import { classNames } from "@/lib/utils";

type VoteResult = "UNANIMOUS" | "MAJORITY" | "NO CONSENSUS";
type ConsensusDirection = "LONG" | "SHORT" | "FLAT";

interface ConsensusData {
  vote: VoteResult;
  direction: ConsensusDirection;
  avgConfidence: number;
  sizeMultiplier: number;
  contrarian_warning: string | null;
  decisions: AIDecision[];
}

function computeConsensus(decisions: AIDecision[]): ConsensusData {
  if (decisions.length === 0) {
    return {
      vote: "NO CONSENSUS",
      direction: "FLAT",
      avgConfidence: 0,
      sizeMultiplier: 0,
      contrarian_warning: null,
      decisions: [],
    };
  }

  const directions = decisions.map((d) => d.direction);
  const longCount = directions.filter((d) => d === "LONG").length;
  const shortCount = directions.filter((d) => d === "SHORT").length;
  const flatCount = directions.filter((d) => d === "FLAT").length;

  const avgConfidence =
    decisions.reduce((sum, d) => sum + d.confidence, 0) / decisions.length;

  let vote: VoteResult;
  let direction: ConsensusDirection;

  if (longCount === decisions.length) {
    vote = "UNANIMOUS";
    direction = "LONG";
  } else if (shortCount === decisions.length) {
    vote = "UNANIMOUS";
    direction = "SHORT";
  } else if (flatCount === decisions.length) {
    vote = "UNANIMOUS";
    direction = "FLAT";
  } else if (longCount >= 2) {
    vote = "MAJORITY";
    direction = "LONG";
  } else if (shortCount >= 2) {
    vote = "MAJORITY";
    direction = "SHORT";
  } else {
    vote = "NO CONSENSUS";
    direction = "FLAT";
  }

  // Size multiplier: unanimous high-confidence = 1.5x, majority = 1.0x, no consensus = 0x
  let sizeMultiplier = 0;
  if (vote === "UNANIMOUS") {
    sizeMultiplier = avgConfidence >= 0.8 ? 1.5 : 1.2;
  } else if (vote === "MAJORITY") {
    sizeMultiplier = avgConfidence >= 0.7 ? 1.0 : 0.75;
  }

  // Check contrarian warning
  const contrarianDecision = decisions.find(
    (d) => d.decision_type === "contrarian"
  );
  let contrarian_warning: string | null = null;
  if (
    contrarianDecision &&
    contrarianDecision.direction !== direction &&
    contrarianDecision.risk_score !== null &&
    contrarianDecision.risk_score >= 6
  ) {
    contrarian_warning = `Contrarian dissents (risk: ${contrarianDecision.risk_score.toFixed(1)}) — proceed with caution`;
  }

  return {
    vote,
    direction,
    avgConfidence,
    sizeMultiplier,
    contrarian_warning,
    decisions,
  };
}

function directionArrow(direction: ConsensusDirection) {
  switch (direction) {
    case "LONG":
      return (
        <svg
          className="h-10 w-10 text-green-400"
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
      );
    case "SHORT":
      return (
        <svg
          className="h-10 w-10 text-red-400"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={2.5}
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M19 9l-7 7-7-7"
          />
        </svg>
      );
    case "FLAT":
      return (
        <svg
          className="h-10 w-10 text-gray-400"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={2.5}
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M5 12h14"
          />
        </svg>
      );
  }
}

function voteBadgeStyle(vote: VoteResult): { text: string; bg: string } {
  switch (vote) {
    case "UNANIMOUS":
      return { text: "text-green-300", bg: "bg-green-400/15" };
    case "MAJORITY":
      return { text: "text-yellow-300", bg: "bg-yellow-400/15" };
    case "NO CONSENSUS":
      return { text: "text-gray-400", bg: "bg-gray-400/15" };
  }
}

export default function ConsensusResult() {
  const [consensus, setConsensus] = useState<ConsensusData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchConsensus = async () => {
      try {
        const agentTypes = ["quant", "macro_strategist", "contrarian"];
        const results = await Promise.all(
          agentTypes.map((type) =>
            supabase
              .from("ai_decisions")
              .select("*")
              .eq("decision_type", type)
              .order("timestamp", { ascending: false })
              .limit(1)
              .single()
          )
        );

        const decisions: AIDecision[] = results
          .filter((r) => !r.error && r.data)
          .map((r) => r.data as AIDecision);

        setConsensus(computeConsensus(decisions));
      } catch {
        // Empty state
      } finally {
        setLoading(false);
      }
    };

    fetchConsensus();
    const interval = setInterval(fetchConsensus, 30_000);
    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center rounded-lg border border-gray-800 bg-gray-900/50 py-10">
        <div className="h-5 w-5 animate-spin rounded-full border-2 border-gray-600 border-t-blue-400" />
      </div>
    );
  }

  if (!consensus) {
    return (
      <div className="rounded-lg border border-gray-800 bg-gray-900/50 px-6 py-10 text-center text-sm text-gray-500">
        No consensus data available
      </div>
    );
  }

  const badge = voteBadgeStyle(consensus.vote);

  return (
    <div className="rounded-lg border border-gray-800 bg-gray-900/50">
      <div className="flex flex-col items-center gap-4 px-6 py-6 sm:flex-row sm:justify-between">
        {/* Left: Vote + Direction */}
        <div className="flex items-center gap-5">
          {directionArrow(consensus.direction)}
          <div>
            <span
              className={classNames(
                "inline-block rounded-full px-3 py-1 text-xs font-bold uppercase tracking-wider",
                badge.text,
                badge.bg
              )}
            >
              {consensus.vote}
            </span>
            <p className="mt-1 text-lg font-bold text-white">
              {consensus.direction === "LONG"
                ? "Go Long"
                : consensus.direction === "SHORT"
                  ? "Go Short"
                  : "Stay Flat"}
            </p>
          </div>
        </div>

        {/* Center: Metrics */}
        <div className="flex items-center gap-8">
          <div className="text-center">
            <p className="text-xs text-gray-500">Avg Confidence</p>
            <p className="mt-0.5 text-xl font-bold text-white">
              {(consensus.avgConfidence * 100).toFixed(0)}%
            </p>
          </div>
          <div className="text-center">
            <p className="text-xs text-gray-500">Size Multiplier</p>
            <p
              className={classNames(
                "mt-0.5 text-xl font-bold",
                consensus.sizeMultiplier > 1
                  ? "text-green-400"
                  : consensus.sizeMultiplier > 0
                    ? "text-yellow-400"
                    : "text-gray-500"
              )}
            >
              {consensus.sizeMultiplier.toFixed(2)}x
            </p>
          </div>
          <div className="text-center">
            <p className="text-xs text-gray-500">Agents Agree</p>
            <p className="mt-0.5 text-xl font-bold text-white">
              {consensus.decisions.filter(
                (d) => d.direction === consensus.direction
              ).length}
              /{consensus.decisions.length}
            </p>
          </div>
        </div>

        {/* Right: Individual votes */}
        <div className="flex items-center gap-3">
          {consensus.decisions.map((d) => (
            <div
              key={d.id}
              className={classNames(
                "flex h-8 w-8 items-center justify-center rounded-full text-xs font-bold",
                d.direction === "LONG"
                  ? "bg-green-400/20 text-green-400"
                  : d.direction === "SHORT"
                    ? "bg-red-400/20 text-red-400"
                    : "bg-gray-700 text-gray-400"
              )}
              title={`${d.decision_type}: ${d.direction}`}
            >
              {d.direction === "LONG"
                ? "L"
                : d.direction === "SHORT"
                  ? "S"
                  : "F"}
            </div>
          ))}
        </div>
      </div>

      {/* Contrarian Warning */}
      {consensus.contrarian_warning && (
        <div className="border-t border-orange-500/20 bg-orange-500/5 px-6 py-3">
          <div className="flex items-center gap-2 text-sm text-orange-400">
            <svg
              className="h-4 w-4 flex-shrink-0"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={2}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z"
              />
            </svg>
            <span>{consensus.contrarian_warning}</span>
          </div>
        </div>
      )}
    </div>
  );
}
