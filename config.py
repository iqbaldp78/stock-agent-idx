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

# LLM
GEMINI_MODEL = "gemini-2.0-flash"
CLAUDE_MODEL = "claude-sonnet-4-20250514"

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
