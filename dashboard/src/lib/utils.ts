import { formatDistanceToNow } from "date-fns";
import { RegimeType } from "./types";

/**
 * Format a number as currency with $ sign and commas.
 */
export function formatCurrency(value: number, decimals: number = 2): string {
  const isNegative = value < 0;
  const abs = Math.abs(value);
  const formatted = abs.toLocaleString("en-US", {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
  return `${isNegative ? "-" : ""}$${formatted}`;
}

/**
 * Format a number as a percentage with % sign.
 */
export function formatPct(value: number, decimals: number = 2): string {
  const sign = value > 0 ? "+" : "";
  return `${sign}${value.toFixed(decimals)}%`;
}

/**
 * Format a number with commas.
 */
export function formatNumber(value: number, decimals: number = 2): string {
  return value.toLocaleString("en-US", {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
}

/**
 * Get the Tailwind color class for a given market regime.
 */
export function getRegimeColor(regime: RegimeType): string {
  const map: Record<RegimeType, string> = {
    EUPHORIA: "text-orange-400",
    OPTIMISM: "text-green-400",
    NEUTRAL: "text-blue-400",
    FEAR: "text-yellow-400",
    CAPITULATION: "text-red-400",
  };
  return map[regime] ?? "text-gray-400";
}

/**
 * Get the Tailwind background color class for a given market regime.
 */
export function getRegimeBgColor(regime: RegimeType): string {
  const map: Record<RegimeType, string> = {
    EUPHORIA: "bg-orange-400/20",
    OPTIMISM: "bg-green-400/20",
    NEUTRAL: "bg-blue-400/20",
    FEAR: "bg-yellow-400/20",
    CAPITULATION: "bg-red-400/20",
  };
  return map[regime] ?? "bg-gray-400/20";
}

/**
 * Get the color class for a PnL value (green if positive, red if negative).
 */
export function getPnlColor(value: number): string {
  if (value > 0) return "text-green-400";
  if (value < 0) return "text-red-400";
  return "text-gray-400";
}

/**
 * Return a human-readable relative time string (e.g. "3 minutes ago").
 */
export function timeAgo(date: string | Date): string {
  const d = typeof date === "string" ? new Date(date) : date;
  return formatDistanceToNow(d, { addSuffix: true });
}

/**
 * Conditional class name joining utility.
 * Filters out falsy values and joins with spaces.
 */
export function classNames(
  ...classes: (string | undefined | null | false)[]
): string {
  return classes.filter(Boolean).join(" ");
}
