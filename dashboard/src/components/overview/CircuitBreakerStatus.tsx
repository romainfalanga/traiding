"use client";

import { classNames } from "@/lib/utils";

interface CircuitBreakerStatusProps {
  active: boolean;
  reason?: string;
}

export default function CircuitBreakerStatus({
  active,
  reason,
}: CircuitBreakerStatusProps) {
  return (
    <div
      className={classNames(
        "card border",
        active
          ? "border-red-500/30 bg-red-500/5"
          : "border-green-500/20 bg-green-500/5"
      )}
    >
      <div className="card-header">Circuit Breaker</div>

      <div className="flex items-center gap-3">
        {/* Status indicator */}
        <div
          className={classNames(
            "flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-full",
            active ? "bg-red-500/20" : "bg-green-500/20"
          )}
        >
          <div
            className={classNames(
              "h-4 w-4 rounded-full",
              active
                ? "bg-red-500 animate-pulse"
                : "bg-green-500"
            )}
          />
        </div>

        <div>
          <span
            className={classNames(
              "text-lg font-bold",
              active ? "text-red-400" : "text-green-400"
            )}
          >
            {active ? "ACTIVE" : "Normal"}
          </span>

          {active && reason && (
            <p className="mt-0.5 text-xs text-red-300/70">{reason}</p>
          )}

          {!active && (
            <p className="mt-0.5 text-xs text-gray-500">
              All systems operational
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
