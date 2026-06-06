import os
from dotenv import load_dotenv

load_dotenv()

# Universe saham LQ45 (per Juni 2026)
LQ45 = [
    "AADI", "ADMR", "ADRO", "AKRA", "AMMN",
    "AMRT", "ANTM", "ASII", "BBCA", "BBNI",
    "BBRI", "BBTN", "BMRI", "BRPT", "BUMI",
    "CPIN", "CUAN", "DEWA", "EMTK", "ESSA",
    "EXCL", "GOTO", "HRTA", "ICBP", "INCO",
    "INDF", "INKP", "ISAT", "ITMG", "JPFA",
    "KLBF", "MAPI", "MBMA", "MDKA", "MEDC",
    "PGAS", "PGEO", "PTBA", "SCMA", "SMGR",
    "TLKM", "TOWR", "UNTR", "UNVR", "WIFI",
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
    "gc/gemini-3-pro-preview",
    "gemini/gemini-2.5-pro",
    "gh/claude-opus-4.6",
    "gh/claude-opus-4.7",
    "gh/claude-sonnet-4",
    "gh/claude-sonnet-4.5",
    "gh/claude-sonnet-4.6",
    "gh/gpt-5.4",
    "gh/gemini-3-flash-preview",
    "gh/gemini-3.1-pro-preview",
    "gh/goldeneye-free-auto",
    "gh/gpt-4o-mini",
    "gh/gpt-4",
    "gh/gpt-3.5-turbo",
    "gh/gpt-5.3-codex",
    "gh/gpt-5.4-mini",
    "gh/gpt-5.2",
    "gh/gpt-4.1",
    "gh/grok-code-fast-1",
    "gh/gpt-5-mini",
    "gh/oswe-vscode-prime",
    "kr/claude-haiku-4.5",
    "kr/claude-sonnet-4.5",
    "gc/gemini-3-flash-preview",
    "gemini/gemini-2.0-flash",
    "gemini/gemini-2.0-flash-lite",
    "gemini/gemini-2.5-flash",
    "gemini/gemini-3.1-flash-lite-preview",
    "gemini/gemma-4-31b-it",
    "gemini/gemini-3-flash-preview",
    "gemini/gemini-2.5-flash-lite",
    "gemini/gemini-3.1-pro-preview",
    "ag/claude-opus-4-6-thinking",
    "ag/claude-sonnet-4-6",
    "ag/gemini-3-flash",
    "ag/gemini-pro-agent",
    "ag/gemini-3.1-pro-low",
    "ag/gemini-3-flash-agent",
    "ag/gemini-3.5-flash-extra-low",
    "ag/gpt-oss-120b-medium",
    "ag/gemini-3.5-flash-low",
    "cx/gpt-5.3-codex",
    "cx/gpt-5.3-codex-high",
    "cx/gpt-5.3-codex-high-review",
    "cx/gpt-5.3-codex-low",
    "cx/gpt-5.3-codex-low-review",
    "cx/gpt-5.3-codex-none",
    "cx/gpt-5.3-codex-none-review",
    "cx/gpt-5.3-codex-xhigh-review",
    "cx/gpt-5.3-codex-xhigh",
    "cx/gpt-5.3-codex-review",
    "cx/gpt-5.3-codex-spark",
    "cx/gpt-5.3-codex-spark-review",
    "cx/gpt-5.4",
    "cx/gpt-5.4-mini",
    "cx/gpt-5.4-mini-review",
    "cx/gpt-5.4-review",
    "cx/gpt-5.5",
    "cx/gpt-5.5-review",
    "kc/anthropic/claude-opus-4-20250514",
    "kc/anthropic/claude-sonnet-4-20250514",
    "kc/deepseek/deepseek-reasoner",
    "cl/anthropic/claude-opus-4.6",
    "cl/anthropic/claude-opus-4.7",
    "cl/anthropic/claude-sonnet-4.6",
    "cl/openai/gpt-5.3-codex",
    "cl/kwaipilot/kat-coder-pro",
    "cl/openai/gpt-5.4",
    "free",
    "kc/google/gemini-2.5-flash",
    "kc/deepseek/deepseek-chat",
    "kc/google/gemini-2.5-pro",
    "kc/openai/gpt-4.1",
    "cl/google/gemini-3.1-flash-lite-preview",
    "cl/google/gemini-3.1-pro-preview",
    "qd/dfmodel",
    "qd/dmodel",
    "qd/gm51model",
    "qd/kmodel",
    "qd/mmodel",
    "qd/auto",
    "qd/efficient",
    "qd/lite",
    "qd/qmodel",
    "nvidia/z-ai/glm4.7",
    "nvidia/minimaxai/minimax-m2.7",
    "ollama/glm-4.7-flash",
    "ollama/glm-5",
    "ollama/gpt-oss:120b",
    "ollama/qwen3.5",
    "ollama/kimi-k2.5",
    "ollama/minimax-m2.5",
    "ds/deepseek-chat",
    "ds/deepseek-reasoner",
    "ds/deepseek-v4-pro-max",
    "ds/deepseek-v4-pro-none",
    "ds/deepseek-v4-flash",
    "ds/deepseek-v4-pro",
    "groq/openai/gpt-oss-120b",
    "groq/llama-3.3-70b-versatile",
    "groq/meta-llama/llama-4-maverick-17b-128e-instruct",
    "groq/qwen/qwen3-32b",
})

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

LLM_MODEL_DEBATE_R1 = os.getenv("LLM_MODEL_DEBATE_R1", "gh/gpt-4o-mini")
LLM_MODEL_DEBATE_R2 = os.getenv("LLM_MODEL_DEBATE_R2", "gemini/gemini-2.5-flash")
LLM_MODEL_INVESTMENT_MANAGER = os.getenv(
    "LLM_MODEL_INVESTMENT_MANAGER", "gh/gpt-4o"
)
LLM_MODEL_DEBATE_FALLBACK = os.getenv("LLM_MODEL_DEBATE_FALLBACK", "gemini/gemini-2.0-flash-lite")
LLM_MODEL_IM_FALLBACK = os.getenv("LLM_MODEL_IM_FALLBACK", "gemini/gemini-2.5-pro")
LLM_MODEL_DEBATE_R2_FALLBACK = os.getenv(
    "LLM_MODEL_DEBATE_R2_FALLBACK", "gemini/gemini-2.0-flash-lite"
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
    "default": {"bandarm": 0.35, "technical": 0.22, "fundamental": 0.18, "macro": 0.13, "news": 0.12},
    "big_cap": {"bandarm": 0.30, "technical": 0.22, "fundamental": 0.22, "macro": 0.13, "news": 0.13},
    "small_cap": {"bandarm": 0.44, "technical": 0.27, "fundamental": 0.09, "macro": 0.09, "news": 0.11},
    "volatile": {"bandarm": 0.30, "technical": 0.18, "fundamental": 0.13, "macro": 0.26, "news": 0.13},
}

BIG_CAP_TICKERS = ["BBCA", "BBRI", "BMRI", "TLKM", "ASII", "UNVR"]
SMALL_CAP_MAX_MC = 2_000_000_000_000  # < 2T = small cap
