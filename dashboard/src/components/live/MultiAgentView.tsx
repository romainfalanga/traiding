"use client";

import { useEffect, useState } from "react";
import { supabase } from "@/lib/supabase";
import { AIDecision } from "@/lib/types";
import { classNames } from "@/lib/utils";

interface AgentConfig {
  name: string;
  modelLabel: string;
  decisionType: string;
  accentColor: string;
  bgColor: string;
  borderColor: string;
}

const AGENTS: AgentConfig[] = [
  {
    name: "The Quant",
    modelLabel: "GPT-4o",
    decisionType: "quant",
    accentColor: "text-blue-400",
    bgColor: "bg-blue-400/10",
    borderColor: "border-blue-400/30",
  },
  {
    name: "The Macro Strategist",
    modelLabel: "Claude Opus",
    decisionType: "macro_strategist",
    accentColor: "text-purple-400",
    bgColor: "bg-purple-400/10",
    borderColor: "border-purple-400/30",
  },
  {
    name: "The Contrarian",
    modelLabel: "Gemini Pro",
    decisionType: "contrarian",
    accentColor: "text-orange-400",
    bgColor: "bg-orange-400/10",
    borderColor: "border-orange-400/30",
  },
];

function directionBadge(direction: AIDecision["direction"]): {
  label: string;
  color: string;
  bg: string;
} {
  switch (direction) {
    case "LONG":
      return {
        label: "Bullish",
        color: "text-green-400",
        bg: "bg-green-400/15",
      };
    case "SHORT":
      return {
        label: "Bearish",
        color: "text-red-400",
        bg: "bg-red-400/15",
      };
    case "FLAT":
      return {
        label: "Neutral",
        color: "text-gray-400",
        bg: "bg-gray-400/15",
      };
  }
}

function confidenceBarColor(confidence: number): string {
  if (confidence >= 0.8) return "bg-green-400";
  if (confidence >= 0.6) return "bg-yellow-400";
  if (confidence >= 0.4) return "bg-orange-400";
  return "bg-red-400";
}

interface AgentColumnProps {
  agent: AgentConfig;
  decision: AIDecision | null;
  loading: boolean;
}

function AgentColumn({ agent, decision, loading }: AgentColumnProps) {
  const badge = decision ? directionBadge(decision.direction) : null;
  const isContrarian = agent.decisionType === "contrarian";

  return (
    <div
      className={classNames(
        "flex flex-col rounded-lg border bg-gray-900/50",
        agent.borderColor
      )}
    >
      {/* Agent Header */}
      <div
        className={classNames(
          "flex items-center justify-between border-b px-4 py-3",
          agent.borderColor
        )}
      >
        <div>
          <h3 className={classNames("text-sm font-bold", agent.accentColor)}>
            {agent.name}
          </h3>
          <span className="text-xs text-gray-500">{agent.modelLabel}</span>
        </div>
        {decision && badge && (
          <span
            className={classNames(
              "rounded-full px-2.5 py-0.5 text-xs font-semibold",
              badge.color,
              badge.bg
            )}
          >
            {badge.label}
          </span>
        )}
      </div>

      {/* Body */}
      <div className="flex-1 p-4">
        {loading ? (
          <div className="flex items-center justify-center py-8">
            <div className="h-5 w-5 animate-spin rounded-full border-2 border-gray-600 border-t-blue-400" />
          </div>
        ) : !decision ? (
          <p className="py-8 text-center text-sm text-gray-500">
            No analysis available
          </p>
        ) : (
          <div className="space-y-4">
            {/* Confidence Bar */}
            <div>
              <div className="mb-1 flex items-center justify-between text-xs">
                <span className="text-gray-400">Confidence</span>
                <span className="font-mono text-white">
                  {(decision.confidence * 100).toFixed(0)}%
                </span>
              </div>
              <div className="h-2 w-full overflow-hidden rounded-full bg-gray-800">
                <div
                  className={classNames(
                    "h-full rounded-full transition-all duration-500",
                    confidenceBarColor(decision.confidence)
                  )}
                  style={{ width: `${decision.confidence * 100}%` }}
                />
              </div>
            </div>

            {/* Risk Score */}
            {decision.risk_score !== null && (
              <div className="flex items-center justify-between text-xs">
                <span className="text-gray-400">Risk Score</span>
                <span
                  className={classNames(
                    "font-mono font-semibold",
                    decision.risk_score >= 7
                      ? "text-red-400"
                      : decision.risk_score >= 4
                        ? "text-yellow-400"
                        : "text-green-400"
                  )}
                >
                  {decision.risk_score.toFixed(1)}/10
                </span>
              </div>
            )}

            {/* Expected Return */}
            {decision.expected_return !== null && (
              <div className="flex items-center justify-between text-xs">
                <span className="text-gray-400">Expected Return</span>
                <span
                  className={classNames(
                    "font-mono font-semibold",
                    decision.expected_return > 0
                      ? "text-green-400"
                      : "text-red-400"
                  )}
                >
                  {decision.expected_return > 0 ? "+" : ""}
                  {decision.expected_return.toFixed(2)}%
                </span>
              </div>
            )}

            {/* Contrarian Risk Warning */}
            {isContrarian && decision.risk_score !== null && decision.risk_score >= 6 && (
              <div className="rounded-md border border-orange-500/30 bg-orange-500/10 px-3 py-2">
                <div className="flex items-center gap-1.5 text-xs">
                  <span className="text-orange-400 font-semibold">
                    Contrarian Risk
                  </span>
                  <span className="font-mono text-orange-300">
                    {decision.risk_score.toFixed(1)}
                  </span>
                </div>
                <p className="mt-1 text-xs text-orange-300/70">
                  High contrarian signal — potential reversal zone
                </p>
              </div>
            )}

            {/* Regime at Decision */}
            {decision.regime_at_decision && (
              <div className="flex items-center justify-between text-xs">
                <span className="text-gray-400">Regime</span>
                <span className="font-mono text-gray-300">
                  {decision.regime_at_decision}
                </span>
              </div>
            )}

            {/* Time Horizon */}
            {decision.time_horizon && (
              <div className="flex items-center justify-between text-xs">
                <span className="text-gray-400">Horizon</span>
                <span className="text-gray-300">{decision.time_horizon}</span>
              </div>
            )}

            {/* Reasoning (scrollable) */}
            {decision.reasoning && (
              <div>
                <span className="text-xs font-medium text-gray-400">
                  Reasoning
                </span>
                <div className="mt-1 max-h-36 overflow-y-auto rounded-md bg-gray-800/50 p-3 text-xs leading-relaxed text-gray-300">
                  {decision.reasoning}
                </div>
              </div>
            )}

            {/* Data Sources */}
            {decision.data_sources && decision.data_sources.length > 0 && (
              <div className="flex flex-wrap gap-1">
                {decision.data_sources.map((source) => (
                  <span
                    key={source}
                    className="rounded bg-gray-800 px-1.5 py-0.5 text-[10px] text-gray-500"
                  >
                    {source}
                  </span>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

export default function MultiAgentView() {
  const [decisions, setDecisions] = useState<Record<string, AIDecision | null>>(
    {
      quant: null,
      macro_strategist: null,
      contrarian: null,
    }
  );
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchDecisions = async () => {
      try {
        const results = await Promise.all(
          AGENTS.map((agent) =>
            supabase
              .from("ai_decisions")
              .select("*")
              .eq("decision_type", agent.decisionType)
              .order("timestamp", { ascending: false })
              .limit(1)
              .single()
          )
        );

        const newDecisions: Record<string, AIDecision | null> = {};
        AGENTS.forEach((agent, i) => {
          const result = results[i];
          newDecisions[agent.decisionType] =
            result.error ? null : (result.data as AIDecision);
        });

        setDecisions(newDecisions);
      } catch {
        // Will show empty state
      } finally {
        setLoading(false);
      }
    };

    fetchDecisions();

    // Refresh every 30 seconds
    const interval = setInterval(fetchDecisions, 30_000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
      {AGENTS.map((agent) => (
        <AgentColumn
          key={agent.decisionType}
          agent={agent}
          decision={decisions[agent.decisionType]}
          loading={loading}
        />
      ))}
    </div>
  );
}
