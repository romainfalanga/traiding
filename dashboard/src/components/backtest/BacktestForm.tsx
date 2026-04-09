"use client";

import { useState } from "react";

interface BacktestParams {
  startDate: string;
  endDate: string;
  confidenceThreshold: number;
  atrMultiplier: number;
  rrRatio: number;
}

interface BacktestFormProps {
  onSubmit: (params: BacktestParams) => void;
  running: boolean;
}

export default function BacktestForm({ onSubmit, running }: BacktestFormProps) {
  const [startDate, setStartDate] = useState("2025-01-01");
  const [endDate, setEndDate] = useState("2025-12-31");
  const [confidenceThreshold, setConfidenceThreshold] = useState(0.65);
  const [atrMultiplier, setAtrMultiplier] = useState(1.5);
  const [rrRatio, setRrRatio] = useState(2.0);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit({
      startDate,
      endDate,
      confidenceThreshold,
      atrMultiplier,
      rrRatio,
    });
  };

  const inputClass =
    "w-full rounded-lg border border-gray-700 bg-gray-800 px-3 py-2 text-sm text-white placeholder-gray-500 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500";
  const labelClass =
    "text-[10px] font-semibold uppercase tracking-wider text-gray-500";

  return (
    <div className="card">
      <div className="card-header">Backtest Parameters</div>

      <form onSubmit={handleSubmit} className="space-y-4">
        {/* Date Range */}
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className={labelClass}>Start Date</label>
            <input
              type="date"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              className={inputClass}
            />
          </div>
          <div>
            <label className={labelClass}>End Date</label>
            <input
              type="date"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
              className={inputClass}
            />
          </div>
        </div>

        {/* Confidence Threshold */}
        <div>
          <label className={labelClass}>
            Confidence Threshold: {(confidenceThreshold * 100).toFixed(0)}%
          </label>
          <input
            type="range"
            min={0.3}
            max={0.95}
            step={0.05}
            value={confidenceThreshold}
            onChange={(e) => setConfidenceThreshold(parseFloat(e.target.value))}
            className="mt-1 w-full accent-blue-500"
          />
          <div className="flex justify-between text-[10px] text-gray-600">
            <span>30%</span>
            <span>95%</span>
          </div>
        </div>

        {/* ATR Multiplier */}
        <div>
          <label className={labelClass}>
            ATR Multiplier: {atrMultiplier.toFixed(1)}x
          </label>
          <input
            type="range"
            min={0.5}
            max={4.0}
            step={0.1}
            value={atrMultiplier}
            onChange={(e) => setAtrMultiplier(parseFloat(e.target.value))}
            className="mt-1 w-full accent-blue-500"
          />
          <div className="flex justify-between text-[10px] text-gray-600">
            <span>0.5x</span>
            <span>4.0x</span>
          </div>
        </div>

        {/* Risk:Reward Ratio */}
        <div>
          <label className={labelClass}>
            R:R Ratio: 1:{rrRatio.toFixed(1)}
          </label>
          <input
            type="range"
            min={1.0}
            max={5.0}
            step={0.1}
            value={rrRatio}
            onChange={(e) => setRrRatio(parseFloat(e.target.value))}
            className="mt-1 w-full accent-blue-500"
          />
          <div className="flex justify-between text-[10px] text-gray-600">
            <span>1:1</span>
            <span>1:5</span>
          </div>
        </div>

        {/* Submit */}
        <button
          type="submit"
          disabled={running}
          className="w-full rounded-lg bg-blue-600 px-4 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-blue-500 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {running ? (
            <span className="flex items-center justify-center gap-2">
              <div className="h-4 w-4 animate-spin rounded-full border-2 border-white/30 border-t-white" />
              Running Backtest...
            </span>
          ) : (
            "Run Backtest"
          )}
        </button>
      </form>
    </div>
  );
}
