"use client";

import { useState } from "react";
import { supabase } from "@/lib/supabase";
import { BacktestResult } from "@/lib/types";
import BacktestForm from "@/components/backtest/BacktestForm";
import BacktestResults from "@/components/backtest/BacktestResults";
import BacktestHistory from "@/components/backtest/BacktestHistory";

export interface BacktestParams {
  startDate: string;
  endDate: string;
  confidenceThreshold: number;
  atrMultiplier: number;
  rrRatio: number;
}

export default function BacktestPage() {
  const [result, setResult] = useState<BacktestResult | null>(null);
  const [running, setRunning] = useState(false);

  const handleRunBacktest = async (params: BacktestParams) => {
    setRunning(true);
    try {
      // Simulate a backtest by fetching historical data and computing results
      const { data: trades, error } = await supabase
        .from("trades")
        .select("*")
        .eq("status", "CLOSED")
        .gte("entry_time", params.startDate)
        .lte("entry_time", params.endDate)
        .order("entry_time", { ascending: true });

      if (error) throw error;

      const closedTrades = trades ?? [];
      const totalTrades = closedTrades.length;
      const wins = closedTrades.filter((t: any) => (t.pnl ?? 0) > 0);
      const losses = closedTrades.filter((t: any) => (t.pnl ?? 0) < 0);
      const winRate = totalTrades > 0 ? (wins.length / totalTrades) * 100 : 0;
      const totalPnl = closedTrades.reduce(
        (sum: number, t: any) => sum + (t.pnl ?? 0),
        0
      );
      const avgWin =
        wins.length > 0
          ? wins.reduce((s: number, t: any) => s + (t.pnl ?? 0), 0) / wins.length
          : 0;
      const avgLoss =
        losses.length > 0
          ? losses.reduce((s: number, t: any) => s + (t.pnl ?? 0), 0) /
            losses.length
          : 0;

      // Build equity curve
      let balance = 10000;
      let maxBalance = balance;
      let maxDrawdown = 0;
      const equityCurve: number[] = [balance];
      for (const trade of closedTrades) {
        balance += (trade as any).pnl ?? 0;
        equityCurve.push(balance);
        if (balance > maxBalance) maxBalance = balance;
        const dd = (maxBalance - balance) / maxBalance;
        if (dd > maxDrawdown) maxDrawdown = dd;
      }

      const totalReturn = ((balance - 10000) / 10000) * 100;
      const profitFactor =
        avgLoss !== 0 ? Math.abs(avgWin / avgLoss) : avgWin > 0 ? 999 : 0;

      const backtestResult: BacktestResult = {
        id: crypto.randomUUID(),
        strategy_name: "Macro Pulse AI",
        symbol: "BTCUSDT",
        start_date: params.startDate,
        end_date: params.endDate,
        initial_capital: 10000,
        final_capital: balance,
        total_return_pct: totalReturn,
        max_drawdown: maxDrawdown * 100,
        sharpe_ratio: totalReturn > 0 ? totalReturn / (maxDrawdown * 100 || 1) : 0,
        sortino_ratio: null,
        win_rate: winRate,
        total_trades: totalTrades,
        profit_factor: profitFactor,
        avg_trade_pnl: totalTrades > 0 ? totalPnl / totalTrades : 0,
        avg_win: avgWin,
        avg_loss: avgLoss,
        best_trade: closedTrades.length > 0
          ? Math.max(...closedTrades.map((t: any) => t.pnl ?? 0))
          : 0,
        worst_trade: closedTrades.length > 0
          ? Math.min(...closedTrades.map((t: any) => t.pnl ?? 0))
          : 0,
        parameters: {
          confidence_threshold: params.confidenceThreshold,
          atr_multiplier: params.atrMultiplier,
          rr_ratio: params.rrRatio,
        },
        equity_curve: equityCurve,
        created_at: new Date().toISOString(),
      };

      setResult(backtestResult);
    } catch {
      // Handle error silently
    } finally {
      setRunning(false);
    }
  };

  return (
    <div className="mx-auto max-w-screen-2xl space-y-6">
      <h1 className="text-2xl font-bold text-white">Backtest</h1>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div className="lg:col-span-1">
          <BacktestForm onSubmit={handleRunBacktest} running={running} />
        </div>
        <div className="lg:col-span-2">
          <BacktestResults result={result} running={running} />
        </div>
      </div>

      <BacktestHistory />
    </div>
  );
}
