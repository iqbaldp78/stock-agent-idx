from sqlalchemy import (
    Column, Integer, String, Boolean, Date, DateTime, Numeric,
    Text, BigInteger, ForeignKey, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from db import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String(50), nullable=False, unique=True)
    password_hash = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())


class Universe(Base):
    __tablename__ = "universe"

    id = Column(Integer, primary_key=True)
    ticker = Column(String(10), nullable=False, unique=True)
    is_lq45 = Column(Boolean, default=True)
    is_custom = Column(Boolean, default=False)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())


class AgentScore(Base):
    __tablename__ = "agent_scores"

    id = Column(Integer, primary_key=True)
    run_date = Column(DateTime, nullable=False)
    ticker = Column(String(10), nullable=False)
    fundamental_score = Column(Numeric(4, 2))
    technical_score = Column(Numeric(4, 2))
    bandarm_score = Column(Numeric(4, 2))
    macro_signal = Column(String(20))
    composite_score = Column(Numeric(4, 2))
    weight_mode = Column(String(20))
    weights_used = Column(JSONB)
    created_at = Column(DateTime, server_default=func.now())


class BrokerAccumulation(Base):
    __tablename__ = "broker_accumulation"
    __table_args__ = (
        UniqueConstraint("ticker", "trade_date", "broker_code"),
    )

    id = Column(Integer, primary_key=True)
    ticker = Column(String(10), nullable=False)
    trade_date = Column(Date, nullable=False)
    broker_code = Column(String(10), nullable=False)
    broker_name = Column(String(100))
    buy_lot = Column(BigInteger, default=0)
    buy_value = Column(BigInteger, default=0)
    avg_price = Column(Numeric(12, 2))
    sell_lot = Column(BigInteger, default=0)
    sell_value = Column(BigInteger, default=0)
    foreign_net = Column(BigInteger, default=0)
    broker_type = Column(String(10))
    day_foreign_net = Column(BigInteger, default=0)
    created_at = Column(Date, server_default=func.now())


class DebateLog(Base):
    __tablename__ = "debate_logs"

    id = Column(Integer, primary_key=True)
    run_date = Column(DateTime, nullable=False)
    ticker = Column(String(10), nullable=False)
    round = Column(Integer, nullable=False)
    agent = Column(String(50), nullable=False)
    argument = Column(Text)
    vote = Column(String(10))
    created_at = Column(Date, server_default=func.now())


class Signal(Base):
    __tablename__ = "signals"

    id = Column(Integer, primary_key=True)
    run_date = Column(DateTime, nullable=False)
    ticker = Column(String(10), nullable=False)
    rank = Column(Integer)
    signal = Column(Text)
    entry_low = Column(Numeric(12, 2))
    entry_high = Column(Numeric(12, 2))
    max_entry = Column(Numeric(12, 2))
    target_1 = Column(Numeric(12, 2))
    target_2 = Column(Numeric(12, 2))
    target_3 = Column(Numeric(12, 2))
    stop_loss = Column(Numeric(12, 2))
    risk_reward = Column(Numeric(5, 2))
    conviction = Column(Text)
    thesis = Column(Text)
    entry_reasoning = Column(Text)
    bandar_avg_7d = Column(Numeric(12, 2))
    bandar_avg_1m = Column(Numeric(12, 2))
    broker_utama = Column(Text)
    time_horizon = Column(Text)
    weight_mode = Column(String(20))
    composite_score = Column(Numeric(4, 2))
    ml_prediction = Column(JSONB)
    price_prediction = Column(JSONB)
    tp_position_sizing = Column(JSONB)
    broker_true_costs = Column(JSONB)
    broker_distributors = Column(JSONB)
    fair_value = Column(JSONB)
    risk_reward_tp1 = Column(String(20))
    risk_reward_tp2 = Column(String(20))
    risk_reward_tp3 = Column(String(20))
    batch_id = Column(String(36))
    created_at = Column(DateTime, server_default=func.now())


class Performance(Base):
    __tablename__ = "performance"

    id = Column(Integer, primary_key=True)
    signal_id = Column(Integer, ForeignKey("signals.id"))
    check_date = Column(Date, nullable=False)
    actual_price = Column(Numeric(12, 2))
    result = Column(String(20))
    return_pct = Column(Numeric(6, 2))
    created_at = Column(Date, server_default=func.now())


# ============================================================
# Raw Data Cache Models
# ============================================================

class OhlcvPrice(Base):
    __tablename__ = "ohlcv_prices"
    __table_args__ = (UniqueConstraint("ticker", "trade_date"),)

    id = Column(Integer, primary_key=True)
    ticker = Column(String(10), nullable=False)
    trade_date = Column(Date, nullable=False)
    open = Column(Numeric(12, 2))
    high = Column(Numeric(12, 2))
    low = Column(Numeric(12, 2))
    close = Column(Numeric(12, 2))
    volume = Column(BigInteger)
    source = Column(String(20), default="stockbit")
    created_at = Column(Date, server_default=func.now())


class IhsgOhlcv(Base):
    __tablename__ = "ihsg_ohlcv"

    id = Column(Integer, primary_key=True)
    trade_date = Column(Date, nullable=False, unique=True)
    open = Column(Numeric(12, 2))
    high = Column(Numeric(12, 2))
    low = Column(Numeric(12, 2))
    close = Column(Numeric(12, 2))
    volume = Column(BigInteger)
    created_at = Column(Date, server_default=func.now())


class StockInfoSnapshot(Base):
    __tablename__ = "stock_info_snapshot"
    __table_args__ = (UniqueConstraint("ticker", "snapshot_date"),)

    id = Column(Integer, primary_key=True)
    ticker = Column(String(10), nullable=False)
    snapshot_date = Column(Date, nullable=False)
    per = Column(Numeric(10, 4))
    pbv = Column(Numeric(10, 4))
    roe = Column(Numeric(10, 4))
    der = Column(Numeric(10, 4))
    market_cap = Column(Numeric(20, 2))
    current_price = Column(Numeric(12, 2))
    revenue_growth = Column(Numeric(10, 4))
    earnings_growth = Column(Numeric(10, 4))
    high_52w = Column(Numeric(12, 2))
    low_52w = Column(Numeric(12, 2))
    dividend_yield = Column(Numeric(10, 4))
    dividend_payout_ratio = Column(Numeric(10, 4))
    dividend_per_share = Column(Numeric(12, 4))
    net_income_history = Column(JSONB)
    eps_history = Column(JSONB)
    revenue_history = Column(JSONB)
    extra_data = Column(JSONB)
    created_at = Column(Date, server_default=func.now())


class SectorOhlcv(Base):
    __tablename__ = "sector_ohlcv"
    __table_args__ = (UniqueConstraint("sector_code", "trade_date"),)

    id = Column(Integer, primary_key=True)
    sector_code = Column(String(20), nullable=False)
    trade_date = Column(Date, nullable=False)
    open = Column(Numeric(12, 4))
    high = Column(Numeric(12, 4))
    low = Column(Numeric(12, 4))
    close = Column(Numeric(12, 4))
    created_at = Column(Date, server_default=func.now())


# ============================================================
# Portfolio Management Models
# ============================================================

class PortfolioHolding(Base):
    __tablename__ = "portfolio_holdings"

    id = Column(Integer, primary_key=True)
    ticker = Column(String(10), nullable=False, unique=True)
    avg_cost = Column(Numeric(12, 2), nullable=False)
    total_shares = Column(Integer, nullable=False)
    total_invested = Column(Numeric(15, 2))
    current_price = Column(Numeric(12, 2))
    current_value = Column(Numeric(15, 2))
    unrealized_pnl = Column(Numeric(15, 2))
    unrealized_pnl_pct = Column(Numeric(6, 2))
    status = Column(String(20), default="ACTIVE")
    notes = Column(Text)
    created_at = Column(Date, server_default=func.now())
    updated_at = Column(Date, server_default=func.now())


class DcaTransaction(Base):
    __tablename__ = "dca_transactions"

    id = Column(Integer, primary_key=True)
    holding_id = Column(Integer, ForeignKey("portfolio_holdings.id"))
    ticker = Column(String(10), nullable=False)
    transaction_type = Column(String(10), nullable=False)  # BUY, SELL
    shares = Column(Integer, nullable=False)
    price = Column(Numeric(12, 2), nullable=False)
    amount = Column(Numeric(15, 2), nullable=False)
    broker_fee = Column(Numeric(10, 2), default=0)
    transaction_date = Column(Date, nullable=False)
    signal_id = Column(Integer, ForeignKey("signals.id"), nullable=True)
    notes = Column(Text)
    created_at = Column(Date, server_default=func.now())


class DcaStrategy(Base):
    __tablename__ = "dca_strategy"

    id = Column(Integer, primary_key=True)
    ticker = Column(String(10), nullable=False)
    holding_id = Column(Integer, ForeignKey("portfolio_holdings.id"), nullable=True)
    total_budget = Column(Numeric(15, 2), nullable=False)
    remaining_budget = Column(Numeric(15, 2))
    dca_count = Column(Integer, default=3)
    entry_low = Column(Numeric(12, 2))
    entry_high = Column(Numeric(12, 2))
    max_entry = Column(Numeric(12, 2))
    next_buy_price = Column(Numeric(12, 2))
    signal_id = Column(Integer, ForeignKey("signals.id"), nullable=True)
    tp1 = Column(Numeric(12, 2))
    tp2 = Column(Numeric(12, 2))
    tp3 = Column(Numeric(12, 2))
    stop_loss = Column(Numeric(12, 2))
    status = Column(String(20), default="ACTIVE")
    activated_at = Column(Date)
    completed_at = Column(Date)
    created_at = Column(Date, server_default=func.now())


# ============================================================
# Paper Trading Models
# ============================================================

class PaperWallet(Base):
    __tablename__ = "paper_wallet"
    
    id = Column(Integer, primary_key=True)
    cash = Column(Numeric(15, 2), default=0)         # saldo cash
    total_topup = Column(Numeric(15, 2), default=0)  # total modal diisi
    total_invested = Column(Numeric(15, 2), default=0)  # total uang masuk saham
    total_pnl = Column(Numeric(15, 2), default=0)    # total realized P&L
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now())


class PaperTrade(Base):
    __tablename__ = "paper_trades"
    
    id = Column(Integer, primary_key=True)
    ticker = Column(String(10), nullable=False)
    action = Column(String(10), nullable=False)      # BUY/SELL
    lot = Column(Integer, nullable=False)            # 1 lot = 100 lembar
    shares = Column(Integer, nullable=False)         # lot × 100
    price = Column(Numeric(12, 2), nullable=False)   # harga eksekusi
    amount = Column(Numeric(15, 2), nullable=False)  # total nilai (shares × price)
    fee = Column(Numeric(10, 2), default=0)          # fee transaksi
    signal_id = Column(Integer, ForeignKey("signals.id"), nullable=True)
    tp1 = Column(Numeric(12, 2))                     # take-profit level 1
    tp2 = Column(Numeric(12, 2))
    tp3 = Column(Numeric(12, 2))
    stop_loss = Column(Numeric(12, 2))
    status = Column(String(20), default="OPEN")      # PENDING/OPEN/CLOSED/TP_HIT/SL_HIT
    opened_at = Column(DateTime, server_default=func.now())
    closed_at = Column(DateTime)
    realized_pnl = Column(Numeric(15, 2), default=0)  # P&L setelah close
    realized_pnl_pct = Column(Numeric(6, 2), default=0)
    notes = Column(Text)
    exit_price = Column(Numeric(12, 2))              # harga jual/exit saat close

    # Foreign key to wallet (optional, bisa dihitung aggregat)
    wallet_id = Column(Integer, ForeignKey("paper_wallet.id"), nullable=True)
