"use client";

import { useEffect, useState } from "react";
import { classNames } from "@/lib/utils";

interface EventCountdownProps {
  eventName: string;
  eventTime: string;
  country: string;
  impact: number;
}

function impactColor(impact: number): string {
  if (impact >= 8) return "text-red-400";
  if (impact >= 5) return "text-yellow-400";
  return "text-blue-400";
}

function impactBg(impact: number): string {
  if (impact >= 8) return "bg-red-400/15";
  if (impact >= 5) return "bg-yellow-400/15";
  return "bg-blue-400/15";
}

function impactLabel(impact: number): string {
  if (impact >= 8) return "High";
  if (impact >= 5) return "Medium";
  return "Low";
}

function formatCountdown(ms: number): string {
  if (ms <= 0) return "NOW";

  const totalSeconds = Math.floor(ms / 1000);
  const days = Math.floor(totalSeconds / 86400);
  const hours = Math.floor((totalSeconds % 86400) / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = totalSeconds % 60;

  if (days > 0) return `${days}d ${hours}h ${minutes}m`;
  if (hours > 0) return `${hours}h ${minutes}m ${seconds}s`;
  return `${minutes}m ${seconds}s`;
}

export default function EventCountdown({
  eventName,
  eventTime,
  country,
  impact,
}: EventCountdownProps) {
  const [remaining, setRemaining] = useState<number>(0);

  useEffect(() => {
    function update() {
      const diff = new Date(eventTime).getTime() - Date.now();
      setRemaining(Math.max(0, diff));
    }

    update();
    const interval = setInterval(update, 1000);
    return () => clearInterval(interval);
  }, [eventTime]);

  const isPast = remaining <= 0;

  return (
    <div className="card">
      <div className="card-header">Next Event</div>

      <div className="flex items-start justify-between gap-2">
        <div className="flex-1 min-w-0">
          <h3 className="truncate text-sm font-semibold text-white">
            {eventName}
          </h3>
          <div className="mt-1 flex items-center gap-2 text-xs text-gray-500">
            <span className="font-mono">{country}</span>
            <span
              className={classNames(
                "rounded-full px-2 py-0.5 text-[10px] font-semibold",
                impactColor(impact),
                impactBg(impact)
              )}
            >
              {impactLabel(impact)} Impact
            </span>
          </div>
        </div>
      </div>

      {/* Countdown */}
      <div className="mt-3 flex items-center justify-center rounded-lg bg-gray-800/50 py-3">
        <span
          className={classNames(
            "font-mono text-2xl font-bold",
            isPast ? "text-yellow-400 animate-pulse" : "text-white"
          )}
        >
          {isPast ? "LIVE" : formatCountdown(remaining)}
        </span>
      </div>

      <p className="mt-2 text-center text-xs text-gray-500">
        {new Date(eventTime).toLocaleString()}
      </p>
    </div>
  );
}
