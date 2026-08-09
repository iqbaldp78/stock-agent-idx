# Project Rules for stock-engine-prediction-v2

## Technical Analysis Preference
When building or modifying technical indicators, Support & Resistance levels, or momentum tracking in agents (e.g. `technical.py`), **always prioritize fetching data from the `tradingview_ta` integration** (e.g., using TradingView's native Pivot Points, RSI, MACD, etc.) instead of manually calculating these indicators using raw OHLCV historical data.

This ensures the agent relies on industry-standard algorithms and minimizes code complexity.

## Strict Container Execution & Debugging Rule
When executing Python scripts, running unit tests (`pytest`), debugging feature code, checking database states, or reading application logs, **NEVER run execution commands directly on the host machine OS environment**.

Always trigger the [`container_debugging`](file:///.agents/skills/container_debugging/SKILL.md) skill and execute all commands inside Docker containers (e.g. `docker compose exec -T app python ...`, `docker compose exec -T web_api pytest ...`, etc.).

