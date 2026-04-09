// ─── Macro & Market Data ─────────────────────────────────────────────────────

export interface MacroEvent {
  id: string;
  event_name: string;
  event_type: string;
  scheduled_time: string;
  actual_value: number | null;
  forecast_value: number | null;
  previous_value: number | null;
  surprise_pct: number | null;
  impact_score: number | null;
  currency: string;
  source: string;
  created_at: string;
}

export interface TradFiContext {
  id: string;
  symbol: string;
  asset_class: string;
  price: number;
  change_pct: number;
  volume: number;
  correlation_to_btc: number | null;
  signal: string | null;
  timestamp: string;
  created_at: string;
}

export interface MarketData {
  id: string;
  symbol: string;
  price: number;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  market_cap: number | null;
  change_1h: number | null;
  change_24h: number | null;
  change_7d: number | null;
  timestamp: string;
  source: string;
  created_at: string;
}

export interface TechnicalSnapshot {
  id: string;
  symbol: string;
  timeframe: string;
  rsi: number | null;
  macd_line: number | null;
  macd_signal: number | null;
  macd_histogram: number | null;
  bb_upper: number | null;
  bb_middle: number | null;
  bb_lower: number | null;
  ema_12: number | null;
  ema_26: number | null;
  ema_50: number | null;
  ema_200: number | null;
  atr: number | null;
  adx: number | null;
  obv: number | null;
  vwap: number | null;
  support_levels: number[] | null;
  resistance_levels: number[] | null;
  trend_direction: string | null;
  trend_strength: number | null;
  timestamp: string;
  created_at: string;
}

// ─── DeFi & On-Chain ─────────────────────────────────────────────────────────

export interface DefiFlows {
  id: string;
  protocol: string;
  chain: string;
  tvl: number | null;
  tvl_change_24h: number | null;
  inflows: number | null;
  outflows: number | null;
  net_flows: number | null;
  yield_rate: number | null;
  timestamp: string;
  created_at: string;
}

export interface OptionsData {
  id: string;
  symbol: string;
  expiry: string;
  strike: number;
  option_type: string;
  implied_volatility: number | null;
  open_interest: number | null;
  volume: number | null;
  delta: number | null;
  gamma: number | null;
  theta: number | null;
  max_pain: number | null;
  put_call_ratio: number | null;
  timestamp: string;
  created_at: string;
}

// ─── Sentiment & Whale Tracking ──────────────────────────────────────────────

export interface SentimentSnapshot {
  id: string;
  source: string;
  symbol: string;
  sentiment_score: number;
  bullish_pct: number | null;
  bearish_pct: number | null;
  neutral_pct: number | null;
  fear_greed_index: number | null;
  social_volume: number | null;
  social_dominance: number | null;
  weighted_sentiment: number | null;
  news_sentiment: number | null;
  timestamp: string;
  created_at: string;
}

export interface WhaleMovement {
  id: string;
  tx_hash: string;
  from_address: string;
  to_address: string;
  from_label: string | null;
  to_label: string | null;
  asset: string;
  amount: number;
  usd_value: number;
  movement_type: string;
  exchange: string | null;
  is_significant: boolean;
  timestamp: string;
  created_at: string;
}

// ─── Regime & AI Decisions ───────────────────────────────────────────────────

export type RegimeType =
  | "EUPHORIA"
  | "OPTIMISM"
  | "NEUTRAL"
  | "FEAR"
  | "CAPITULATION";

export interface RegimeHistory {
  id: string;
  regime: RegimeType;
  confidence: number;
  volatility_regime: string | null;
  trend_regime: string | null;
  liquidity_regime: string | null;
  composite_score: number | null;
  factors: Record<string, unknown> | null;
  timestamp: string;
  created_at: string;
}

export interface AIDecision {
  id: string;
  decision_type: string;
  symbol: string;
  direction: "LONG" | "SHORT" | "FLAT";
  confidence: number;
  reasoning: string | null;
  risk_score: number | null;
  expected_return: number | null;
  time_horizon: string | null;
  data_sources: string[] | null;
  model_version: string | null;
  regime_at_decision: RegimeType | null;
  approved: boolean;
  executed: boolean;
  trade_id: string | null;
  timestamp: string;
  created_at: string;
}

// ─── Trading & Portfolio ─────────────────────────────────────────────────────

export type TradeStatus = "OPEN" | "CLOSED" | "CANCELLED" | "PENDING";
export type TradeSide = "LONG" | "SHORT";

export interface Trade {
  id: string;
  symbol: string;
  side: TradeSide;
  status: TradeStatus;
  entry_price: number;
  exit_price: number | null;
  quantity: number;
  stop_loss: number | null;
  take_profit: number | null;
  pnl: number | null;
  pnl_pct: number | null;
  fees: number | null;
  entry_time: string;
  exit_time: string | null;
  duration_minutes: number | null;
  decision_id: string | null;
  regime_at_entry: RegimeType | null;
  regime_at_exit: RegimeType | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface Portfolio {
  id: string;
  total_value: number;
  cash_balance: number;
  positions_value: number;
  unrealized_pnl: number;
  realized_pnl: number;
  total_pnl: number;
  total_pnl_pct: number;
  max_drawdown: number;
  sharpe_ratio: number | null;
  win_rate: number | null;
  total_trades: number;
  open_positions: number;
  daily_pnl: number | null;
  weekly_pnl: number | null;
  monthly_pnl: number | null;
  timestamp: string;
  created_at: string;
}

// ─── Analytics ───────────────────────────────────────────────────────────────

export interface PostTradeAnalysis {
  id: string;
  trade_id: string;
  entry_quality: number | null;
  exit_quality: number | null;
  timing_score: number | null;
  risk_management_score: number | null;
  regime_alignment: boolean | null;
  market_conditions: string | null;
  lessons_learned: string | null;
  tags: string[] | null;
  created_at: string;
}

export interface BacktestResult {
  id: string;
  strategy_name: string;
  symbol: string;
  start_date: string;
  end_date: string;
  initial_capital: number;
  final_capital: number;
  total_return_pct: number;
  max_drawdown: number;
  sharpe_ratio: number | null;
  sortino_ratio: number | null;
  win_rate: number;
  total_trades: number;
  profit_factor: number | null;
  avg_trade_pnl: number | null;
  avg_win: number | null;
  avg_loss: number | null;
  best_trade: number | null;
  worst_trade: number | null;
  parameters: Record<string, unknown> | null;
  equity_curve: number[] | null;
  created_at: string;
}

// ─── Settings ────────────────────────────────────────────────────────────────

export interface BotSettings {
  id: string;
  setting_key: string;
  setting_value: string | number | boolean | Record<string, unknown>;
  category: string;
  description: string | null;
  updated_at: string;
  created_at: string;
}
