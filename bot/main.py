"""
Macro Pulse — Main Orchestration.
Runs 6 concurrent async loops: hourly, event-driven, position management,
whale monitoring, health check, and post-trade analysis.
"""

import sys
import os
import asyncio
import logging
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config
from modules.data_store import DataStore
from modules.macro_scraper import MacroScraper
from modules.tradfi_context import TradFiContext
from modules.market_scanner import MarketScanner
from modules.technical_engine import TechnicalEngine
from modules.defi_scanner import DefiScanner
from modules.options_scanner import OptionsScanner
from modules.sentiment_scanner import SentimentScanner
from modules.whale_tracker import WhaleTracker
from modules.regime_detector import RegimeDetector
from modules.ai_brain import AIBrain
from modules.paper_trader import PaperTrader
from modules.risk_engine import RiskEngine
from modules.post_trade_analyzer import PostTradeAnalyzer

logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL, logging.INFO),
    format="%(asctime)s | %(name)-20s | %(levelname)-7s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("macro_pulse")

BANNER = r"""
  __  __   _   ___ ___  ___    ___  _   _ _    ___ ___
 |  \/  | /_\ / __| _ \/ _ \  | _ \| | | | |  / __| __|
 | |\/| |/ _ \ (__|   / (_) | |  _/| |_| | |__\__ \ _|
 |_|  |_/_/ \_\___|_|_\\___/  |_|   \___/|____|___/___|
              v1.0 — Multi-Agent AI Trading Bot
"""


class MacroPulseBot:
    """Main bot orchestrator."""

    def __init__(self):
        self.data_store = DataStore()
        self.macro_scraper = MacroScraper()
        self.tradfi = TradFiContext()
        self.market_scanner = MarketScanner()
        self.technical = TechnicalEngine()
        self.defi = DefiScanner()
        self.options = OptionsScanner()
        self.sentiment = SentimentScanner()
        self.whale = WhaleTracker()
        self.regime = RegimeDetector()
        self.ai_brain = AIBrain()
        self.risk_engine = RiskEngine()
        self.paper_trader = PaperTrader(self.data_store, self.risk_engine)
        self.post_trade = PostTradeAnalyzer(self.data_store)

        self._processed_events: set[str] = set()
        self._pending_analyses: list[str] = []

    async def start(self):
        print(BANNER)
        logger.info("Starting Macro Pulse Bot...")

        await self.paper_trader.initialize()
        logger.info("Portfolio initialized: $%.2f", self.paper_trader.balance)

        await asyncio.gather(
            self._loop_wrapper("Hourly", self.loop_1_hourly, 3600),
            self._loop_wrapper("EventDriven", self.loop_2_event_driven, 30),
            self._loop_wrapper("PositionMgmt", self.loop_3_position_management, 15),
            self._loop_wrapper("WhaleMonitor", self.loop_4_whale_monitoring, 60),
            self._loop_wrapper("HealthCheck", self.loop_5_health_check, 300),
            self._loop_wrapper("PostTrade", self.loop_6_post_trade_analysis, 60),
        )

    async def _loop_wrapper(self, name: str, coro, interval: int):
        """Wrap a loop function with error handling and sleep."""
        while True:
            try:
                await coro()
            except Exception:
                logger.exception("Loop %s encountered an error", name)
            await asyncio.sleep(interval)

    # ──────────────────── Loop 1: Hourly Cycle ────────────────────

    async def loop_1_hourly(self):
        logger.info("=== HOURLY CYCLE START ===")
        t0 = datetime.now(timezone.utc)

        # 1. Calendar refresh
        try:
            events = self.macro_scraper.fetch_calendar(days_ahead=3)
            logger.info("Calendar: %d events fetched", len(events))
        except Exception:
            logger.exception("Calendar fetch failed")

        # 2. TradFi data
        try:
            tradfi_data = self.tradfi.fetch_all()
            if tradfi_data:
                self.data_store.insert_tradfi_context(self.tradfi.to_dict())
                logger.info("TradFi updated — Macro Risk Score: %s", tradfi_data.get("macro_risk_score"))
        except Exception:
            logger.exception("TradFi update failed")

        # 3. DeFi data
        try:
            defi_data = self.defi.fetch_all()
            if defi_data:
                self.data_store.insert_defi_flows(defi_data)
                logger.info("DeFi updated — Liquidity Pulse: %s", defi_data.get("liquidity_pulse_score"))
        except Exception:
            logger.exception("DeFi update failed")

        # 4. Options data
        try:
            options_data = self.options.fetch_all()
            if options_data:
                self.data_store.insert_options_data(options_data)
                logger.info("Options updated — BTC DVOL: %s", options_data.get("btc_dvol"))
        except Exception:
            logger.exception("Options update failed")

        # 5. Market data + technical for each tracked symbol
        for symbol in config.TRACKED_SYMBOLS:
            try:
                market = self.market_scanner.fetch_all(symbol)
                if market:
                    self.data_store.insert_market_continuous(market)

                # Technical analysis on all timeframes
                analyses = {}
                for tf in config.TECHNICAL_TIMEFRAMES:
                    ta_result = self.technical.analyze(symbol, tf)
                    if ta_result:
                        analyses[tf] = ta_result
                        self.data_store.insert_technical_snapshot(self.technical.to_dict(ta_result))

                # MTF Confluence
                if analyses:
                    mtf_score = TechnicalEngine.calculate_mtf_confluence(analyses)
                    logger.info("%s MTF Confluence: %d/%d timeframes", symbol, mtf_score, len(analyses))

            except Exception:
                logger.exception("Market/Technical update failed for %s", symbol)

        # 6. Sentiment
        try:
            price_change = 0.0
            latest_market = self.data_store.get_latest_market_continuous("BTC/USDT")
            if latest_market:
                price_change = latest_market.get("change_24h", 0.0) or 0.0
            sentiment_data = self.sentiment.fetch_all(price_change_24h=price_change)
            if sentiment_data:
                self.data_store.insert_sentiment_snapshot(sentiment_data)
                logger.info("Sentiment updated — Score: %s", sentiment_data.get("sentiment_score"))
        except Exception:
            logger.exception("Sentiment update failed")

        # 7. Regime detection
        try:
            latest_market = self.data_store.get_latest_market_continuous("BTC/USDT") or {}
            latest_tradfi = self.data_store.get_latest_tradfi_context() or {}
            latest_defi = self.data_store.get_latest_defi_flows() or {}

            metrics = {
                "fear_greed": latest_market.get("fear_greed_index", 50),
                "funding_rate": latest_market.get("funding_rate", 0),
                "volume_change_24h": 0,
                "price_momentum": 0,
                "whale_flow_index": 0,
                "trend_strength": 50,
                "macro_risk_score": latest_tradfi.get("macro_risk_score", 50),
                "liquidity_pulse_score": latest_defi.get("liquidity_pulse_score", 50),
                "market_breadth_sma50_pct": latest_market.get("market_breadth_above_sma50_pct", 50),
            }
            regime_result = self.regime.detect(metrics)
            self.data_store.insert_regime_history(self.regime.to_dict())
            logger.info("Regime: %s (confidence: %.1f%%)", regime_result["regime"], regime_result["confidence"] * 100)
        except Exception:
            logger.exception("Regime detection failed")

        # 8. Portfolio update
        try:
            summary = self.paper_trader.get_portfolio_summary()
            self.data_store.update_portfolio(summary)
        except Exception:
            logger.exception("Portfolio update failed")

        elapsed = (datetime.now(timezone.utc) - t0).total_seconds()
        logger.info("=== HOURLY CYCLE DONE (%.1fs) ===", elapsed)

    # ──────────────────── Loop 2: Event-Driven ────────────────────

    async def loop_2_event_driven(self):
        try:
            recent = self.macro_scraper.get_recent_results(hours_back=0.17)  # ~10 minutes
        except Exception:
            return

        for event in recent:
            event_key = f"{event.get('event_name')}_{event.get('timestamp', '')}"
            if event_key in self._processed_events:
                continue

            if event.get("actual") is None:
                continue

            logger.info("NEW EVENT: %s — Actual: %s, Forecast: %s",
                        event.get("event_name"), event.get("actual"), event.get("forecast"))

            # Check cooldown
            if self.paper_trader.check_cooldown(event.get("event_name", "")):
                logger.info("Cooldown active for %s, skipping", event.get("event_name"))
                self._processed_events.add(event_key)
                continue

            # Process event
            processed = self.macro_scraper.process_event(event)
            self.data_store.insert_macro_event(processed)

            # Gather all data
            market_data = self.data_store.get_latest_market_continuous("BTC/USDT") or {}
            technical_data = self.data_store.get_latest_technical_snapshot("BTC/USDT", "1h") or {}
            tradfi_data = self.data_store.get_latest_tradfi_context() or {}
            defi_data = self.data_store.get_latest_defi_flows() or {}
            options_data = self.data_store.get_latest_options_data() or {}
            sentiment_data = self.data_store.get_latest_sentiment_snapshot() or {}
            whale_data = {}
            try:
                whale_data = self.whale.fetch_all()
            except Exception:
                pass
            regime_data = self.regime.get_current_regime()

            # AI Brain — 3 agents in parallel
            try:
                decision = await self.ai_brain.analyze(
                    event_data=processed,
                    market_data=market_data,
                    technical_data=technical_data,
                    tradfi_data=tradfi_data,
                    defi_data=defi_data,
                    options_data=options_data,
                    sentiment_data=sentiment_data,
                    whale_data=whale_data,
                    regime_data=regime_data,
                )
            except Exception:
                logger.exception("AI Brain analysis failed")
                self._processed_events.add(event_key)
                continue

            vote = decision.get("vote", {})
            agents = decision.get("agents", [])
            synthesis = decision.get("synthesis", "")

            # Store AI decision
            decision_dict = self.ai_brain.to_dict(
                event_id=None,
                regime_id=None,
                agent_results=agents,
                vote_result=vote,
                synthesis=synthesis,
            )
            self.data_store.insert_ai_decision(decision_dict)

            logger.info("AI Decision: %s | Direction: %s | Confidence: %.2f | Size: %.1fx",
                        vote.get("vote_result"), vote.get("consensus_direction"),
                        vote.get("consensus_confidence_avg", 0), vote.get("size_multiplier", 0))

            if vote.get("contrarian_warning"):
                logger.warning("Contrarian warning: %s", vote["contrarian_warning"][:200])

            # Execute trade if consensus reached
            if vote.get("vote_result") != "no_consensus" and vote.get("size_multiplier", 0) > 0:
                await self._execute_consensus_trade(vote, agents, processed, market_data, technical_data, regime_data)

            self._processed_events.add(event_key)

    async def _execute_consensus_trade(self, vote, agents, event, market_data, technical_data, regime_data):
        """Validate and execute a consensus trade."""
        direction = vote["consensus_direction"]
        price = market_data.get("price", 0)
        atr = technical_data.get("atr", price * 0.02)
        regime = regime_data.get("regime", "NEUTRAL")

        if not price or price <= 0:
            logger.warning("Cannot execute trade: no valid price")
            return

        # Aggregate proposed trades from agents
        all_trades = []
        for a in agents:
            all_trades.extend(a.get("trades", []))

        # Filter trades matching consensus direction
        matching = [t for t in all_trades if t.get("direction", "").lower() == direction.lower()]

        if not matching:
            # Create a default trade from consensus
            matching = [{"symbol": "BTC/USDT", "direction": direction, "size_pct": 3}]

        trade_proposal = matching[0]
        symbol = trade_proposal.get("symbol", "BTC/USDT")
        size_pct = float(trade_proposal.get("size_pct", 3)) * vote.get("size_multiplier", 1.0)

        # Get open trades and recent trades for validation
        open_trades = self.data_store.get_open_trades()
        recent_trades = self.data_store.get_closed_trades(limit=10)

        # Risk engine validation
        validation = self.risk_engine.validate_trade(
            trade_proposal={
                "symbol": symbol,
                "direction": direction,
                "size_pct": size_pct,
                "confidence": vote.get("consensus_calibrated_avg", 0.5),
            },
            balance=self.paper_trader.balance,
            open_positions=open_trades,
            recent_trades=recent_trades,
            regime=regime,
            atr=atr,
        )

        if not validation.get("approved"):
            logger.info("Trade REJECTED by risk engine: %s", validation.get("rejection_reasons"))
            return

        adjusted = validation.get("adjusted_trade", {})
        stop_loss = adjusted.get("stop_loss", self.risk_engine.calculate_stop_loss(price, atr, direction, regime))
        take_profit = adjusted.get("take_profit", self.risk_engine.calculate_take_profit(price, stop_loss, direction))
        position_size = adjusted.get("position_size", self.risk_engine.calculate_position_size(
            self.paper_trader.balance, vote.get("consensus_calibrated_avg", 0.5), atr, price, regime
        ))

        quantity = position_size / price if price > 0 else 0

        self.paper_trader.open_position(
            symbol=symbol,
            direction=direction,
            entry_price=price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            quantity=quantity,
            position_size_usd=position_size,
            event_name=event.get("event_name", "Unknown"),
            regime=regime,
            agent_consensus=vote.get("vote_result", ""),
        )

        logger.info("TRADE OPENED: %s %s @ %.2f | SL: %.2f | TP: %.2f | Size: $%.2f",
                     direction.upper(), symbol, price, stop_loss, take_profit, position_size)

    # ──────────────────── Loop 3: Position Management ─────────────

    async def loop_3_position_management(self):
        open_trades = self.data_store.get_open_trades()
        if not open_trades:
            return

        for trade in open_trades:
            try:
                symbol = trade.get("symbol", "BTC/USDT")
                market = self.market_scanner.fetch_market_data(symbol)
                if not market:
                    continue

                current_price = market.get("price", 0)
                if not current_price:
                    continue

                # Get ATR
                ta_data = self.data_store.get_latest_technical_snapshot(symbol, "1h") or {}
                atr = ta_data.get("atr", current_price * 0.02)

                # Get max pain
                options = self.data_store.get_latest_options_data() or {}
                max_pain = options.get("btc_max_pain")
                expiry = options.get("next_expiry_date")
                hours_to_expiry = None
                if expiry:
                    try:
                        exp_dt = datetime.fromisoformat(str(expiry).replace("Z", "+00:00"))
                        hours_to_expiry = (exp_dt - datetime.now(timezone.utc)).total_seconds() / 3600
                    except Exception:
                        pass

                self.paper_trader.update_positions(
                    current_prices={symbol: current_price},
                    atr_values={symbol: atr},
                    max_pain=max_pain,
                    hours_to_expiry=hours_to_expiry,
                )

            except Exception:
                logger.exception("Position update failed for trade %s", trade.get("id"))

        # Persist portfolio
        try:
            summary = self.paper_trader.get_portfolio_summary()
            self.data_store.update_portfolio(summary)
        except Exception:
            pass

    # ──────────────────── Loop 4: Whale Monitoring ────────────────

    async def loop_4_whale_monitoring(self):
        try:
            data = self.whale.fetch_all()
            if not data:
                return

            for tx in data.get("transactions", [])[:20]:
                self.data_store.insert_whale_movement(tx)

            significant = data.get("significant_movements", [])
            if significant:
                for mv in significant[:3]:
                    logger.warning("WHALE ALERT: %s %s — $%s USD (%s)",
                                   mv.get("symbol", "?"),
                                   mv.get("transaction_type", "?"),
                                   f"{mv.get('amount_usd', 0):,.0f}",
                                   mv.get("from_owner", "?") + " -> " + mv.get("to_owner", "?"))

        except Exception:
            logger.exception("Whale monitoring failed")

    # ──────────────────── Loop 5: Health Check ────────────────────

    async def loop_5_health_check(self):
        summary = self.paper_trader.get_portfolio_summary()
        logger.info(
            "HEALTH | Balance: $%.2f | Equity: $%.2f | PnL: %.2f%% | Open: %d | WR: %.1f%%",
            summary.get("balance", 0),
            summary.get("equity", 0),
            summary.get("total_pnl_pct", 0),
            summary.get("open_positions_count", 0),
            summary.get("win_rate", 0) * 100,
        )

        # Circuit breaker check
        cb = summary.get("circuit_breaker", {})
        if cb and cb.get("active"):
            logger.warning("CIRCUIT BREAKER ACTIVE: %s", cb.get("reason", "unknown"))

    # ──────────────────── Loop 6: Post-Trade Analysis ─────────────

    async def loop_6_post_trade_analysis(self):
        try:
            closed = self.data_store.get_closed_trades(limit=5)
            existing = self.data_store.get_post_trade_analyses(limit=100)
            analyzed_ids = {a.get("trade_id") for a in existing} if existing else set()

            for trade in closed:
                trade_id = trade.get("id")
                if trade_id and trade_id not in analyzed_ids:
                    logger.info("Running post-trade analysis for trade %s", trade_id)
                    await self.post_trade.analyze_trade(trade)

                    # Update AI calibration
                    pnl = trade.get("pnl", 0)
                    consensus = trade.get("agent_consensus", "")
                    if consensus and pnl is not None:
                        win = pnl > 0
                        for agent_num in (1, 2, 3):
                            # Use stored confidence if available
                            self.ai_brain.update_calibration(agent_num, 0.65, win)

            # Meta-analysis after 20+ trades
            all_analyses = self.data_store.get_post_trade_analyses(limit=100)
            if all_analyses and len(all_analyses) >= 20:
                await self.post_trade.generate_meta_analysis(all_analyses)

        except Exception:
            logger.exception("Post-trade analysis failed")


if __name__ == "__main__":
    bot = MacroPulseBot()
    asyncio.run(bot.start())
