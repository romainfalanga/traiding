"use client";

import { useEffect, useState, useRef } from "react";
import { supabase, subscribeToTable, unsubscribe } from "@/lib/supabase";
import { MacroEvent } from "@/lib/types";
import { classNames, timeAgo, formatNumber } from "@/lib/utils";
import { RealtimeChannel } from "@supabase/supabase-js";

const FEED_LIMIT = 50;

function impactDot(score: number | null): string {
  if (score === null) return "bg-gray-500";
  if (score >= 8) return "bg-red-500";
  if (score >= 5) return "bg-yellow-500";
  if (score >= 3) return "bg-blue-400";
  return "bg-gray-500";
}

function impactLabel(score: number | null): string {
  if (score === null) return "Unknown";
  if (score >= 8) return "High";
  if (score >= 5) return "Medium";
  if (score >= 3) return "Low";
  return "Minimal";
}

function surpriseColor(surprise: number | null): string {
  if (surprise === null) return "text-gray-400";
  if (surprise > 0) return "text-green-400";
  if (surprise < 0) return "text-red-400";
  return "text-gray-400";
}

function currencyFlag(currency: string): string {
  const flags: Record<string, string> = {
    USD: "US",
    EUR: "EU",
    GBP: "GB",
    JPY: "JP",
    CHF: "CH",
    AUD: "AU",
    CAD: "CA",
    NZD: "NZ",
    CNY: "CN",
  };
  return flags[currency] ?? currency;
}

export default function EventFeed() {
  const [events, setEvents] = useState<MacroEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const fetchEvents = async () => {
      try {
        const { data, error } = await supabase
          .from("macro_events")
          .select("*")
          .order("scheduled_time", { ascending: false })
          .limit(FEED_LIMIT);

        if (error) throw error;
        setEvents(data as MacroEvent[]);
      } catch {
        // Silently fail — events will populate via realtime
      } finally {
        setLoading(false);
      }
    };

    fetchEvents();

    const channel: RealtimeChannel = subscribeToTable<MacroEvent>(
      "macro_events",
      (payload) => {
        if (payload.eventType === "INSERT") {
          setEvents((prev) => [payload.new, ...prev].slice(0, FEED_LIMIT));
        } else if (payload.eventType === "UPDATE") {
          setEvents((prev) =>
            prev.map((e) => (e.id === payload.new.id ? payload.new : e))
          );
        }
      }
    );

    return () => {
      unsubscribe(channel);
    };
  }, []);

  return (
    <div className="flex h-full flex-col rounded-lg border border-gray-800 bg-gray-900/50">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-gray-800 px-4 py-3">
        <h2 className="text-sm font-semibold uppercase tracking-wider text-gray-300">
          Event Feed
        </h2>
        <div className="flex items-center gap-1.5">
          <div className="h-2 w-2 animate-pulse rounded-full bg-green-400" />
          <span className="text-xs text-gray-500">Live</span>
        </div>
      </div>

      {/* Scrollable Feed */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto">
        {loading ? (
          <div className="flex items-center justify-center py-12">
            <div className="h-5 w-5 animate-spin rounded-full border-2 border-gray-600 border-t-blue-400" />
          </div>
        ) : events.length === 0 ? (
          <div className="px-4 py-12 text-center text-sm text-gray-500">
            No events yet
          </div>
        ) : (
          <div className="divide-y divide-gray-800/50">
            {events.map((event) => (
              <div
                key={event.id}
                className="px-4 py-3 transition-colors hover:bg-gray-800/30"
              >
                {/* Top row: time + name + impact */}
                <div className="flex items-start justify-between gap-2">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span
                        className={classNames(
                          "inline-block h-2.5 w-2.5 flex-shrink-0 rounded-full",
                          impactDot(event.impact_score)
                        )}
                        title={impactLabel(event.impact_score)}
                      />
                      <span className="truncate text-sm font-medium text-gray-200">
                        {event.event_name}
                      </span>
                    </div>
                    <div className="mt-1 flex items-center gap-2 text-xs text-gray-500">
                      <span className="font-mono">
                        {currencyFlag(event.currency)}
                      </span>
                      <span>&middot;</span>
                      <span>{timeAgo(event.scheduled_time)}</span>
                      <span>&middot;</span>
                      <span className="capitalize">{event.event_type}</span>
                    </div>
                  </div>
                </div>

                {/* Values row */}
                <div className="mt-2 flex items-center gap-4 text-xs">
                  <div className="flex items-center gap-1">
                    <span className="text-gray-500">Act:</span>
                    <span className="font-mono text-white">
                      {event.actual_value !== null
                        ? formatNumber(event.actual_value, 2)
                        : "—"}
                    </span>
                  </div>
                  <div className="flex items-center gap-1">
                    <span className="text-gray-500">Fcst:</span>
                    <span className="font-mono text-gray-400">
                      {event.forecast_value !== null
                        ? formatNumber(event.forecast_value, 2)
                        : "—"}
                    </span>
                  </div>
                  <div className="flex items-center gap-1">
                    <span className="text-gray-500">Prev:</span>
                    <span className="font-mono text-gray-400">
                      {event.previous_value !== null
                        ? formatNumber(event.previous_value, 2)
                        : "—"}
                    </span>
                  </div>
                  {event.surprise_pct !== null && (
                    <div className="flex items-center gap-1">
                      <span className="text-gray-500">Surprise:</span>
                      <span
                        className={classNames(
                          "font-mono font-semibold",
                          surpriseColor(event.surprise_pct)
                        )}
                      >
                        {event.surprise_pct > 0 ? "+" : ""}
                        {event.surprise_pct.toFixed(1)}%
                      </span>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
