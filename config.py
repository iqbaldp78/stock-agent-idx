import os
from dotenv import load_dotenv

load_dotenv()

# Universe diambil dinamis dari database table `universe`

DEFAULT_UNIVERSE = [
    "BBCA", "BMRI", "TLKM", "BBNI", "BBRI", "ASII", "UNVR", "ICBP", "AMRT", "GOTO",
    "MDKA", "ANTM", "INCO", "PTBA", "ADRO", "ITMG", "PGAS", "EXCL", "ISAT", "KLBF",
    "MYOR", "SIDO", "TBIG", "TOWR", "BREN", "CUAN", "BRPT", "AMMN", "MBMA", "PGEO",
    "NCKL", "TINS", "ESSA", "MEDC", "AKRA", "BRMS", "DEWA", "BUMI", "PANI", "DSSA",
    "BYAN", "ARCI", "OASA", "MSIN", "BUVA", "BNBR", "BIPI", "MINA", "PADI", "PACK",
    "CBDK", "CDIA", "EMAS", "ENRG", "INET", "RATU", "VKTR", "ACES", "BBTN", "BULL",
    "BRIS", "RAJA", "SSIA", "TPIA"
]

CUSTOM_WATCHLIST: list[str] = []


def get_universe() -> list[str]:
    try:
        from db import SessionLocal
        from db.models import Universe
        db = SessionLocal()
        active_universes = db.query(Universe.ticker).filter(Universe.active == True).all()
        db_tickers = [row[0] for row in active_universes]
        db.close()
        if db_tickers:
            return list(set(db_tickers + CUSTOM_WATCHLIST))
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"Failed to fetch universe from DB: {e}")

    return list(set(DEFAULT_UNIVERSE + CUSTOM_WATCHLIST))


def to_yahoo_ticker(code: str) -> str:
    return f"{code}.JK"


# Filter thresholds
MIN_VOLUME = 100_000
MIN_MARKET_CAP = 1_000_000_000_000  # 1 Triliun IDR

# LLM — 9Router (OpenAI-compatible)
# Load allowed models from the environment to avoid hardcoding large lists in the repo.
# Provide a comma-separated list via the `ALLOWED_LLM_MODELS` env var.
_env_allowed = os.getenv("ALLOWED_LLM_MODELS", "").strip()
if _env_allowed:
    ALLOWED_LLM_MODELS = set(m.strip() for m in _env_allowed.split(",") if m.strip())
else:
    # Minimal safe defaults so the app works without an env var set.
    ALLOWED_LLM_MODELS = {"free", "kr/claude-haiku-4.5", "kr/claude-sonnet-4.5"}

LLM_ENABLED = os.getenv("LLM_ENABLED", "true").lower() in ("true", "1", "yes")
LLM_DEBATE_MAX_TICKERS = int(os.getenv("LLM_DEBATE_MAX_TICKERS", "12"))
LLM_TEMPERATURE_DEBATE = float(os.getenv("LLM_TEMPERATURE_DEBATE", "0.3"))
LLM_TEMPERATURE_IM = float(os.getenv("LLM_TEMPERATURE_IM", "0.2"))

# Global round-robin mode (optional)
_LLM_RR_MODELS_ENV = os.getenv("LLM_ROUND_ROBIN", "").strip()

# Predefined model combos
LLM_MODEL_COMBOS = {
    "ALL": list(ALLOWED_LLM_MODELS),
    "THINKING": [m for m in ALLOWED_LLM_MODELS if "thinking" in m],
    "CLAUDE": [m for m in ALLOWED_LLM_MODELS if "claude" in m],
}

if _LLM_RR_MODELS_ENV in LLM_MODEL_COMBOS:
    LLM_ROUND_ROBIN_MODELS = LLM_MODEL_COMBOS[_LLM_RR_MODELS_ENV]
else:
    LLM_ROUND_ROBIN_MODELS = [m.strip() for m in _LLM_RR_MODELS_ENV.split(",") if m.strip()]

LLM_ROUND_ROBIN_INDEX = 0  # Global index for round-robin

LLM_MODEL_DEBATE_R1 = os.getenv("LLM_MODEL_DEBATE_R1", "kr/claude-haiku-4.5")
LLM_MODEL_DEBATE_R2 = os.getenv("LLM_MODEL_DEBATE_R2", "kr/claude-sonnet-4.5")
LLM_MODEL_INVESTMENT_MANAGER = os.getenv(
    "LLM_MODEL_INVESTMENT_MANAGER", "kr/claude-sonnet-4.5-thinking"
)
LLM_MODEL_DEBATE_FALLBACK = os.getenv("LLM_MODEL_DEBATE_FALLBACK", "kr/claude-haiku-4.5")
LLM_MODEL_IM_FALLBACK = os.getenv("LLM_MODEL_IM_FALLBACK", "kr/claude-sonnet-4.5")
LLM_MODEL_DEBATE_R2_FALLBACK = os.getenv(
    "LLM_MODEL_DEBATE_R2_FALLBACK", "kr/claude-haiku-4.5"
)

# Per-agent models (different providers = more objective debate)
LLM_MODEL_AGENT: dict[str, str] = {
    "fundamental": os.getenv("LLM_MODEL_FUNDAMENTAL", "kr/claude-haiku-4.5"),
    "technical": os.getenv("LLM_MODEL_TECHNICAL", "kr/deepseek-3.2"),
    "bandarmologi": os.getenv("LLM_MODEL_BANDARM", "kr/glm-5"),
    "macro": os.getenv("LLM_MODEL_MACRO", "kr/claude-haiku-4.5"),
}

LLM_MODEL_AGENT_R2: dict[str, str] = {
    "fundamental": os.getenv("LLM_MODEL_FUNDAMENTAL_R2", "kr/claude-sonnet-4.5"),
    "technical": os.getenv("LLM_MODEL_TECHNICAL_R2", "ds/deepseek-v4-pro"),
    "bandarmologi": os.getenv("LLM_MODEL_BANDARM_R2", "kr/claude-sonnet-4.5"),
    "macro": os.getenv("LLM_MODEL_MACRO_R2", "kr/claude-sonnet-4.5"),
}

# Ensure any models configured via env vars are included in the allowed set.
# This avoids raising validation errors for models explicitly set in the env
# (e.g. LLM_MODEL_DEBATE_R1, per-agent overrides, or round-robin list).
_referenced_models = set()
_referenced_models.update([
    os.getenv("LLM_MODEL_DEBATE_R1", "kr/claude-haiku-4.5"),
    os.getenv("LLM_MODEL_DEBATE_R2", "kr/claude-sonnet-4.5"),
    os.getenv("LLM_MODEL_INVESTMENT_MANAGER", "kr/claude-sonnet-4.5-thinking"),
    os.getenv("LLM_MODEL_DEBATE_FALLBACK", "kr/claude-haiku-4.5"),
    os.getenv("LLM_MODEL_IM_FALLBACK", "kr/claude-sonnet-4.5"),
    os.getenv("LLM_MODEL_DEBATE_R2_FALLBACK", "kr/claude-haiku-4.5"),
])
_referenced_models.update(LLM_MODEL_AGENT.values())
_referenced_models.update(LLM_MODEL_AGENT_R2.values())
_referenced_models.update(LLM_ROUND_ROBIN_MODELS or [])
_referenced_models = {m for m in _referenced_models if m}
ALLOWED_LLM_MODELS = set(ALLOWED_LLM_MODELS) | _referenced_models

NINEROUTER_API_KEY = os.getenv("NINEROUTER_API_KEY", os.getenv("OPENAI_API_KEY", ""))

# Legacy (optional direct APIs)
GEMINI_MODEL = "gemini-2.0-flash"
CLAUDE_MODEL = "claude-sonnet-4-20250514"


def _default_llm_base_url() -> str:
    if os.getenv("LLM_BASE_URL"):
        return os.getenv("LLM_BASE_URL", "").rstrip("/")
    if os.path.exists("/.dockerenv"):
        # Docker di Linux: auto-discover gateway IP atau gunakan env var
        import subprocess
        
        # Priority 1: Environment variable
        if os.getenv("OMNIROUTE_HOST"):
            return os.getenv("OMNIROUTE_HOST").rstrip("/")
        
        # Priority 2: Try to auto-discover Docker gateway
        try:
            # Get default gateway from ip route
            result = subprocess.run(
                ['ip', 'route', 'show', 'default'],
                capture_output=True, text=True, timeout=2
            )
            if result.returncode == 0 and 'via' in result.stdout:
                lines = result.stdout.strip().split('\n')
                for line in lines:
                    if 'via' in line:
                        parts = line.split()
                        if len(parts) >= 3:
                            gateway = parts[2]
                            return f"http://{gateway}:20128/v1"
        except:
            pass
        
        # Priority 3: Common Docker gateway IPs (fallback)
        # Try multiple common Docker bridge IPs
        common_gateways = [
            "172.18.0.1",  # Current streamlit network
            "172.17.0.1",  # Docker default bridge
            "host.docker.internal",  # Docker Desktop (Mac/Windows)
        ]
        
        return os.getenv("OMNIROUTE_HOST", f"http://{common_gateways[0]}:20128/v1")
    
    return "http://localhost:20128/v1"


LLM_BASE_URL = _default_llm_base_url()


def validate_llm_model(model: str) -> str:
    """Raise ValueError if model not in whitelist."""
    if model not in ALLOWED_LLM_MODELS:
        raise ValueError(
            f"Model '{model}' not in ALLOWED_LLM_MODELS. "
            f"Allowed: {sorted(ALLOWED_LLM_MODELS)}"
        )
    return model


def get_model_for_agent(agent: str, round_num: int = 1) -> str:
    """Resolve LLM model for a debate agent and round."""
    global LLM_ROUND_ROBIN_INDEX
    
    # If round-robin mode is enabled, use next model from the list
    if LLM_ROUND_ROBIN_MODELS:
        model = LLM_ROUND_ROBIN_MODELS[LLM_ROUND_ROBIN_INDEX % len(LLM_ROUND_ROBIN_MODELS)]
        LLM_ROUND_ROBIN_INDEX += 1
        return validate_llm_model(model)
    
    # Otherwise, use per-agent/per-round configuration
    if round_num >= 2:
        model = LLM_MODEL_AGENT_R2.get(agent) or LLM_MODEL_AGENT.get(agent, LLM_MODEL_DEBATE_R2)
    else:
        model = LLM_MODEL_AGENT.get(agent, LLM_MODEL_DEBATE_R1)
    return validate_llm_model(model)


def get_configured_llm_models() -> dict[str, str]:
    """Return all configured models after whitelist validation."""
    models = {
        "debate_r1": LLM_MODEL_DEBATE_R1,
        "debate_r2": LLM_MODEL_DEBATE_R2,
        "investment_manager": LLM_MODEL_INVESTMENT_MANAGER,
        "debate_fallback": LLM_MODEL_DEBATE_FALLBACK,
        "im_fallback": LLM_MODEL_IM_FALLBACK,
        "debate_r2_fallback": LLM_MODEL_DEBATE_R2_FALLBACK,
    }
    for agent, model in LLM_MODEL_AGENT.items():
        models[f"agent_r1_{agent}"] = model
    for agent, model in LLM_MODEL_AGENT_R2.items():
        models[f"agent_r2_{agent}"] = model
    for name, model in models.items():
        validate_llm_model(model)
    return models

# Database
_db_user = os.getenv("POSTGRES_USER") or "stockuser"
_db_pass = os.getenv("POSTGRES_PASSWORD") or "stockpassword"
_db_host = os.getenv("POSTGRES_HOST") or os.getenv("DB_HOST") or "stock_postgres"
_db_port = os.getenv("POSTGRES_PORT") or os.getenv("DB_PORT") or "5432"
if not str(_db_port).isdigit():
    _db_port = "5432"
_db_name = os.getenv("POSTGRES_DB") or os.getenv("DB_NAME") or "stockagent"

DATABASE_URL = f"postgresql://{_db_user}:{_db_pass}@{_db_host}:{_db_port}/{_db_name}"

# Bandarmologi
BROKER_WATCH_SHORT = 7   # hari → timing signal (sedang aktif akumulasi?)
BROKER_WATCH_LONG = 30   # hari → true avg cost bandar
TOP_BROKER_COUNT = 5     # tampilkan top 5 broker

# Bobot agent (dinamis)
WEIGHTS = {
    "default": {"bandarm": 0.35, "technical": 0.22, "fundamental": 0.18, "macro": 0.13, "news": 0.12},
    "big_cap": {"bandarm": 0.30, "technical": 0.22, "fundamental": 0.22, "macro": 0.13, "news": 0.13},
    "small_cap": {"bandarm": 0.44, "technical": 0.27, "fundamental": 0.09, "macro": 0.09, "news": 0.11},
    "volatile": {"bandarm": 0.30, "technical": 0.18, "fundamental": 0.13, "macro": 0.26, "news": 0.13},
}

BIG_CAP_TICKERS = ["BBCA", "BBRI", "BMRI", "TLKM", "ASII", "UNVR"]
SMALL_CAP_MAX_MC = 2_000_000_000_000  # < 2T = small cap
