"""
Macro Pulse — Configuration centrale.
Charge les variables d'environnement et expose les constantes.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ──────────────────────────── API Keys ────────────────────────────
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY", "")
WHALE_ALERT_API_KEY = os.getenv("WHALE_ALERT_API_KEY", "")

# ──────────────────────────── AI Models ───────────────────────────
AGENT_QUANT_MODEL = os.getenv("AGENT_QUANT_MODEL", "deepseek/deepseek-r1")
AGENT_MACRO_MODEL = os.getenv("AGENT_MACRO_MODEL", "deepseek/deepseek-r1:online")
AGENT_CONTRARIAN_MODEL = os.getenv("AGENT_CONTRARIAN_MODEL", "meta-llama/llama-3.1-8b-instruct:free")
MODEL_LIGHT = os.getenv("MODEL_LIGHT", "meta-llama/llama-3.1-8b-instruct:free")
MODEL_SEARCH = os.getenv("MODEL_SEARCH", "perplexity/sonar")

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

# ──────────────────────────── Supabase ────────────────────────────
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")

# ──────────────────────────── Trading ─────────────────────────────
INITIAL_BALANCE = float(os.getenv("INITIAL_BALANCE", "10000"))
TRADING_FEE_PCT = float(os.getenv("TRADING_FEE_PCT", "0.075"))

# ──────────────────────────── Consensus ───────────────────────────
MIN_CONSENSUS = int(os.getenv("MIN_CONSENSUS", "2"))
MIN_CONFIDENCE_AVG = float(os.getenv("MIN_CONFIDENCE_AVG", "0.6"))

# ──────────────────────────── Risk Management ─────────────────────
MAX_POSITION_PCT = float(os.getenv("MAX_POSITION_PCT", "5"))
MAX_CONCURRENT_TRADES = int(os.getenv("MAX_CONCURRENT_TRADES", "3"))
MIN_RR_RATIO = float(os.getenv("MIN_RR_RATIO", "1.5"))
MIN_MTF_CONFLUENCE = int(os.getenv("MIN_MTF_CONFLUENCE", "2"))
CIRCUIT_BREAKER_CONSECUTIVE_LOSSES = int(os.getenv("CIRCUIT_BREAKER_CONSECUTIVE_LOSSES", "3"))
CIRCUIT_BREAKER_DRAWDOWN_PAUSE = float(os.getenv("CIRCUIT_BREAKER_DRAWDOWN_PAUSE", "10"))
CIRCUIT_BREAKER_DRAWDOWN_STOP = float(os.getenv("CIRCUIT_BREAKER_DRAWDOWN_STOP", "15"))
CORRELATION_THRESHOLD = float(os.getenv("CORRELATION_THRESHOLD", "0.75"))
POST_EVENT_COOLDOWN_MINUTES = int(os.getenv("POST_EVENT_COOLDOWN_MINUTES", "30"))

# ──────────────────────────── Logging ─────────────────────────────
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# ──────────────────────────── Tracked Cryptos ─────────────────────
TRACKED_SYMBOLS = ["BTC/USDT", "ETH/USDT"]
TOP_100_SYMBOLS_SUFFIX = "/USDT"

# ──────────────────────────── Timeframes ──────────────────────────
TECHNICAL_TIMEFRAMES = ["5m", "15m", "1h", "4h", "1d"]

# ──────────────────────────── Finnhub Priority Indicators ─────────
PRIORITY_INDICATORS = [
    "CPI", "Non-Farm Payrolls", "NFP", "Fed Interest Rate",
    "ECB Interest Rate", "BOJ Interest Rate", "PBOC",
    "PMI", "GDP", "Initial Jobless Claims", "PPI",
    "PCE Price Index", "Michigan Consumer Sentiment",
    "China Trade Balance",
]

# ──────────────────────────── Deribit ─────────────────────────────
DERIBIT_BASE_URL = "https://www.deribit.com/api/v2"

# ──────────────────────────── DeFiLlama ───────────────────────────
DEFILLAMA_BASE_URL = "https://api.llama.fi"
STABLECOINS_URL = "https://stablecoins.llama.fi"

# ──────────────────────────── Whale Alert ─────────────────────────
WHALE_ALERT_BASE_URL = "https://api.whale-alert.io/v1"
WHALE_MIN_USD = 1_000_000

# ──────────────────────────── Fear & Greed ────────────────────────
FEAR_GREED_URL = "https://api.alternative.me/fng/"

# ──────────────────────────── LunarCrush ──────────────────────────
LUNARCRUSH_DISCOVER_URL = "https://lunarcrush.com/api4/public/topic"
