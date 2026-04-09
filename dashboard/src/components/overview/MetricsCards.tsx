"use client";

import { formatCurrency, formatPct, classNames } from "@/lib/utils";
import { Portfolio } from "@/lib/types";

interface MetricCardProps {
  label: string;
  value: string;
  subtitle?: string;
  colorClass?: string;
}

function MetricCard({ label, value, subtitle, colorClass }: MetricCardProps) {
  return (
    <div className="card flex flex-col gap-1">
      <span className="stat-label">{label}</span>
      <span className={classNames("stat-value", colorClass ?? "text-white")}>
        {value}
      </span>
      {subtitle && (
        <span className="text-xs text-gray-500">{subtitle}</span>
      )}
    </div>
  );
}

interface MetricsCardsProps {
  portfolio: Portfolio | null;
  openTradesCount: number;
  loading?: boolean;
}

export default function MetricsCards({
  portfolio,
  openTradesCount,
  loading,
}: MetricsCardsProps) {
  if (loading || !portfolio) {
    return (
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="card animate-pulse">
            <div className="mb-2 h-3 w-20 rounded bg-gray-800" />
            <div className="h-8 w-28 rounded bg-gray-800" />
          </div>
        ))}
      </div>
    );
  }

  const totalPnl = portfolio.total_pnl;
  const pnlColor =
    totalPnl > 0 ? "text-profit" : totalPnl < 0 ? "text-loss" : "text-gray-400";

  const winRate = portfolio.win_rate ?? 0;
  const winRateColor =
    winRate >= 55 ? "text-profit" : winRate >= 45 ? "text-yellow-400" : "text-loss";

  return (
    <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
      <MetricCard
        label="Balance"
        value={formatCurrency(portfolio.total_value)}
        subtitle={`Cash: ${formatCurrency(portfolio.cash_balance)}`}
      />
      <MetricCard
        label="Total PnL"
        value={formatCurrency(totalPnl)}
        subtitle={formatPct(portfolio.total_pnl_pct)}
        colorClass={pnlColor}
      />
      <MetricCard
        label="Win Rate"
        value={formatPct(winRate, 1)}
        subtitle={`${portfolio.total_trades} total trades`}
        colorClass={winRateColor}
      />
      <MetricCard
        label="Open Trades"
        value={String(openTradesCount)}
        subtitle={
          portfolio.unrealized_pnl !== 0
            ? `Unrealized: ${formatCurrency(portfolio.unrealized_pnl)}`
            : undefined
        }
        colorClass="text-accent-light"
      />
    </div>
  );
}
