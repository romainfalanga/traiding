"use client";

import { useEffect, useState } from "react";
import { supabase } from "@/lib/supabase";
import {
  Portfolio,
  TradFiContext,
  MarketData,
  DefiFlows,
  OptionsData,
  SentimentSnapshot,
  RegimeHistory,
  MacroEvent,
} from "@/lib/types";

import MetricsCards from "@/components/overview/MetricsCards";
import MacroRiskGauge from "@/components/overview/MacroRiskGauge";
import FearGreedGauge from "@/components/overview/FearGreedGauge";
import LiquidityPulseBar from "@/components/overview/LiquidityPulseBar";
import DVOLIndicator from "@/components/overview/DVOLIndicator";
import MarketBreadthBars from "@/components/overview/MarketBreadthBars";
import ETFFlowCard from "@/components/overview/ETFFlowCard";
import EquityCurve from "@/components/overview/EquityCurve";
import RegimeScoreBar from "@/components/overview/RegimeScoreBar";
import PFIBar from "@/components/overview/PFIBar";
import CircuitBreakerStatus from "@/components/overview/CircuitBreakerStatus";
import EventCountdown from "@/components/overview/EventCountdown";

interface OverviewData {
  portfolio: Portfolio | null;
  portfolioHistory: Portfolio[];
  tradFi: TradFiContext[];
  market: MarketData[];
  defi: DefiFlows[];
  options: OptionsData[];
  sentiment: SentimentSnapshot | null;
  regime: RegimeHistory | null;
  nextEvent: MacroEvent | null;
  openTradesCount: number;
}

export default function OverviewPage() {
  const [data, setData] = useState<OverviewData>({
    portfolio: null,
    portfolioHistory: [],
    tradFi: [],
    market: [],
    defi: [],
    options: [],
    sentiment: null,
    regime: null,
    nextEvent: null,
    openTradesCount: 0,
  });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchAll() {
      try {
        const [
          portfolioRes,
          portfolioHistoryRes,
          tradFiRes,
          marketRes,
          defiRes,
          optionsRes,
          sentimentRes,
          regimeRes,
          eventsRes,
          openTradesRes,
        ] = await Promise.all([
          supabase
            .from("portfolio")
            .select("*")
            .order("timestamp", { ascending: false })
            .limit(1)
            .single(),
          supabase
            .from("portfolio")
            .select("*")
            .order("timestamp", { ascending: false })
            .limit(100),
          supabase
            .from("tradfi_context")
            .select("*")
            .order("timestamp", { ascending: false })
            .limit(20),
          supabase
            .from("market_continuous")
            .select("*")
            .order("timestamp", { ascending: false })
            .limit(20),
          supabase
            .from("defi_flows")
            .select("*")
            .order("timestamp", { ascending: false })
            .limit(20),
          supabase
            .from("options_data")
            .select("*")
            .order("timestamp", { ascending: false })
            .limit(20),
          supabase
            .from("sentiment_snapshots")
            .select("*")
            .order("timestamp", { ascending: false })
            .limit(1)
            .single(),
          supabase
            .from("regime_history")
            .select("*")
            .order("timestamp", { ascending: false })
            .limit(1)
            .single(),
          supabase
            .from("macro_events")
            .select("*")
            .gte("scheduled_time", new Date().toISOString())
            .order("scheduled_time", { ascending: true })
            .limit(1)
            .single(),
          supabase
            .from("trades")
            .select("id", { count: "exact", head: true })
            .eq("status", "OPEN"),
        ]);

        setData({
          portfolio: portfolioRes.error ? null : (portfolioRes.data as Portfolio),
          portfolioHistory: portfolioHistoryRes.error
            ? []
            : (portfolioHistoryRes.data as Portfolio[]),
          tradFi: tradFiRes.error ? [] : (tradFiRes.data as TradFiContext[]),
          market: marketRes.error ? [] : (marketRes.data as MarketData[]),
          defi: defiRes.error ? [] : (defiRes.data as DefiFlows[]),
          options: optionsRes.error ? [] : (optionsRes.data as OptionsData[]),
          sentiment: sentimentRes.error
            ? null
            : (sentimentRes.data as SentimentSnapshot),
          regime: regimeRes.error ? null : (regimeRes.data as RegimeHistory),
          nextEvent: eventsRes.error ? null : (eventsRes.data as MacroEvent),
          openTradesCount: openTradesRes.count ?? 0,
        });
      } catch {
        // Silently handle fetch errors
      } finally {
        setLoading(false);
      }
    }

    fetchAll();
  }, []);

  // Derived values
  const fearGreedValue = data.sentiment?.fear_greed_index ?? null;
  const macroRiskScore = data.regime?.composite_score ?? null;

  // Liquidity score from defi net flows (normalize to 0-100)
  const totalNetFlows = data.defi.reduce(
    (sum, d) => sum + (d.net_flows ?? 0),
    0
  );
  const liquidityScore = Math.max(
    0,
    Math.min(100, 50 + totalNetFlows / 1_000_000)
  );

  // DVOL from options data
  const btcOption = data.options.find(
    (o) => o.symbol === "BTC" || o.symbol === "BTCUSDT"
  );
  const dvol = btcOption?.implied_volatility ?? 55;
  const dvolPercentile = dvol > 80 ? 90 : dvol > 60 ? 70 : dvol > 40 ? 45 : 20;

  // Market breadth from market data
  const marketWithSma50 = data.market.filter(
    (m) => m.price > 0 && m.change_24h !== null
  );
  const aboveSma50 =
    marketWithSma50.length > 0
      ? (marketWithSma50.filter((m) => (m.change_24h ?? 0) > 0).length /
          marketWithSma50.length) *
        100
      : 50;
  const aboveSma200 = aboveSma50 * 0.85;

  // ETF flows from tradfi context
  const etfAssets = data.tradFi.filter((t) => t.asset_class === "ETF");
  const etfNetFlow = etfAssets.reduce((sum, e) => sum + e.change_pct, 0) * 100;
  const etfSummary =
    etfAssets.length > 0
      ? `${etfAssets.length} ETF(s) tracked`
      : "No ETF data available";

  // PFI score from portfolio
  const pfiScore =
    data.portfolio
      ? Math.max(
          0,
          Math.min(
            100,
            (data.portfolio.win_rate ?? 50) * 0.4 +
              (data.portfolio.sharpe_ratio ?? 0) * 20 +
              (100 - Math.abs(data.portfolio.max_drawdown) * 100) * 0.3
          )
        )
      : 50;

  // Circuit breaker status
  const circuitBreakerActive =
    data.portfolio !== null && data.portfolio.max_drawdown < -0.15;
  const circuitBreakerReason = circuitBreakerActive
    ? `Drawdown exceeded 15%: ${(data.portfolio!.max_drawdown * 100).toFixed(1)}%`
    : undefined;

  return (
    <div className="mx-auto max-w-screen-2xl space-y-6">
      <h1 className="text-2xl font-bold text-white">Overview</h1>

      {/* Top Metrics */}
      <MetricsCards
        portfolio={data.portfolio}
        openTradesCount={data.openTradesCount}
        loading={loading}
      />

      {/* Gauges Row */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-4">
        <MacroRiskGauge score={macroRiskScore} />
        <FearGreedGauge value={fearGreedValue} />
        <CircuitBreakerStatus
          active={circuitBreakerActive}
          reason={circuitBreakerReason}
        />
        {data.nextEvent ? (
          <EventCountdown
            eventName={data.nextEvent.event_name}
            eventTime={data.nextEvent.scheduled_time}
            country={data.nextEvent.currency}
            impact={data.nextEvent.impact_score ?? 5}
          />
        ) : (
          <div className="card flex items-center justify-center">
            <span className="text-sm text-gray-500">No upcoming events</span>
          </div>
        )}
      </div>

      {/* Indicators Row */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-4">
        <LiquidityPulseBar score={liquidityScore} />
        <DVOLIndicator dvol={dvol} percentile={dvolPercentile} />
        <MarketBreadthBars sma50={aboveSma50} sma200={aboveSma200} />
        <ETFFlowCard flow={etfNetFlow} summary={etfSummary} />
      </div>

      {/* Regime + PFI Row */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <RegimeScoreBar regime={data.regime} loading={loading} />
        <PFIBar score={pfiScore} />
      </div>

      {/* Equity Curve */}
      <EquityCurve history={data.portfolioHistory} />
    </div>
  );
}
