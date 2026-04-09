-- ============================================
-- MACRO PULSE — Supabase Schema (toutes les tables)
-- Exécuter dans SQL Editor de Supabase
-- ============================================

-- Extension UUID
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 1. macro_events
CREATE TABLE IF NOT EXISTS macro_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    event_name TEXT,
    country TEXT,
    impact INTEGER,
    actual NUMERIC,
    forecast NUMERIC,
    previous NUMERIC,
    surprise_score NUMERIC,
    revision_adjusted_surprise NUMERIC,
    cumulative_surprise_momentum NUMERIC,
    priority BOOLEAN DEFAULT FALSE,
    timestamp TIMESTAMPTZ DEFAULT NOW()
);

-- 2. tradfi_context
CREATE TABLE IF NOT EXISTS tradfi_context (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    dxy_price NUMERIC,
    dxy_change_24h NUMERIC,
    vix_value NUMERIC,
    vix_percentile_90d NUMERIC,
    sp500_price NUMERIC,
    sp500_change_24h NUMERIC,
    us10y_yield NUMERIC,
    us10y_change_24h NUMERIC,
    gold_price NUMERIC,
    gold_change_24h NUMERIC,
    btc_spx_correlation_30d NUMERIC,
    macro_risk_score NUMERIC,
    timestamp TIMESTAMPTZ DEFAULT NOW()
);

-- 3. market_continuous
CREATE TABLE IF NOT EXISTS market_continuous (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    symbol TEXT,
    price NUMERIC,
    volume_24h NUMERIC,
    open_interest NUMERIC,
    funding_rate NUMERIC,
    long_short_ratio NUMERIC,
    fear_greed_index INTEGER,
    market_breadth_above_sma50_pct NUMERIC,
    market_breadth_above_sma200_pct NUMERIC,
    estimated_liquidation_levels JSONB,
    timestamp TIMESTAMPTZ DEFAULT NOW()
);

-- 4. technical_snapshots
CREATE TABLE IF NOT EXISTS technical_snapshots (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    symbol TEXT,
    timeframe TEXT,
    rsi NUMERIC,
    rsi_divergence TEXT,
    macd_signal TEXT,
    macd_histogram NUMERIC,
    sma_20 NUMERIC,
    sma_50 NUMERIC,
    sma_200 NUMERIC,
    ema_12 NUMERIC,
    ema_26 NUMERIC,
    atr NUMERIC,
    bollinger_upper NUMERIC,
    bollinger_lower NUMERIC,
    keltner_squeeze BOOLEAN,
    obv NUMERIC,
    vwap NUMERIC,
    cvd NUMERIC,
    pivot_point NUMERIC,
    support_1 NUMERIC,
    resistance_1 NUMERIC,
    trend_strength_score INTEGER,
    momentum_exhaustion TEXT,
    volatility_regime TEXT,
    mtf_confluence_score INTEGER,
    timestamp TIMESTAMPTZ DEFAULT NOW()
);

-- 5. defi_flows
CREATE TABLE IF NOT EXISTS defi_flows (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    total_tvl NUMERIC,
    tvl_change_24h_pct NUMERIC,
    tvl_change_7d_pct NUMERIC,
    stablecoin_total_supply NUMERIC,
    stablecoin_supply_change_7d NUMERIC,
    stablecoin_mint_rate NUMERIC,
    dex_volume_24h NUMERIC,
    dex_cex_ratio NUMERIC,
    liquidity_pulse_score NUMERIC,
    timestamp TIMESTAMPTZ DEFAULT NOW()
);

-- 6. options_data
CREATE TABLE IF NOT EXISTS options_data (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    btc_dvol NUMERIC,
    eth_dvol NUMERIC,
    btc_dvol_change_24h NUMERIC,
    dvol_percentile_90d NUMERIC,
    btc_max_pain NUMERIC,
    eth_max_pain NUMERIC,
    btc_max_pain_distance_pct NUMERIC,
    btc_put_call_ratio NUMERIC,
    eth_put_call_ratio NUMERIC,
    vol_term_structure TEXT,
    next_expiry_date TIMESTAMPTZ,
    next_expiry_oi_usd NUMERIC,
    timestamp TIMESTAMPTZ DEFAULT NOW()
);

-- 7. sentiment_snapshots
CREATE TABLE IF NOT EXISTS sentiment_snapshots (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source TEXT,
    summary TEXT,
    sentiment_score NUMERIC,
    sentiment_label TEXT,
    sentiment_divergence_score NUMERIC,
    etf_flow_summary TEXT,
    etf_net_flow_usd NUMERIC,
    timestamp TIMESTAMPTZ DEFAULT NOW()
);

-- 8. whale_movements
CREATE TABLE IF NOT EXISTS whale_movements (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    blockchain TEXT,
    symbol TEXT,
    tx_hash TEXT,
    from_owner TEXT,
    to_owner TEXT,
    amount NUMERIC,
    amount_usd NUMERIC,
    transaction_type TEXT,
    whale_flow_index NUMERIC,
    timestamp TIMESTAMPTZ DEFAULT NOW()
);

-- 9. regime_history
CREATE TABLE IF NOT EXISTS regime_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    regime TEXT,
    confidence NUMERIC,
    transition_score NUMERIC,
    fear_greed NUMERIC,
    funding_rate NUMERIC,
    volume_change NUMERIC,
    price_momentum NUMERIC,
    whale_flow NUMERIC,
    trend_strength NUMERIC,
    macro_risk_score NUMERIC,
    liquidity_pulse_score NUMERIC,
    market_breadth_sma50_pct NUMERIC,
    timestamp TIMESTAMPTZ DEFAULT NOW()
);

-- 10. ai_decisions
CREATE TABLE IF NOT EXISTS ai_decisions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    event_id UUID,
    regime_id UUID,
    agent_1_model TEXT,
    agent_1_response TEXT,
    agent_1_impact TEXT,
    agent_1_confidence NUMERIC,
    agent_1_confidence_calibrated NUMERIC,
    agent_2_model TEXT,
    agent_2_response TEXT,
    agent_2_impact TEXT,
    agent_2_confidence NUMERIC,
    agent_2_confidence_calibrated NUMERIC,
    agent_3_model TEXT,
    agent_3_response TEXT,
    agent_3_impact TEXT,
    agent_3_confidence NUMERIC,
    agent_3_contrarian_risk TEXT,
    vote_result TEXT,
    consensus_direction TEXT,
    consensus_confidence_avg NUMERIC,
    consensus_calibrated_avg NUMERIC,
    final_synthesis TEXT,
    trades_proposed JSONB,
    trades_approved JSONB,
    trades_rejected_reasons JSONB,
    correlation_check JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 11. portfolio
CREATE TABLE IF NOT EXISTS portfolio (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    balance NUMERIC DEFAULT 10000,
    equity NUMERIC DEFAULT 10000,
    total_pnl NUMERIC DEFAULT 0,
    total_pnl_pct NUMERIC DEFAULT 0,
    win_rate NUMERIC DEFAULT 0,
    total_trades INTEGER DEFAULT 0,
    open_positions JSONB DEFAULT '[]'::JSONB,
    pfi_score NUMERIC DEFAULT 50,
    circuit_breaker_active BOOLEAN DEFAULT FALSE,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 12. trades
CREATE TABLE IF NOT EXISTS trades (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    decision_id UUID,
    symbol TEXT,
    direction TEXT,
    entry_price NUMERIC,
    current_price NUMERIC,
    exit_price NUMERIC,
    quantity NUMERIC,
    position_size_usd NUMERIC,
    stop_loss NUMERIC,
    take_profit NUMERIC,
    trailing_stop NUMERIC,
    pnl NUMERIC,
    pnl_pct NUMERIC,
    status TEXT DEFAULT 'open',
    close_reason TEXT,
    entry_time TIMESTAMPTZ,
    exit_time TIMESTAMPTZ,
    event_name TEXT,
    regime TEXT,
    agent_consensus TEXT
);

-- 13. post_trade_analyses
CREATE TABLE IF NOT EXISTS post_trade_analyses (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    trade_id UUID REFERENCES trades(id),
    model_used TEXT,
    what_worked TEXT,
    what_failed TEXT,
    alternative_action TEXT,
    recurring_pattern TEXT,
    suggested_adjustments JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 14. backtest_results
CREATE TABLE IF NOT EXISTS backtest_results (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT,
    start_date TIMESTAMPTZ,
    end_date TIMESTAMPTZ,
    params JSONB,
    total_trades INTEGER,
    win_rate NUMERIC,
    total_pnl_pct NUMERIC,
    max_drawdown NUMERIC,
    sharpe_ratio NUMERIC,
    results_detail JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 15. bot_settings
CREATE TABLE IF NOT EXISTS bot_settings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    key TEXT UNIQUE NOT NULL,
    value JSONB,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- Index pour les requêtes fréquentes
-- ============================================
CREATE INDEX IF NOT EXISTS idx_market_continuous_symbol_ts ON market_continuous(symbol, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_technical_snapshots_symbol_tf_ts ON technical_snapshots(symbol, timeframe, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_trades_status ON trades(status);
CREATE INDEX IF NOT EXISTS idx_trades_entry_time ON trades(entry_time DESC);
CREATE INDEX IF NOT EXISTS idx_regime_history_ts ON regime_history(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_ai_decisions_ts ON ai_decisions(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_macro_events_ts ON macro_events(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_whale_movements_ts ON whale_movements(timestamp DESC);

-- ============================================
-- Row Level Security (RLS) — lecture publique
-- ============================================
ALTER TABLE macro_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE tradfi_context ENABLE ROW LEVEL SECURITY;
ALTER TABLE market_continuous ENABLE ROW LEVEL SECURITY;
ALTER TABLE technical_snapshots ENABLE ROW LEVEL SECURITY;
ALTER TABLE defi_flows ENABLE ROW LEVEL SECURITY;
ALTER TABLE options_data ENABLE ROW LEVEL SECURITY;
ALTER TABLE sentiment_snapshots ENABLE ROW LEVEL SECURITY;
ALTER TABLE whale_movements ENABLE ROW LEVEL SECURITY;
ALTER TABLE regime_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE ai_decisions ENABLE ROW LEVEL SECURITY;
ALTER TABLE portfolio ENABLE ROW LEVEL SECURITY;
ALTER TABLE trades ENABLE ROW LEVEL SECURITY;
ALTER TABLE post_trade_analyses ENABLE ROW LEVEL SECURITY;
ALTER TABLE backtest_results ENABLE ROW LEVEL SECURITY;
ALTER TABLE bot_settings ENABLE ROW LEVEL SECURITY;

-- Politique : lecture pour tout le monde (anon key du dashboard)
CREATE POLICY "allow_read_all" ON macro_events FOR SELECT USING (true);
CREATE POLICY "allow_read_all" ON tradfi_context FOR SELECT USING (true);
CREATE POLICY "allow_read_all" ON market_continuous FOR SELECT USING (true);
CREATE POLICY "allow_read_all" ON technical_snapshots FOR SELECT USING (true);
CREATE POLICY "allow_read_all" ON defi_flows FOR SELECT USING (true);
CREATE POLICY "allow_read_all" ON options_data FOR SELECT USING (true);
CREATE POLICY "allow_read_all" ON sentiment_snapshots FOR SELECT USING (true);
CREATE POLICY "allow_read_all" ON whale_movements FOR SELECT USING (true);
CREATE POLICY "allow_read_all" ON regime_history FOR SELECT USING (true);
CREATE POLICY "allow_read_all" ON ai_decisions FOR SELECT USING (true);
CREATE POLICY "allow_read_all" ON portfolio FOR SELECT USING (true);
CREATE POLICY "allow_read_all" ON trades FOR SELECT USING (true);
CREATE POLICY "allow_read_all" ON post_trade_analyses FOR SELECT USING (true);
CREATE POLICY "allow_read_all" ON backtest_results FOR SELECT USING (true);
CREATE POLICY "allow_read_all" ON bot_settings FOR SELECT USING (true);

-- Politique : écriture avec service_role key uniquement (le bot Python)
CREATE POLICY "allow_service_insert" ON macro_events FOR INSERT WITH CHECK (true);
CREATE POLICY "allow_service_insert" ON tradfi_context FOR INSERT WITH CHECK (true);
CREATE POLICY "allow_service_insert" ON market_continuous FOR INSERT WITH CHECK (true);
CREATE POLICY "allow_service_insert" ON technical_snapshots FOR INSERT WITH CHECK (true);
CREATE POLICY "allow_service_insert" ON defi_flows FOR INSERT WITH CHECK (true);
CREATE POLICY "allow_service_insert" ON options_data FOR INSERT WITH CHECK (true);
CREATE POLICY "allow_service_insert" ON sentiment_snapshots FOR INSERT WITH CHECK (true);
CREATE POLICY "allow_service_insert" ON whale_movements FOR INSERT WITH CHECK (true);
CREATE POLICY "allow_service_insert" ON regime_history FOR INSERT WITH CHECK (true);
CREATE POLICY "allow_service_insert" ON ai_decisions FOR INSERT WITH CHECK (true);
CREATE POLICY "allow_service_insert" ON portfolio FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "allow_service_insert" ON trades FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "allow_service_insert" ON post_trade_analyses FOR INSERT WITH CHECK (true);
CREATE POLICY "allow_service_insert" ON backtest_results FOR INSERT WITH CHECK (true);
CREATE POLICY "allow_service_insert" ON bot_settings FOR ALL USING (true) WITH CHECK (true);

-- ============================================
-- Activer Realtime sur les tables clés
-- ============================================
ALTER PUBLICATION supabase_realtime ADD TABLE portfolio;
ALTER PUBLICATION supabase_realtime ADD TABLE trades;
ALTER PUBLICATION supabase_realtime ADD TABLE regime_history;
ALTER PUBLICATION supabase_realtime ADD TABLE ai_decisions;
ALTER PUBLICATION supabase_realtime ADD TABLE macro_events;

-- Insérer le portefeuille initial
INSERT INTO portfolio (balance, equity, total_pnl, total_pnl_pct, win_rate, total_trades, pfi_score)
VALUES (10000, 10000, 0, 0, 0, 0, 50);

SELECT 'Schema created successfully!' AS status;
