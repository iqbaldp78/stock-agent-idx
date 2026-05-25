# 🤖 Stock Agent IDX — Project Blueprint
> Multi-Agent AI System untuk Stock Picking Pasar Indonesia

---

## Overview

**Tujuan:** Sistem multi-agent AI yang menganalisis saham IDX (LQ45 + custom watchlist), berdiskusi antar agent, dan menghasilkan **3 top pick** beserta rekomendasi entry presisi berdasarkan avg cost bandar.

**Stack:**
- 🧠 LLM: Gemini Flash (gratis) + Claude Sonnet (Phase 4 saja)
- 🤖 Agent Framework: LangGraph
- 📊 Data: yfinance, IDX API, Stockbit API
- 🖥️ UI: Streamlit
- 🗄️ Database: PostgreSQL (Docker)
- 🐳 Infra: Docker Compose (semua service)
- ⏰ Scheduler: APScheduler

---

## Bobot Agent (Dinamis)

> **Bandarmologi mendapat bobot terbesar** karena market IDX relatif tipis dan pergerakan bandar adalah alpha terkuat.

### Bobot Default (Mid Cap)

| Agent | Bobot | Alasan |
|---|---|---|
| 🔴 **Bandarmologi** | **40%** | Market mover utama IDX, akumulasi bandar = early signal terkuat |
| 🔵 **Technical** | **25%** | Konfirmasi chart & entry timing |
| 🟢 **Fundamental** | **20%** | Filter saham jelek, basis valuasi |
| 🟡 **Macro** | **15%** | Konteks pasar, bukan penentu utama per saham |

### Bobot Dinamis Berdasarkan Kondisi

```
╔══════════════════════╦═════════╦═════════╦══════════╦═════════╗
║ Kondisi              ║ Bandarm ║  Tech   ║  Fund    ║  Macro  ║
╠══════════════════════╬═════════╬═════════╬══════════╬═════════╣
║ Default (mid cap)    ║   40%   ║   25%   ║   20%    ║   15%   ║
║ Big cap (BBCA,BBRI)  ║   35%   ║   25%   ║   25%    ║   15%   ║
║ Small cap spekulatif ║   50%   ║   30%   ║   10%    ║   10%   ║
║ IHSG volatile/krisis ║   35%   ║   20%   ║   15%    ║   30%   ║
╚══════════════════════╩═════════╩═════════╩══════════╩═════════╝
```

### Contoh Dampak Bobot

```
BBCA — Bandarm kuat, chart belum breakout:
  Fundamental: 8.5 | Technical: 6.0 | Bandarm: 9.0 | Macro: 7.0

  Bobot rata (25%): 7.63
  Bobot baru (40%): 7.85 ✅ naik — sinyal bandar kuat dihargai

GOTO — Chart oke tapi distribusi:
  Fundamental: 5.0 | Technical: 6.5 | Bandarm: 3.0 | Macro: 7.0

  Bobot rata (25%): 5.38
  Bobot baru (40%): 4.88 ❌ turun — distribusi bandar langsung tersisih
```

---

## Arsitektur Sistem

```
Universe Saham (LQ45 + Custom Watchlist)
                    │
                    ▼
         ┌──────────────────┐
         │   PHASE 1        │  Rule-based filter (no LLM)
         │   FILTER         │  ~55 → ~30 saham
         └────────┬─────────┘
                  │
                  ▼
         ┌──────────────────┐
         │   PHASE 2        │  Parallel LLM scoring
         │   SCORING        │  Bobot dinamis per saham
         │                  │  ~30 → top 10–15 saham
         └────────┬─────────┘
                  │
                  ▼
         ┌──────────────────┐
         │   PHASE 3        │  Multi-agent debate
         │   DEBATE         │  10–15 → 5–7 finalis
         └────────┬─────────┘
                  │
                  ▼
         ┌──────────────────┐
         │   PHASE 4        │  Investment Manager
         │   DECISION       │  Entry zone = dekat avg bandar
         │                  │  → TOP 3 PICK
         └──────────────────┘
```

---

## Docker Architecture

```
docker-compose.yml
├── 🐳 postgres     → Database utama (port 5432)
├── 🐳 app          → Python agents + LangGraph + scheduler
└── 🐳 streamlit    → UI Dashboard (port 8501)

Volumes:
└── postgres_data   → persistent storage

Network:
└── stock_net       → internal bridge network
```

---

## Phase 0 — Setup & Persiapan

### 0.1 Checklist

```
□ Docker Desktop terinstall → docker.com/products/docker-desktop
□ Python 3.10+ (untuk dev lokal)
□ VS Code + extension Python & Docker
□ Google AI Studio API key → aistudio.google.com  (Gemini Flash, gratis)
□ Anthropic API key → console.anthropic.com       (Claude Sonnet, Phase 4)
□ Stockbit API key                                 (broker data)
□ Git terinstall
```

### 0.2 Struktur Folder

```
stock-agent/
├── agents/
│   ├── __init__.py
│   ├── fundamental.py
│   ├── technical.py
│   ├── bandarmologi.py          ← bobot 40%, avg cost 7H & 1M
│   ├── macro.py
│   └── investment_manager.py   ← entry zone = dekat avg bandar
├── graph/
│   ├── __init__.py
│   └── workflow.py              ← LangGraph orchestration
├── data/
│   ├── __init__.py
│   ├── fetcher_yfinance.py
│   ├── fetcher_idx.py
│   ├── fetcher_stockbit.py      ← broker summary + avg price 7H & 1M
│   └── filter.py
├── db/
│   ├── models.py                ← SQLAlchemy models
│   ├── tracker.py
│   └── migrations/
│       └── init.sql             ← schema PostgreSQL
├── ui/
│   └── app.py                   ← Streamlit dashboard
├── config.py
├── scheduler.py
├── docker-compose.yml
├── Dockerfile.app
├── Dockerfile.streamlit
├── .env
├── .env.example
├── .gitignore
└── requirements.txt
```

### 0.3 `.env`

```env
# LLM
GEMINI_API_KEY=your_gemini_key_here
ANTHROPIC_API_KEY=your_claude_key_here

# Stockbit
STOCKBIT_API_KEY=your_stockbit_key_here

# PostgreSQL
POSTGRES_DB=stockagent
POSTGRES_USER=stockuser
POSTGRES_PASSWORD=stockpassword
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
```

### 0.4 `docker-compose.yml`

```yaml
version: '3.9'

services:

  postgres:
    image: postgres:16-alpine
    container_name: stock_postgres
    restart: always
    environment:
      POSTGRES_DB: ${POSTGRES_DB}
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./db/migrations/init.sql:/docker-entrypoint-initdb.d/init.sql
    ports:
      - "5432:5432"
    networks:
      - stock_net
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB}"]
      interval: 10s
      timeout: 5s
      retries: 5

  app:
    build:
      context: .
      dockerfile: Dockerfile.app
    container_name: stock_app
    restart: always
    env_file: .env
    depends_on:
      postgres:
        condition: service_healthy
    volumes:
      - .:/app
    networks:
      - stock_net
    command: python scheduler.py

  streamlit:
    build:
      context: .
      dockerfile: Dockerfile.streamlit
    container_name: stock_streamlit
    restart: always
    env_file: .env
    depends_on:
      - postgres
      - app
    ports:
      - "8501:8501"
    volumes:
      - .:/app
    networks:
      - stock_net
    command: streamlit run ui/app.py --server.port=8501 --server.address=0.0.0.0

volumes:
  postgres_data:

networks:
  stock_net:
    driver: bridge
```

### 0.5 `Dockerfile.app`

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["python", "scheduler.py"]
```

### 0.6 `Dockerfile.streamlit`

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8501
CMD ["streamlit", "run", "ui/app.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

### 0.7 `config.py`

```python
import os
from dotenv import load_dotenv
load_dotenv()

# Universe saham
LQ45 = [
    "BBCA", "BBRI", "BMRI", "TLKM", "ASII",
    "UNVR", "ICBP", "KLBF", "ANTM", "INDF",
    "GOTO", "BYAN", "MDKA", "ADMR", "PGEO",
    # ... lengkapi 45 saham
]
CUSTOM_WATCHLIST = []

def get_universe():
    return list(set(LQ45 + CUSTOM_WATCHLIST))

def to_yahoo_ticker(code: str) -> str:
    return f"{code}.JK"

# Filter thresholds
MIN_VOLUME     = 1_000_000
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
BROKER_WATCH_LONG  = 30  # hari → true avg cost bandar
TOP_BROKER_COUNT   = 5   # tampilkan top 5 broker

# Bobot agent (dinamis)
WEIGHTS = {
    "default" : {"bandarm": 0.40, "technical": 0.25, "fundamental": 0.20, "macro": 0.15},
    "big_cap" : {"bandarm": 0.35, "technical": 0.25, "fundamental": 0.25, "macro": 0.15},
    "small_cap": {"bandarm": 0.50, "technical": 0.30, "fundamental": 0.10, "macro": 0.10},
    "volatile" : {"bandarm": 0.35, "technical": 0.20, "fundamental": 0.15, "macro": 0.30},
}

BIG_CAP_TICKERS  = ["BBCA", "BBRI", "BMRI", "TLKM", "ASII", "UNVR"]
SMALL_CAP_MAX_MC = 2_000_000_000_000  # < 2T = small cap
```

**Deliverable Phase 0:**
- [ ] Docker Desktop berjalan
- [ ] `docker compose up -d` sukses, semua container healthy
- [ ] `.env` terisi semua key
- [ ] `config.py` LQ45 lengkap

---

## Phase 1 — Data Layer (Fetchers)

> **Goal:** Semua agent dapat data bersih. Fetcher = jembatan antara sumber data dan agent.

### 1.1 `fetcher_yfinance.py`

```python
import yfinance as yf
import pandas as pd
from config import to_yahoo_ticker

def get_ohlcv(ticker: str, period: str = "3mo") -> pd.DataFrame:
    return yf.download(to_yahoo_ticker(ticker), period=period, progress=False)

def get_stock_info(ticker: str) -> dict:
    info = yf.Ticker(to_yahoo_ticker(ticker)).info
    return {
        "ticker"         : ticker,
        "per"            : info.get("trailingPE"),
        "pbv"            : info.get("priceToBook"),
        "market_cap"     : info.get("marketCap"),
        "roe"            : info.get("returnOnEquity"),
        "der"            : info.get("debtToEquity"),
        "revenue_growth" : info.get("revenueGrowth"),
        "earnings_growth": info.get("earningsGrowth"),
        "current_price"  : info.get("currentPrice"),
        "52w_high"       : info.get("fiftyTwoWeekHigh"),
        "52w_low"        : info.get("fiftyTwoWeekLow"),
    }
```

### 1.2 `fetcher_stockbit.py` — Core Bandarmologi

Fetcher paling penting. Mengambil data broker dengan **2 window waktu sekaligus**.

```python
def get_broker_daily(ticker: str, date: str) -> dict:
    """Broker summary untuk 1 saham di 1 tanggal."""
    # Hit Stockbit API
    return {
        "ticker": ticker,
        "date"  : date,
        "buy": [
            {"broker": "BK", "broker_name": "JP Morgan",
             "lot": 15420, "value": 14_619_000_000,
             "avg_price": 9500.0},   # value / (lot × 100)
        ],
        "sell": [
            {"broker": "AK", "broker_name": "UBS",
             "lot": 8900, "value": 8_455_000_000,
             "avg_price": 9500.0},
        ],
        "foreign_net": 5_200_000_000,
    }

def get_broker_accumulation(ticker: str, days: int) -> dict:
    """
    Agregasi broker summary untuk N hari trading ke belakang.
    Hitung avg price tiap broker = true cost mereka.
    days=7  → timing signal (sedang aktif sekarang?)
    days=30 → true avg cost bandar
    """
    trading_days = get_last_n_trading_days(days)
    daily_data   = {d: get_broker_daily(ticker, d) for d in trading_days}

    broker_totals = {}
    for date, data in daily_data.items():
        for entry in data["buy"]:
            b = entry["broker"]
            if b not in broker_totals:
                broker_totals[b] = {
                    "broker_name"    : entry["broker_name"],
                    "total_buy_lot"  : 0,
                    "total_buy_value": 0,
                    "active_days"    : 0,
                    "daily"          : {}
                }
            broker_totals[b]["total_buy_lot"]   += entry["lot"]
            broker_totals[b]["total_buy_value"] += entry["value"]
            broker_totals[b]["active_days"]     += 1
            broker_totals[b]["daily"][date]      = {
                "lot"      : entry["lot"],
                "avg_price": entry["avg_price"],
            }

    # Hitung weighted avg price per broker
    for b, data in broker_totals.items():
        data["avg_price"] = round(
            data["total_buy_value"] / (data["total_buy_lot"] * 100), 2
        ) if data["total_buy_lot"] > 0 else 0

    sorted_brokers = sorted(
        broker_totals.items(),
        key=lambda x: x[1]["total_buy_value"],
        reverse=True
    )

    foreign_net = sum(d["foreign_net"] for d in daily_data.values())

    return {
        "ticker"          : ticker,
        "window_days"     : days,
        "period"          : f"{trading_days[-1]} s/d {trading_days[0]}",
        "top_accumulators": sorted_brokers[:5],
        "daily_summary"   : daily_data,
        "foreign_net"     : foreign_net,
    }

def get_full_bandarm_data(ticker: str) -> dict:
    """Ambil kedua window sekaligus untuk 1 saham."""
    return {
        "ticker"  : ticker,
        "w7"      : get_broker_accumulation(ticker, days=7),
        "w30"     : get_broker_accumulation(ticker, days=30),
    }
```

### 1.3 `fetcher_macro.py`

```python
def get_macro_data() -> dict:
    ihsg   = yf.Ticker("^JKSE")
    usdidr = yf.Ticker("USDIDR=X")
    return {
        "ihsg_price"    : ihsg.info.get("regularMarketPrice"),
        "ihsg_change_pct": ihsg.info.get("regularMarketChangePercent"),
        "usdidr"        : usdidr.info.get("regularMarketPrice"),
        "ihsg_vs_ma20"  : calculate_vs_ma(ihsg, 20),
        "is_volatile"   : abs(ihsg.info.get("regularMarketChangePercent", 0)) > 1.5,
    }
```

### 1.4 `fetcher_idx.py`

```python
# Scraping IDX untuk fundamental lebih detail:
# Revenue, laba bersih, total aset, utang
# Dividen history, corporate action
```

**Deliverable Phase 1:**
- [ ] `fetcher_yfinance.py` — OHLCV + info semua universe
- [ ] `fetcher_stockbit.py` — broker summary + avg price window 7H & 1M
- [ ] `fetcher_macro.py` — IHSG, USD/IDR, volatility flag
- [ ] `fetcher_idx.py` — data lapkeu dasar
- [ ] Semua fetcher testable standalone

---

## Phase 2 — Filter & Scoring Agents

### 2.1 Filter Rule-Based (No LLM)

```python
# data/filter.py
def apply_filter(universe: list) -> list:
    candidates = []
    for ticker in universe:
        info    = get_stock_info(ticker)
        ohlcv   = get_ohlcv(ticker)
        avg_vol = ohlcv["Volume"].tail(20).mean()

        if avg_vol < MIN_VOLUME:                    continue
        if not info["market_cap"]:                  continue
        if info["market_cap"] < MIN_MARKET_CAP:     continue
        candidates.append(ticker)
    return candidates
```

### 2.2 Composite Score — Bobot Dinamis

```python
# graph/scoring.py
def get_weights(ticker: str, market_cap: float, is_volatile: bool) -> dict:
    if is_volatile:
        return WEIGHTS["volatile"]
    elif ticker in BIG_CAP_TICKERS:
        return WEIGHTS["big_cap"]
    elif market_cap < SMALL_CAP_MAX_MC:
        return WEIGHTS["small_cap"]
    return WEIGHTS["default"]

def calculate_composite(scores: dict, ticker: str,
                        market_cap: float, is_volatile: bool) -> dict:
    w = get_weights(ticker, market_cap, is_volatile)
    composite = (
        scores["bandarm"]     * w["bandarm"]     +
        scores["technical"]   * w["technical"]   +
        scores["fundamental"] * w["fundamental"] +
        scores["macro"]       * w["macro"]
    )
    return {
        "composite_score": round(composite, 2),
        "weights_used"   : w,
        "weight_mode"    : detect_mode(ticker, market_cap, is_volatile),
    }
```

### 2.3 Fundamental Agent

**Output JSON:**
```json
{
  "ticker"    : "BBCA",
  "score"     : 8.5,
  "signal"    : "BUY",
  "key_points": ["ROE 18% di atas industri", "PER 18x masih wajar"],
  "risks"     : ["Valuasi premium vs peers"],
  "data_used" : ["PER: 18x", "PBV: 3.2x", "ROE: 18%", "DER: 0.8x"],
  "confidence": "HIGH"
}
```

### 2.4 Technical Agent

**Output JSON:**
```json
{
  "ticker"    : "BBCA",
  "score"     : 7.8,
  "signal"    : "BUY",
  "setup"     : "Breakout resistance, volume konfirmasi",
  "entry_zone": "9400-9500",
  "target"    : "10200",
  "stop_loss" : "9100",
  "data_used" : ["RSI: 58", "MA20: 9350", "MACD: golden cross"],
  "confidence": "MEDIUM"
}
```

### 2.5 Bandarmologi Agent — Full Output

**Output JSON:**
```json
{
  "ticker"  : "BBCA",
  "score"   : 8.5,
  "signal"  : "STRONG_ACCUMULATION",
  "weight"  : "40%",

  "window_7d": {
    "period"          : "16 Mei – 24 Mei 2025",
    "assessment"      : "Bandar AKTIF akumulasi minggu ini",
    "top_accumulators": [
      {
        "broker"         : "BK",
        "broker_name"    : "JP Morgan",
        "total_buy_lot"  : 85200,
        "total_buy_value": "Rp 79.7M",
        "avg_price_7d"   : 9354,
        "active_days"    : "7/7 hari",
        "status"         : "⚡ KONSISTEN — PANTAU KETAT",
        "daily": [
          {"date": "2025-05-16", "lot": 8880,  "avg_price": 9200},
          {"date": "2025-05-19", "lot": 13200, "avg_price": 9250},
          {"date": "2025-05-20", "lot": 11500, "avg_price": 9300},
          {"date": "2025-05-21", "lot": 14100, "avg_price": 9350},
          {"date": "2025-05-22", "lot": 9800,  "avg_price": 9400},
          {"date": "2025-05-23", "lot": 12300, "avg_price": 9450},
          {"date": "2025-05-24", "lot": 15420, "avg_price": 9500}
        ]
      }
    ],
    "foreign_net_7d": "NET BUY Rp 42.5M",
    "foreign_daily" : {
      "2025-05-16": "+3.8M", "2025-05-19": "+6.3M",
      "2025-05-20": "+4.9M", "2025-05-21": "+7.8M",
      "2025-05-22": "+5.4M", "2025-05-23": "+6.1M",
      "2025-05-24": "+8.2M"
    }
  },

  "window_1m": {
    "period"          : "24 Apr – 24 Mei 2025",
    "assessment"      : "Akumulasi panjang konfirmasi posisi bandar",
    "top_accumulators": [
      {
        "broker"       : "BK",
        "broker_name"  : "JP Morgan",
        "avg_price_1m" : 9050,
        "active_days"  : "18/22 hari",
        "status"       : "⚡ AKUMULASI BESAR"
      }
    ],
    "foreign_net_1m"  : "NET BUY Rp 187M"
  },

  "price_analysis": {
    "current_price"       : 9500,
    "bandar_avg_7d"       : 9354,
    "bandar_avg_1m"       : 9050,
    "distance_from_7d"    : "+1.56%",
    "distance_from_1m"    : "+4.97%",
    "ideal_entry_zone"    : "9000–9100",
    "max_entry"           : "9400",
    "entry_status_7d"     : "🟡 ACCEPTABLE — 1.56% di atas avg mingguan bandar",
    "entry_status_1m"     : "🟠 CAUTION — 4.97% di atas true cost bandar",
    "recommendation"      : "Tunggu pullback ke 9.000–9.100 untuk entry ideal"
  },

  "broker_to_watch" : ["BK (JP Morgan)", "YU (CIMB Sekuritas)"],
  "data_used"       : ["Stockbit broker summary 7H & 1M"],
  "confidence"      : "HIGH"
}
```

### 2.6 Entry Status Logic

```python
def assess_entry_vs_bandar(current_price: float,
                            avg_7d: float,
                            avg_1m: float) -> dict:
    dist_7d = (current_price - avg_7d) / avg_7d * 100
    dist_1m = (current_price - avg_1m) / avg_1m * 100

    # Status berdasarkan jarak dari avg 1 bulan (true cost)
    if dist_1m <= 0:
        status = "🟢 IDEAL"
        label  = f"Harga {abs(dist_1m):.1f}% DI BAWAH true cost bandar — entry sangat menarik"
    elif dist_1m <= 2:
        status = "🟡 ACCEPTABLE"
        label  = f"Harga {dist_1m:.1f}% di atas true cost bandar — layak entry"
    elif dist_1m <= 5:
        status = "🟠 CAUTION"
        label  = f"Harga {dist_1m:.1f}% di atas true cost bandar — tunggu pullback"
    else:
        status = "🔴 AVOID"
        label  = f"Harga {dist_1m:.1f}% di atas true cost bandar — terlalu jauh"

    ideal_entry = round(avg_1m * 1.005, 0)  # sedikit di atas avg 1M
    max_entry   = round(avg_7d * 1.02, 0)   # max 2% di atas avg 7H

    return {
        "status_7d"        : status,
        "label"            : label,
        "distance_7d_pct"  : round(dist_7d, 2),
        "distance_1m_pct"  : round(dist_1m, 2),
        "ideal_entry_zone" : f"{round(avg_1m * 0.995, 0):.0f}–{ideal_entry:.0f}",
        "max_entry"        : f"{max_entry:.0f}",
    }
```

### 2.7 Macro Agent

```json
{
  "ihsg_trend"     : "BULLISH",
  "usdidr"         : "15800",
  "usdidr_trend"   : "STABLE",
  "is_volatile"    : false,
  "sector_outlook" : {
    "perbankan": "POSITIF",
    "mining"   : "NETRAL",
    "consumer" : "POSITIF"
  },
  "market_risk": "LOW"
}
```

**Deliverable Phase 2:**
- [ ] Filter rule-based berjalan
- [ ] 4 agent scoring paralel dengan bobot dinamis
- [ ] Bandarmologi agent output avg price 7H & 1M per broker
- [ ] Entry status logic berjalan otomatis
- [ ] Composite score dengan bobot sesuai kategori saham
- [ ] Output JSON divalidasi sebelum lanjut

---

## Phase 3 — Multi-Agent Debate

> **Goal:** Agent berdebat menyaring 10–15 kandidat → 5–7 finalis.

### 3.1 Mekanisme Debate

```
Round 1 — Initial Arguments:
  Tiap agent present case untuk kandidat mereka
  Bandarm: "BBCA — BK akumulasi 7/7 hari, avg cost 9.050, harga masih dekat"
  Tech:    "BBCA — breakout resistance dikonfirmasi volume"
  Fund:    "BBCA — ROE 18%, PER masih wajar"

Round 2 — Cross-Examination:
  "Bandarm tidak setuju TLKM — BK justru mulai distribusi kemarin"
  "Tech setuju ANTM — golden cross MA20/MA50, volume naik"

Synthesis:
  Weighted vote (bandarm vote = bobot 40%) → 5–7 finalis
```

### 3.2 LangGraph Workflow

```python
# graph/workflow.py
from langgraph.graph import StateGraph, END
from typing import TypedDict

class AgentState(TypedDict):
    universe     : list
    candidates   : list
    macro_data   : dict
    scores       : dict       # per ticker per agent
    composites   : dict       # composite score per ticker
    debate_log   : list
    finalists    : list
    top_picks    : list
    final_report : dict

workflow = StateGraph(AgentState)
workflow.add_node("filter",   run_filter)
workflow.add_node("scoring",  run_parallel_scoring)   # paralel, Gemini Flash
workflow.add_node("debate",   run_debate)              # 2 rounds, Gemini Flash
workflow.add_node("decision", run_investment_manager)  # 1 call, Claude Sonnet

workflow.set_entry_point("filter")
workflow.add_edge("filter",   "scoring")
workflow.add_edge("scoring",  "debate")
workflow.add_edge("debate",   "decision")
workflow.add_edge("decision", END)
```

**Deliverable Phase 3:**
- [ ] Debate 2 putaran berjalan
- [ ] Weighted vote memprioritaskan sinyal bandarmologi
- [ ] Log debat tersimpan ke PostgreSQL
- [ ] Output: 5–7 finalis dengan reasoning

---

## Phase 4 — Investment Manager & Final Decision

> **Goal:** Claude Sonnet mensintesis semua input → TOP 3 PICK dengan entry presisi berdasarkan avg cost bandar.

### 4.1 Output Final Investment Manager

```json
{
  "generated_at"    : "2025-05-24T16:05:00+07:00",
  "market_condition": "BULLISH — IHSG di atas MA20, foreign net buy",

  "top_picks": [
    {
      "rank"          : 1,
      "ticker"        : "BBCA",
      "thesis"        : "JP Morgan akumulasi 18/22 hari bulan ini. True cost bandar di 9.050. Harga sekarang 9.500 masih dalam range wajar. Fundamental solid + teknikal breakout = konfluens kuat.",
      "time_horizon"  : "Positional (4–6 minggu)",

      "bandar_context": {
        "broker_utama"    : "BK — JP Morgan",
        "avg_cost_7d"     : 9354,
        "avg_cost_1m"     : 9050,
        "active_days_1m"  : "18/22 hari",
        "distance_current": "+4.97% dari true cost"
      },

      "entry_zone"   : "9.000–9.100",
      "max_entry"    : "9.400",
      "target_1"     : "10.000",
      "target_2"     : "10.500",
      "stop_loss"    : "8.900",
      "risk_reward"  : "1:2.8",
      "position_size": "30% portofolio",
      "conviction"   : "HIGH",

      "entry_reasoning": "Entry ideal di 9.000–9.100 karena dekat true cost JP Morgan (9.050). Bandar tidak akan biarkan harga turun jauh dari cost mereka. SL di 8.900 = 1.5% di bawah avg bandar, risiko kecil.",

      "agent_scores": {
        "bandarm"    : {"score": 8.5, "weight": "40%", "contribution": 3.40},
        "technical"  : {"score": 7.8, "weight": "25%", "contribution": 1.95},
        "fundamental": {"score": 8.5, "weight": "20%", "contribution": 1.70},
        "macro"      : {"score": 7.0, "weight": "15%", "contribution": 1.05},
        "composite"  : 8.10
      }
    }
  ],

  "watchlist": ["TLKM", "BMRI"],
  "avoid"    : ["GOTO — asing net sell 5 hari, BK distribusi, hindari dulu"]
}
```

**Deliverable Phase 4:**
- [ ] Investment Manager pakai avg cost bandar sebagai acuan entry
- [ ] Entry reasoning menjelaskan relasi harga vs avg bandar
- [ ] Output JSON lengkap tersimpan ke PostgreSQL

---

## Phase 5 — Streamlit UI

### 5.1 Halaman Top Picks

```
┌──────────────────────────────────────────────────────┐
│  🤖 Stock Agent IDX                                  │
│  Last run: Sabtu 24 Mei 2025, 16:05 WIB              │
│  [▶ Run Analysis Now]               [⚙ Settings]    │
├──────────────────────────────────────────────────────┤
│  📈 TOP 3 PICKS                                      │
│                                                      │
│  #1 BBCA  ████████░░  8.10/10   Conviction: ✅ HIGH  │
│     Entry Ideal : 9.000–9.100  (dekat avg bandar 1M) │
│     Max Entry   : 9.400                              │
│     Target 1    : 10.000  │  Target 2: 10.500        │
│     Stop Loss   : 8.900   │  R/R: 1:2.8              │
│     ⚡ JP Morgan akumulasi 18/22 hari — avg 9.050    │
│                                                      │
│  #2 ANTM  ███████░░░  7.65/10                        │
│  #3 TLKM  ██████░░░░  7.20/10                        │
├──────────────────────────────────────────────────────┤
│  ⚠️  HINDARI: GOTO (BK distribusi, asing net sell)   │
└──────────────────────────────────────────────────────┘
```

### 5.2 Halaman Bandarmologi Detail

```
┌──────────────────────────────────────────────────────┐
│  🔍 BANDARMOLOGI — BBCA         [7 Hari] [1 Bulan]  │
├──────────────────────────────────────────────────────┤
│  🥇 BK — JP Morgan              ⚡ PANTAU KETAT      │
│                                                      │
│  Tanggal   │ Lot Beli │ Avg Price │ Bar              │
│  16 Mei    │   8.880  │   9.200   │ ██████░          │
│  19 Mei    │  13.200  │   9.250   │ █████████░       │
│  20 Mei    │  11.500  │   9.300   │ ████████░        │
│  21 Mei    │  14.100  │   9.350   │ ██████████░      │
│  22 Mei    │   9.800  │   9.400   │ ███████░         │
│  23 Mei    │  12.300  │   9.450   │ █████████░       │
│  24 Mei    │  15.420  │   9.500   │ ████████████░    │
│  ────────────────────────────────────────────────    │
│  TOTAL     │  85.200  │ AVG: 9.354│ Active: 7/7 hari │
│                                                      │
│  📊 AVG COST BANDAR                                  │
│  Avg 7 Hari  : Rp 9.354  (aktivitas terkini)        │
│  Avg 1 Bulan : Rp 9.050  (true cost bandar)         │
│  Harga kini  : Rp 9.500                              │
│                                                      │
│  Jarak dari avg 7H  : +1.56%  🟡 ACCEPTABLE         │
│  Jarak dari avg 1M  : +4.97%  🟠 CAUTION            │
│                                                      │
│  💡 Entry Ideal  : 9.000–9.100                      │
│     Max Entry   : 9.400                              │
│     Reasoning   : Dekat true cost JP Morgan (9.050)  │
├──────────────────────────────────────────────────────┤
│  🌍 FOREIGN FLOW 7 HARI                             │
│  Total Net Buy: Rp 42.5 Miliar  ↑ INCREASING        │
│  [bar chart harian]                                  │
└──────────────────────────────────────────────────────┘
```

### 5.3 Halaman Performance Tracker

```
Win Rate (30 hari): 68% | Total Signal: 47
Profitable: 32 ✅ | Loss: 15 ❌ | Open: 5 🔄

Agent Accuracy:
  Bandarmologi:  74%  ████████░░  (bobot 40%)
  Fundamental:   72%  ████████░░
  Technical:     65%  ██████░░░░
  Macro:         61%  ██████░░░░
```

**Deliverable Phase 5:**
- [ ] Halaman Top Picks dengan entry zone bandar-based
- [ ] Halaman Bandarmologi: tabel 7H & 1M, avg price per broker, entry status
- [ ] Halaman Performance Tracker per agent
- [ ] On-demand trigger
- [ ] Custom watchlist input

---

## Phase 6 — Scheduler, PostgreSQL & Validation

### 6.1 Scheduler

```python
# scheduler.py — end-of-day otomatis + auto-validation
scheduler.add_job(
    run_full_analysis,
    'cron',
    day_of_week='mon-fri',
    hour=16, minute=15,
    timezone='Asia/Jakarta'
)

scheduler.add_job(
    run_performance_check,   # update hit/miss signal kemarin
    'cron',
    day_of_week='mon-fri',
    hour=16, minute=30,
    timezone='Asia/Jakarta'
)
```

### 6.2 PostgreSQL Schema

```sql
-- db/migrations/init.sql

-- Universe saham
CREATE TABLE IF NOT EXISTS universe (
    id         SERIAL PRIMARY KEY,
    ticker     VARCHAR(10) NOT NULL UNIQUE,
    is_lq45    BOOLEAN DEFAULT TRUE,
    is_custom  BOOLEAN DEFAULT FALSE,
    active     BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Hasil scoring tiap agent
CREATE TABLE IF NOT EXISTS agent_scores (
    id                SERIAL PRIMARY KEY,
    run_date          DATE NOT NULL,
    ticker            VARCHAR(10) NOT NULL,
    fundamental_score NUMERIC(4,2),
    technical_score   NUMERIC(4,2),
    bandarm_score     NUMERIC(4,2),
    macro_signal      VARCHAR(20),
    composite_score   NUMERIC(4,2),
    weight_mode       VARCHAR(20),   -- default/big_cap/small_cap/volatile
    weights_used      JSONB,
    created_at        TIMESTAMP DEFAULT NOW()
);

-- Akumulasi broker harian (rolling 30 hari)
CREATE TABLE IF NOT EXISTS broker_accumulation (
    id           SERIAL PRIMARY KEY,
    ticker       VARCHAR(10) NOT NULL,
    trade_date   DATE NOT NULL,
    broker_code  VARCHAR(10) NOT NULL,
    broker_name  VARCHAR(100),
    buy_lot      BIGINT DEFAULT 0,
    buy_value    BIGINT DEFAULT 0,
    avg_price    NUMERIC(12,2),      -- avg price broker hari itu
    sell_lot     BIGINT DEFAULT 0,
    sell_value   BIGINT DEFAULT 0,
    foreign_net  BIGINT DEFAULT 0,
    created_at   TIMESTAMP DEFAULT NOW(),
    UNIQUE(ticker, trade_date, broker_code)
);

-- View: avg cost bandar 7 hari
CREATE OR REPLACE VIEW v_broker_avg_7d AS
SELECT
    ticker,
    broker_code,
    broker_name,
    SUM(buy_lot)                                        AS total_buy_lot,
    SUM(buy_value)                                      AS total_buy_value,
    ROUND(SUM(buy_value)::numeric /
          NULLIF(SUM(buy_lot), 0) / 100, 2)             AS avg_price_7d,
    COUNT(DISTINCT trade_date)                          AS active_days,
    MAX(trade_date)                                     AS last_active
FROM broker_accumulation
WHERE trade_date >= CURRENT_DATE - INTERVAL '10 days'
  AND buy_lot > 0
GROUP BY ticker, broker_code, broker_name
ORDER BY total_buy_value DESC;

-- View: avg cost bandar 1 bulan (true cost)
CREATE OR REPLACE VIEW v_broker_avg_1m AS
SELECT
    ticker,
    broker_code,
    broker_name,
    SUM(buy_lot)                                        AS total_buy_lot,
    SUM(buy_value)                                      AS total_buy_value,
    ROUND(SUM(buy_value)::numeric /
          NULLIF(SUM(buy_lot), 0) / 100, 2)             AS avg_price_1m,
    COUNT(DISTINCT trade_date)                          AS active_days,
    COUNT(DISTINCT trade_date) * 100.0 /
        (SELECT COUNT(DISTINCT trade_date)
         FROM broker_accumulation b2
         WHERE b2.ticker = broker_accumulation.ticker
           AND b2.trade_date >= CURRENT_DATE - INTERVAL '30 days')
                                                        AS consistency_pct
FROM broker_accumulation
WHERE trade_date >= CURRENT_DATE - INTERVAL '30 days'
  AND buy_lot > 0
GROUP BY ticker, broker_code, broker_name
ORDER BY total_buy_value DESC;

-- Log debate
CREATE TABLE IF NOT EXISTS debate_logs (
    id         SERIAL PRIMARY KEY,
    run_date   DATE NOT NULL,
    ticker     VARCHAR(10) NOT NULL,
    round      INTEGER NOT NULL,
    agent      VARCHAR(50) NOT NULL,
    argument   TEXT,
    vote       VARCHAR(10),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Final signals
CREATE TABLE IF NOT EXISTS signals (
    id               SERIAL PRIMARY KEY,
    run_date         DATE NOT NULL,
    ticker           VARCHAR(10) NOT NULL,
    rank             INTEGER,
    signal           VARCHAR(10),
    entry_low        NUMERIC(12,2),
    entry_high       NUMERIC(12,2),
    max_entry        NUMERIC(12,2),
    target_1         NUMERIC(12,2),
    target_2         NUMERIC(12,2),
    stop_loss        NUMERIC(12,2),
    risk_reward      NUMERIC(5,2),
    conviction       VARCHAR(10),
    thesis           TEXT,
    entry_reasoning  TEXT,
    bandar_avg_7d    NUMERIC(12,2),
    bandar_avg_1m    NUMERIC(12,2),
    broker_utama     VARCHAR(100),
    time_horizon     VARCHAR(50),
    weight_mode      VARCHAR(20),
    composite_score  NUMERIC(4,2),
    created_at       TIMESTAMP DEFAULT NOW()
);

-- Performance tracking
CREATE TABLE IF NOT EXISTS performance (
    id           SERIAL PRIMARY KEY,
    signal_id    INTEGER REFERENCES signals(id),
    check_date   DATE NOT NULL,
    actual_price NUMERIC(12,2),
    result       VARCHAR(20),  -- HIT_TARGET_1 / HIT_TARGET_2 / HIT_SL / OPEN
    return_pct   NUMERIC(6,2),
    created_at   TIMESTAMP DEFAULT NOW()
);

-- Index
CREATE INDEX IF NOT EXISTS idx_broker_ticker_date ON broker_accumulation(ticker, trade_date);
CREATE INDEX IF NOT EXISTS idx_signals_run_date   ON signals(run_date);
CREATE INDEX IF NOT EXISTS idx_scores_run_date    ON agent_scores(run_date, ticker);
CREATE INDEX IF NOT EXISTS idx_debate_run_date    ON debate_logs(run_date, ticker);
```

**Deliverable Phase 6:**
- [ ] Semua tabel + view terbuat via `init.sql`
- [ ] `v_broker_avg_7d` & `v_broker_avg_1m` bisa di-query langsung dari UI
- [ ] Scheduler end-of-day + performance check berjalan
- [ ] Auto-validation hit/miss signal

---

## Cara Menjalankan

```bash
# 1. Clone & setup
git clone <repo> && cd stock-agent
cp .env.example .env
# → isi semua API keys di .env

# 2. Jalankan semua service
docker compose up -d

# 3. Cek status
docker compose ps

# 4. Akses dashboard
# → http://localhost:8501

# 5. Lihat logs
docker compose logs -f app
docker compose logs -f streamlit

# 6. Stop
docker compose down
```

---

## Estimasi Timeline

| Phase | Scope | Estimasi |
|---|---|---|
| Phase 0 | Docker + setup + config | 1–2 hari |
| Phase 1 | Fetchers + Stockbit avg price | 4–6 hari |
| Phase 2 | Filter + scoring + bobot dinamis | 5–7 hari |
| Phase 3 | Debate + LangGraph | 3–4 hari |
| Phase 4 | Investment Manager + entry bandar | 2–3 hari |
| Phase 5 | Streamlit UI + bandarm chart | 4–5 hari |
| Phase 6 | Scheduler + PostgreSQL + validation | 3–4 hari |
| **Total** | **MVP siap** | **~3–4 minggu** |

---

## Estimasi Biaya Bulanan

| Komponen | Biaya |
|---|---|
| Gemini Flash (Phase 2 & 3) | **Gratis** |
| Claude Sonnet (Phase 4, ~22 call/bulan) | ~Rp 5.000–20.000 |
| Stockbit API | ~Rp 100.000–300.000 |
| Docker / hosting | **Gratis** (PC sendiri) |
| **Total** | **~Rp 100.000–320.000/bulan** |

---

## Risiko & Mitigasi

| Risiko | Mitigasi |
|---|---|
| LLM halusinasi | Output wajib JSON + validasi `data_used` |
| Stockbit API down | Cache DB, graceful fallback, skip bandarm |
| Rate limit Gemini | Cache fetcher, batch request |
| Docker container crash | `restart: always` |
| Avg bandar tidak akurat | Validasi: `value / (lot × 100)`, cross-check harga OHLCV |
| Prediksi tidak akurat | Iterasi prompt dari performance tracker |

---

> ⚠️ **Disclaimer:** Alat bantu analisis, bukan rekomendasi investasi resmi. Selalu gunakan judgment sendiri.

> 💡 **Key Insight:** Entry di dekat/bawah avg cost bandar = risk kecil karena bandar tidak akan biarkan harga turun jauh dari modal mereka.

> 🐳 **Docker First:** Semua dev & testing lewat Docker agar environment konsisten.