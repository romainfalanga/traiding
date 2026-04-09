"use client";

import { useEffect, useState } from "react";
import { supabase } from "@/lib/supabase";
import { classNames } from "@/lib/utils";

interface SettingsState {
  // Agent models
  quantModel: string;
  macroModel: string;
  contrarianModel: string;

  // Consensus rules
  consensusRule: "2/3" | "3/3";

  // Risk parameters
  maxPositionPct: number;
  maxTrades: number;
  rrRatio: number;

  // Circuit breaker
  cbMaxDrawdown: number;
  cbMaxDailyLoss: number;
  cbCooldownMinutes: number;
}

export default function SettingsForm() {
  const [settings, setSettings] = useState<SettingsState>({
    quantModel: "gpt-4o",
    macroModel: "claude-opus-4-20250514",
    contrarianModel: "gemini-pro",
    consensusRule: "2/3",
    maxPositionPct: 2,
    maxTrades: 5,
    rrRatio: 2.0,
    cbMaxDrawdown: 15,
    cbMaxDailyLoss: 5,
    cbCooldownMinutes: 60,
  });

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saveStatus, setSaveStatus] = useState<"idle" | "success" | "error">(
    "idle"
  );

  // Load settings from Supabase
  useEffect(() => {
    async function loadSettings() {
      try {
        const { data, error } = await supabase
          .from("bot_settings")
          .select("*");

        if (error) throw error;

        if (data && data.length > 0) {
          const settingsMap: Record<string, any> = {};
          for (const row of data) {
            settingsMap[row.setting_key] = row.setting_value;
          }

          setSettings((prev) => ({
            ...prev,
            quantModel: settingsMap["quant_model"] ?? prev.quantModel,
            macroModel: settingsMap["macro_model"] ?? prev.macroModel,
            contrarianModel:
              settingsMap["contrarian_model"] ?? prev.contrarianModel,
            consensusRule:
              settingsMap["consensus_rule"] ?? prev.consensusRule,
            maxPositionPct:
              settingsMap["max_position_pct"] ?? prev.maxPositionPct,
            maxTrades: settingsMap["max_trades"] ?? prev.maxTrades,
            rrRatio: settingsMap["rr_ratio"] ?? prev.rrRatio,
            cbMaxDrawdown:
              settingsMap["cb_max_drawdown"] ?? prev.cbMaxDrawdown,
            cbMaxDailyLoss:
              settingsMap["cb_max_daily_loss"] ?? prev.cbMaxDailyLoss,
            cbCooldownMinutes:
              settingsMap["cb_cooldown_minutes"] ?? prev.cbCooldownMinutes,
          }));
        }
      } catch {
        // Use defaults
      } finally {
        setLoading(false);
      }
    }

    loadSettings();
  }, []);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setSaveStatus("idle");

    try {
      const settingsToSave = [
        {
          setting_key: "quant_model",
          setting_value: settings.quantModel,
          category: "agents",
          description: "Quant agent model",
        },
        {
          setting_key: "macro_model",
          setting_value: settings.macroModel,
          category: "agents",
          description: "Macro strategist model",
        },
        {
          setting_key: "contrarian_model",
          setting_value: settings.contrarianModel,
          category: "agents",
          description: "Contrarian agent model",
        },
        {
          setting_key: "consensus_rule",
          setting_value: settings.consensusRule,
          category: "consensus",
          description: "Required consensus level",
        },
        {
          setting_key: "max_position_pct",
          setting_value: settings.maxPositionPct,
          category: "risk",
          description: "Maximum position size (% of portfolio)",
        },
        {
          setting_key: "max_trades",
          setting_value: settings.maxTrades,
          category: "risk",
          description: "Maximum concurrent trades",
        },
        {
          setting_key: "rr_ratio",
          setting_value: settings.rrRatio,
          category: "risk",
          description: "Risk-reward ratio",
        },
        {
          setting_key: "cb_max_drawdown",
          setting_value: settings.cbMaxDrawdown,
          category: "circuit_breaker",
          description: "Circuit breaker max drawdown %",
        },
        {
          setting_key: "cb_max_daily_loss",
          setting_value: settings.cbMaxDailyLoss,
          category: "circuit_breaker",
          description: "Circuit breaker max daily loss %",
        },
        {
          setting_key: "cb_cooldown_minutes",
          setting_value: settings.cbCooldownMinutes,
          category: "circuit_breaker",
          description: "Circuit breaker cooldown period (minutes)",
        },
      ];

      for (const setting of settingsToSave) {
        const { error } = await supabase
          .from("bot_settings")
          .upsert(
            {
              ...setting,
              updated_at: new Date().toISOString(),
            },
            { onConflict: "setting_key" }
          );

        if (error) throw error;
      }

      setSaveStatus("success");
      setTimeout(() => setSaveStatus("idle"), 3000);
    } catch {
      setSaveStatus("error");
      setTimeout(() => setSaveStatus("idle"), 3000);
    } finally {
      setSaving(false);
    }
  };

  const inputClass =
    "w-full rounded-lg border border-gray-700 bg-gray-800 px-3 py-2 text-sm text-white placeholder-gray-500 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500";
  const labelClass =
    "text-[10px] font-semibold uppercase tracking-wider text-gray-500";

  if (loading) {
    return (
      <div className="card animate-pulse">
        <div className="space-y-4">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="h-12 rounded bg-gray-800" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <form onSubmit={handleSave} className="space-y-6">
      {/* Agent Models */}
      <div className="card">
        <div className="card-header">Agent Models</div>
        <div className="space-y-4">
          <div>
            <label className={labelClass}>The Quant (Agent 1)</label>
            <input
              type="text"
              value={settings.quantModel}
              onChange={(e) =>
                setSettings({ ...settings, quantModel: e.target.value })
              }
              placeholder="e.g. gpt-4o"
              className={inputClass}
            />
          </div>
          <div>
            <label className={labelClass}>The Macro Strategist (Agent 2)</label>
            <input
              type="text"
              value={settings.macroModel}
              onChange={(e) =>
                setSettings({ ...settings, macroModel: e.target.value })
              }
              placeholder="e.g. claude-opus-4-20250514"
              className={inputClass}
            />
          </div>
          <div>
            <label className={labelClass}>The Contrarian (Agent 3)</label>
            <input
              type="text"
              value={settings.contrarianModel}
              onChange={(e) =>
                setSettings({ ...settings, contrarianModel: e.target.value })
              }
              placeholder="e.g. gemini-pro"
              className={inputClass}
            />
          </div>
        </div>
      </div>

      {/* Consensus Rules */}
      <div className="card">
        <div className="card-header">Consensus Rules</div>
        <div className="flex items-center gap-6">
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="radio"
              name="consensus"
              value="2/3"
              checked={settings.consensusRule === "2/3"}
              onChange={() =>
                setSettings({ ...settings, consensusRule: "2/3" })
              }
              className="accent-blue-500"
            />
            <span className="text-sm text-gray-300">
              2/3 Majority (at least 2 agents agree)
            </span>
          </label>
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="radio"
              name="consensus"
              value="3/3"
              checked={settings.consensusRule === "3/3"}
              onChange={() =>
                setSettings({ ...settings, consensusRule: "3/3" })
              }
              className="accent-blue-500"
            />
            <span className="text-sm text-gray-300">
              3/3 Unanimous (all agents must agree)
            </span>
          </label>
        </div>
      </div>

      {/* Risk Parameters */}
      <div className="card">
        <div className="card-header">Risk Parameters</div>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          <div>
            <label className={labelClass}>
              Max Position Size: {settings.maxPositionPct}%
            </label>
            <input
              type="range"
              min={0.5}
              max={10}
              step={0.5}
              value={settings.maxPositionPct}
              onChange={(e) =>
                setSettings({
                  ...settings,
                  maxPositionPct: parseFloat(e.target.value),
                })
              }
              className="mt-1 w-full accent-blue-500"
            />
            <div className="flex justify-between text-[10px] text-gray-600">
              <span>0.5%</span>
              <span>10%</span>
            </div>
          </div>
          <div>
            <label className={labelClass}>Max Concurrent Trades</label>
            <input
              type="number"
              min={1}
              max={20}
              value={settings.maxTrades}
              onChange={(e) =>
                setSettings({
                  ...settings,
                  maxTrades: parseInt(e.target.value) || 1,
                })
              }
              className={inputClass}
            />
          </div>
          <div>
            <label className={labelClass}>
              R:R Ratio: 1:{settings.rrRatio.toFixed(1)}
            </label>
            <input
              type="range"
              min={1.0}
              max={5.0}
              step={0.1}
              value={settings.rrRatio}
              onChange={(e) =>
                setSettings({
                  ...settings,
                  rrRatio: parseFloat(e.target.value),
                })
              }
              className="mt-1 w-full accent-blue-500"
            />
            <div className="flex justify-between text-[10px] text-gray-600">
              <span>1:1</span>
              <span>1:5</span>
            </div>
          </div>
        </div>
      </div>

      {/* Circuit Breaker */}
      <div className="card">
        <div className="card-header">Circuit Breaker</div>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          <div>
            <label className={labelClass}>
              Max Drawdown: {settings.cbMaxDrawdown}%
            </label>
            <input
              type="range"
              min={5}
              max={30}
              step={1}
              value={settings.cbMaxDrawdown}
              onChange={(e) =>
                setSettings({
                  ...settings,
                  cbMaxDrawdown: parseInt(e.target.value),
                })
              }
              className="mt-1 w-full accent-red-500"
            />
            <div className="flex justify-between text-[10px] text-gray-600">
              <span>5%</span>
              <span>30%</span>
            </div>
          </div>
          <div>
            <label className={labelClass}>
              Max Daily Loss: {settings.cbMaxDailyLoss}%
            </label>
            <input
              type="range"
              min={1}
              max={15}
              step={0.5}
              value={settings.cbMaxDailyLoss}
              onChange={(e) =>
                setSettings({
                  ...settings,
                  cbMaxDailyLoss: parseFloat(e.target.value),
                })
              }
              className="mt-1 w-full accent-red-500"
            />
            <div className="flex justify-between text-[10px] text-gray-600">
              <span>1%</span>
              <span>15%</span>
            </div>
          </div>
          <div>
            <label className={labelClass}>Cooldown (minutes)</label>
            <input
              type="number"
              min={5}
              max={1440}
              value={settings.cbCooldownMinutes}
              onChange={(e) =>
                setSettings({
                  ...settings,
                  cbCooldownMinutes: parseInt(e.target.value) || 60,
                })
              }
              className={inputClass}
            />
          </div>
        </div>
      </div>

      {/* Save Button */}
      <div className="flex items-center gap-4">
        <button
          type="submit"
          disabled={saving}
          className="rounded-lg bg-blue-600 px-6 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-blue-500 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {saving ? (
            <span className="flex items-center gap-2">
              <div className="h-4 w-4 animate-spin rounded-full border-2 border-white/30 border-t-white" />
              Saving...
            </span>
          ) : (
            "Save Settings"
          )}
        </button>

        {saveStatus === "success" && (
          <span className="text-sm font-medium text-green-400">
            Settings saved successfully
          </span>
        )}
        {saveStatus === "error" && (
          <span className="text-sm font-medium text-red-400">
            Failed to save settings
          </span>
        )}
      </div>
    </form>
  );
}
