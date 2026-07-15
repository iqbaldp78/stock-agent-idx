.PHONY: help
help: ## Show this help message
	@echo "Stock Agent IDX - Makefile Commands"
	@echo "===================================="
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'

# ============================================================
# DOCKER COMMANDS
# ============================================================

.PHONY: up
up: ## Start all services (postgres, app, streamlit)
	docker compose up -d
	@NET_ID=$$(docker network inspect stock-agent-idx_stock_net --format '{{.Id}}' 2>/dev/null | cut -c 1-12); \
	if [ ! -z "$$NET_ID" ]; then \
		echo "Allowing port 20128 traffic for bridge br-$$NET_ID..."; \
		sudo iptables -C INPUT -i br-$$NET_ID -p tcp --dport 20128 -j ACCEPT 2>/dev/null || \
		sudo iptables -A INPUT -i br-$$NET_ID -p tcp --dport 20128 -j ACCEPT; \
	fi

.PHONY: down
down: ## Stop all services
	docker compose down

.PHONY: restart
restart: down up ## Restart all services

.PHONY: logs
logs: ## Show logs for all services
	docker compose logs -f

.PHONY: logs-app
logs-app: ## Show logs for app service only
	docker compose logs -f app

.PHONY: logs-streamlit
logs-streamlit: ## Show logs for streamlit service only
	docker compose logs -f streamlit

.PHONY: rebuild
rebuild: ## Rebuild and restart all services
	docker compose down
	docker compose build --no-cache
	docker compose up -d
	@NET_ID=$$(docker network inspect stock-agent-idx_stock_net --format '{{.Id}}' 2>/dev/null | cut -c 1-12); \
	if [ ! -z "$$NET_ID" ]; then \
		echo "Allowing port 20128 traffic for bridge br-$$NET_ID..."; \
		sudo iptables -C INPUT -i br-$$NET_ID -p tcp --dport 20128 -j ACCEPT 2>/dev/null || \
		sudo iptables -A INPUT -i br-$$NET_ID -p tcp --dport 20128 -j ACCEPT; \
	fi

.PHONY: shell
shell: ## Open shell in app container
	docker compose exec app bash

.PHONY: db-shell
db-shell: ## Open PostgreSQL shell
	docker compose exec postgres psql -U stockuser -d stockagent

# ============================================================
# WEB APP COMMANDS
# ============================================================

.PHONY: web-up
web-up: ## Start web-frontend and web-backend in docker
	docker compose up -d web_api web_frontend

.PHONY: web-down
web-down: ## Stop web-frontend and web-backend containers
	docker compose stop web_api web_frontend

.PHONY: web-logs
web-logs: ## Show logs for web-frontend and web-backend
	docker compose logs -f web_api web_frontend

.PHONY: web-frontend-dev
web-frontend-dev: ## Run web-frontend locally (on host) in dev mode
	cd web-frontend && npm install && npm run dev

.PHONY: web-backend-dev
web-backend-dev: ## Run web-backend locally (on host) in dev mode
	cd web-backend && pip install -r requirements.txt && uvicorn main:app --reload --port 8000

# ============================================================
# INDIVIDUAL AGENTS (run single agent analysis)
# ============================================================

.PHONY: agent-bandarmologi
agent-bandarmologi: ## Run bandarmologi agent (usage: make agent-bandarmologi TICKER=BBCA)
	@if [ -z "$(TICKER)" ]; then \
		echo "Error: TICKER is required. Usage: make agent-bandarmologi TICKER=BBCA"; \
		exit 1; \
	fi
	docker compose exec app python -m agents.bandarmologi $(TICKER)

.PHONY: agent-technical
agent-technical: ## Run technical agent (usage: make agent-technical TICKER=BBCA)
	@if [ -z "$(TICKER)" ]; then \
		echo "Error: TICKER is required. Usage: make agent-technical TICKER=BBCA"; \
		exit 1; \
	fi
	docker compose exec app python -m agents.technical $(TICKER)

.PHONY: agent-fundamental
agent-fundamental: ## Run fundamental agent (usage: make agent-fundamental TICKER=BBCA)
	@if [ -z "$(TICKER)" ]; then \
		echo "Error: TICKER is required. Usage: make agent-fundamental TICKER=BBCA"; \
		exit 1; \
	fi
	docker compose exec app python agents/fundamental.py --ticker $(TICKER)

.PHONY: agent-macro
agent-macro: ## Run macro agent (market-wide analysis)
	docker compose exec app python -m agents.macro

.PHONY: agent-news
agent-news: ## Run news agent (usage: make agent-news TICKER=BBCA)
	@if [ -z "$(TICKER)" ]; then \
		echo "Error: TICKER is required. Usage: make agent-news TICKER=BBCA"; \
		exit 1; \
	fi
	docker compose exec app python -m agents.news $(TICKER)

.PHONY: agent-price-predictor
agent-price-predictor: ## Run price predictor (usage: make agent-price-predictor TICKER=BBCA)
	@if [ -z "$(TICKER)" ]; then \
		echo "Error: TICKER is required. Usage: make agent-price-predictor TICKER=BBCA"; \
		exit 1; \
	fi
	docker compose exec app python -m agents.price_predictor $(TICKER)

.PHONY: all-agents
all-agents: ## Run all agents for a ticker (usage: make all-agents TICKER=BBCA)
	@if [ -z "$(TICKER)" ]; then \
		echo "Error: TICKER is required. Usage: make all-agents TICKER=BBCA"; \
		exit 1; \
	fi
	@echo "Running all agents for $(TICKER)..."
	@echo "\n=== BANDARMOLOGI ==="
	@make agent-bandarmologi TICKER=$(TICKER)
	@echo "\n=== TECHNICAL ==="
	@make agent-technical TICKER=$(TICKER)
	@echo "\n=== FUNDAMENTAL ==="
	@make agent-fundamental TICKER=$(TICKER)
	@echo "\n=== NEWS ==="
	@make agent-news TICKER=$(TICKER)

# ============================================================
# DEBATE & ANALYSIS
# ============================================================

.PHONY: debate-only
debate-only: ## Run debate workflow only (filter → scoring → debate, no full analysis)
	docker compose exec app python scripts/run_debate_only.py

.PHONY: debate-tickers
debate-tickers: ## Run debate for specific tickers (usage: make debate-tickers TICKERS="BBCA BMRI TLKM")
	@if [ -z "$(TICKERS)" ]; then \
		echo "Error: TICKERS is required. Usage: make debate-tickers TICKERS=\"BBCA BMRI TLKM\""; \
		exit 1; \
	fi
	docker compose exec app python scripts/run_debate_only.py $(TICKERS)

.PHONY: analysis-full
analysis-full: ## Run full analysis (filter → scoring → debate → investment manager)
	docker compose exec app python scripts/run_analysis.py

.PHONY: analysis-tickers
analysis-tickers: ## Run full analysis for specific tickers (usage: make analysis-tickers TICKERS="BBCA BMRI")
	@if [ -z "$(TICKERS)" ]; then \
		echo "Error: TICKERS is required. Usage: make analysis-tickers TICKERS=\"BBCA BMRI\""; \
		exit 1; \
	fi
	docker compose exec app python scripts/run_analysis.py $(TICKERS)

# ============================================================
# BACKTEST & VALIDATION
# ============================================================

PERIOD ?= 1y

.PHONY: backtest
backtest: ## Run historical backtest for all universe tickers (usage: make backtest PERIOD=max)
	docker compose exec app python scripts/backtest_signals.py --all --period $(PERIOD)

.PHONY: backtest-max
backtest-max: ## Run historical backtest for all universe tickers with max period
	@make backtest PERIOD=max

.PHONY: backtest-ticker
backtest-ticker: ## Run historical backtest for one ticker (usage: make backtest-ticker TICKER=BBCA PERIOD=5y)
	@if [ -z "$(TICKER)" ]; then \
		echo "Error: TICKER is required. Usage: make backtest-ticker TICKER=BBCA"; \
		exit 1; \
	fi
	docker compose exec app python scripts/backtest_signals.py --tickers $(TICKER) --period $(PERIOD)

.PHONY: validate-ml
validate-ml: ## Validate ML Day-1 accuracy for all universe tickers
	docker compose exec app python scripts/validate_ml_accuracy.py --all

.PHONY: train-ml
train-ml: ## Train ML Day-1 model for all universe tickers
	docker compose exec app python scripts/train_day1_model.py --all

.PHONY: train-ml-ticker
train-ml-ticker: ## Train ML Day-1 model for one ticker (usage: make train-ml-ticker TICKER=BBCA)
	@if [ -z "$(TICKER)" ]; then \
		echo "Error: TICKER is required. Usage: make train-ml-ticker TICKER=BBCA"; \
		exit 1; \
	fi
	docker compose exec app python scripts/train_day1_model.py --tickers $(TICKER)

.PHONY: train-ml-multiday
train-ml-multiday: ## Train ML Multi-Day model (T+1, T+3, T+5, T+7) for all universe tickers
	docker compose exec app python scripts/train_multiday_model.py --all

.PHONY: train-ml-multiday-ticker
train-ml-multiday-ticker: ## Train ML Multi-Day model for one ticker (usage: make train-ml-multiday-ticker TICKER=BBCA)
	@if [ -z "$(TICKER)" ]; then \
		echo "Error: TICKER is required. Usage: make train-ml-multiday-ticker TICKER=BBCA"; \
		exit 1; \
	fi
	docker compose exec app python scripts/train_multiday_model.py --tickers $(TICKER)
.PHONY: validate-ml-ticker
validate-ml-ticker: ## Validate ML Day-1 accuracy for one ticker (usage: make validate-ml-ticker TICKER=BBCA)
	@if [ -z "$(TICKER)" ]; then \
		echo "Error: TICKER is required. Usage: make validate-ml-ticker TICKER=BBCA"; \
		exit 1; \
	fi
	docker compose exec app python scripts/validate_ml_accuracy.py --ticker $(TICKER)

# ============================================================
# TESTING & SMOKE TESTS
# ============================================================

.PHONY: smoke-llm
smoke-llm: ## Test LLM connection (9Router)
	docker compose exec app python scripts/smoke_llm.py

.PHONY: smoke-debate
smoke-debate: ## Test debate personas
	docker compose exec app python scripts/smoke_debate_personas.py

.PHONY: print-debate-prompts
print-debate-prompts: ## Print debate prompts for debugging
	docker compose exec app python scripts/print_debate_prompts.py

# ============================================================
# DATA & DATABASE
# ============================================================

.PHONY: db-migrate
db-migrate: ## Run database migrations
	docker compose exec app alembic upgrade head

.PHONY: db-reset
db-reset: ## Reset database (WARNING: deletes all data)
	docker compose exec postgres psql -U stockuser -d stockagent -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
	docker compose exec postgres psql -U stockuser -d stockagent -c "SET client_min_messages TO WARNING;" -f /docker-entrypoint-initdb.d/init.sql

.PHONY: paper-reset
paper-reset: ## Reset paper trading data (wallet, trades, equity)
	@echo "Resetting paper trading data..."
	-docker compose exec -T -e "PYTHONUNBUFFERED=1" app python /app/scripts/paper_reset.py
	@echo "Done! Wallet balance has been reset."

.PHONY: db-backup
db-backup: ## Backup database to backup.sql
	docker compose exec postgres pg_dump -U stockuser stockagent > backup.sql
	@echo "Database backed up to backup.sql"

.PHONY: reset-dev-data
reset-dev-data: ## Reset development/operational data but keep portfolio and cache
	docker compose exec app python scripts/reset_dev_data.py

# ============================================================
# DEVELOPMENT
# ============================================================

.PHONY: lint
lint: ## Run code linting (if linter configured)
	@echo "Linting not configured yet. Add ruff/black/mypy to requirements.txt"

.PHONY: format
format: ## Format code (if formatter configured)
	@echo "Formatter not configured yet. Add black to requirements.txt"

.PHONY: clean
clean: ## Clean __pycache__ and temp files
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name "*.pyo" -delete 2>/dev/null || true

# ============================================================
# QUICK SHORTCUTS
# ============================================================

.PHONY: bbca
bbca: ## Quick test: all agents for BBCA
	@make all-agents TICKER=BBCA

.PHONY: antm
antm: ## Quick test: all agents for ANTM
	@make all-agents TICKER=ANTM

.PHONY: bmri
bmri: ## Quick test: all agents for BMRI
	@make all-agents TICKER=BMRI

# Default target
.DEFAULT_GOAL := help

# ============================================================
# END-TO-END TESTING
# ============================================================

.PHONY: test-ticker
test-ticker: ## Run end-to-end analysis for single ticker (usage: make test-ticker TICKER=BBCA)
	@if [ -z "$(TICKER)" ]; then \
		echo "Error: TICKER is required. Usage: make test-ticker TICKER=BBCA"; \
		exit 1; \
	fi
	docker compose exec -T app python run_single_ticker.py $(TICKER)

.PHONY: validate-schema
validate-schema: ## Validate database schema and test data insertion
	docker compose exec -T app python validate_schema.py
