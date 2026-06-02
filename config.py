import os
from dotenv import load_dotenv

load_dotenv()

# Universe saham LQ45 (per Mei 2025)
LQ45 = [
    "ACES", "ADRO", "AKRA", "AMMN", "AMRT",
    "ANTM", "ARTO", "ASII", "BBCA", "BBNI",
    "BBRI", "BBTN", "BMRI", "BRPT", "BUKA",
    "CPIN", "ESSA", "EXCL", "GOTO", "HRUM",
    "ICBP", "INCO", "INDF", "INKP", "INTP",
    "ISAT", "ITMG", "KLBF", "MAPI", "MDKA",
    "MEDC", "MIKA", "PGAS", "PGEO", "PTBA",
    "SIDO", "SMGR", "TBIG", "TINS", "TLKM",
    "TOWR", "UNTR", "UNVR", "ESSA", "BYAN",
]

CUSTOM_WATCHLIST: list[str] = []


def get_universe() -> list[str]:
    return list(set(LQ45 + CUSTOM_WATCHLIST))


def to_yahoo_ticker(code: str) -> str:
    return f"{code}.JK"


# Filter thresholds
MIN_VOLUME = 1_000_000
MIN_MARKET_CAP = 1_000_000_000_000  # 1 Triliun IDR

# LLM — 9Router (OpenAI-compatible)
ALLOWED_LLM_MODELS = frozenset({
    "kr/claude-haiku-4.5-agentic",
    "kr/claude-haiku-4.5-thinking-agentic",
    "kr/claude-haiku-4.5-thinking",
    "kr/claude-sonnet-4.5-agentic",
    "kr/claude-sonnet-4.5-thinking-agentic",
    "kr/deepseek-3.2",
    "kr/qwen3-coder-next",
    "kr/claude-sonnet-4.5-thinking",
    "kr/MiniMax-M2.5",
    "kr/glm-5",
    "gh/claude-haiku-4.5",
    "gh/claude-opus-4.5",
    "gh/gpt-4o",
    "gh/gemini-2.5-pro",
    "gh/gpt-5.2-codex",
})

LLM_ENABLED = os.getenv("LLM_ENABLED", "true").lower() in ("true", "1", "yes")
LLM_DEBATE_MAX_TICKERS = int(os.getenv("LLM_DEBATE_MAX_TICKERS", "12"))
LLM_TEMPERATURE_DEBATE = float(os.getenv("LLM_TEMPERATURE_DEBATE", "0.3"))
LLM_TEMPERATURE_IM = float(os.getenv("LLM_TEMPERATURE_IM", "0.2"))

LLM_MODEL_DEBATE_R1 = os.getenv("LLM_MODEL_DEBATE_R1", "kr/claude-haiku-4.5-agentic")
LLM_MODEL_DEBATE_R2 = os.getenv("LLM_MODEL_DEBATE_R2", "kr/claude-haiku-4.5-thinking-agentic")
LLM_MODEL_INVESTMENT_MANAGER = os.getenv(
    "LLM_MODEL_INVESTMENT_MANAGER", "kr/claude-sonnet-4.5-thinking"
)
LLM_MODEL_DEBATE_FALLBACK = os.getenv("LLM_MODEL_DEBATE_FALLBACK", "gh/claude-haiku-4.5")
LLM_MODEL_IM_FALLBACK = os.getenv("LLM_MODEL_IM_FALLBACK", "gh/claude-opus-4.5")
LLM_MODEL_DEBATE_R2_FALLBACK = os.getenv(
    "LLM_MODEL_DEBATE_R2_FALLBACK", "kr/claude-haiku-4.5-thinking"
)

# Per-agent models (different providers = more objective debate)
LLM_MODEL_AGENT: dict[str, str] = {
    "fundamental": os.getenv("LLM_MODEL_FUNDAMENTAL", "kr/glm-5"),
    "technical": os.getenv("LLM_MODEL_TECHNICAL", "kr/deepseek-3.2"),
    "bandarmologi": os.getenv("LLM_MODEL_BANDARM", "gh/gemini-2.5-pro"),
    "macro": os.getenv("LLM_MODEL_MACRO", "gh/gpt-4o"),
}

LLM_MODEL_AGENT_R2: dict[str, str] = {
    "fundamental": os.getenv("LLM_MODEL_FUNDAMENTAL_R2", "kr/claude-haiku-4.5-thinking"),
    "technical": os.getenv("LLM_MODEL_TECHNICAL_R2", "kr/claude-haiku-4.5-thinking"),
    "bandarmologi": os.getenv("LLM_MODEL_BANDARM_R2", "kr/claude-sonnet-4.5-thinking"),
    "macro": os.getenv("LLM_MODEL_MACRO_R2", "gh/gpt-4o"),
}

NINEROUTER_API_KEY = os.getenv("NINEROUTER_API_KEY", os.getenv("OPENAI_API_KEY", ""))

# Legacy (optional direct APIs)
GEMINI_MODEL = "gemini-2.0-flash"
CLAUDE_MODEL = "claude-sonnet-4-20250514"


def _default_llm_base_url() -> str:
    if os.getenv("LLM_BASE_URL"):
        return os.getenv("LLM_BASE_URL", "").rstrip("/")
    if os.path.exists("/.dockerenv"):
        return "http://host.docker.internal:20128/v1"
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
DATABASE_URL = (
    f"postgresql://{os.getenv('POSTGRES_USER')}:"
    f"{os.getenv('POSTGRES_PASSWORD')}@"
    f"{os.getenv('POSTGRES_HOST')}:"
    f"{os.getenv('POSTGRES_PORT')}/"
    f"{os.getenv('POSTGRES_DB')}"
)

# Bandarmologi
BROKER_WATCH_SHORT = 7   # hari → timing signal (sedang aktif akumulasi?)
BROKER_WATCH_LONG = 30   # hari → true avg cost bandar
TOP_BROKER_COUNT = 5     # tampilkan top 5 broker

# Bobot agent (dinamis)
WEIGHTS = {
    "default": {"bandarm": 0.40, "technical": 0.25, "fundamental": 0.20, "macro": 0.15},
    "big_cap": {"bandarm": 0.35, "technical": 0.25, "fundamental": 0.25, "macro": 0.15},
    "small_cap": {"bandarm": 0.50, "technical": 0.30, "fundamental": 0.10, "macro": 0.10},
    "volatile": {"bandarm": 0.35, "technical": 0.20, "fundamental": 0.15, "macro": 0.30},
}

BIG_CAP_TICKERS = ["BBCA", "BBRI", "BMRI", "TLKM", "ASII", "UNVR"]
SMALL_CAP_MAX_MC = 2_000_000_000_000  # < 2T = small cap
