"""
Paper Trading Service — Virtual portfolio validator.

Features:
- Topup wallet
- Buy/sell with lot calculator
- Auto fee calculation (0.1% buy / 0.2% sell)
- TP/SL tracking
- Realized P&L calculation
"""

from decimal import Decimal
from datetime import datetime, date
from typing import Optional
from sqlalchemy.orm import Session
from db.models import PaperWallet, PaperTrade, Signal
from db import SessionLocal
import logging

logger = logging.getLogger(__name__)


def _get_current_price(ticker: str) -> Optional[float]:
    """Fetch harga real-time dari Stockbit API (primary), fallback ke DB cache."""
    # Primary: Stockbit API
    try:
        from data.fetcher_stockbit import get_current_price_stockbit
        price = get_current_price_stockbit(ticker)
        if price and price > 0:
            logger.debug(f"[paper_trading] Stockbit price for {ticker}: {price}")
            return float(price)
    except Exception as e:
        logger.warning(f"[paper_trading] Stockbit API failed for {ticker}: {e}")
    
    # Fallback: DB cache (latest OHLCV)
    try:
        from db.cache import get_cached_ohlcv
        from datetime import timedelta
        end = date.today().isoformat()
        start = (date.today() - timedelta(days=7)).isoformat()
        df = get_cached_ohlcv(ticker, start, end)
        if df is not None and not df.empty and "close" in df.columns:
            return float(df["close"].iloc[-1])
    except Exception as e:
        logger.warning(f"[paper_trading] DB cache fallback failed for {ticker}: {e}")
    
    return None


def _get_day_change_pct(ticker: str, current_price: Optional[float] = None) -> Optional[float]:
    """Fetch % perubahan harga harian real-time dari Stockbit API."""
    try:
        from data.fetcher_stockbit import get_realtime_stock_info_stockbit
        info = get_realtime_stock_info_stockbit(ticker)
        if info and "change_pct" in info and info["change_pct"] is not None:
            return float(info["change_pct"])
    except Exception as e:
        logger.warning(f"[paper_trading] Stockbit realtime info failed for {ticker}: {e}")

    try:
        from db.cache import get_cached_ohlcv
        from datetime import timedelta
        end = date.today().isoformat()
        start = (date.today() - timedelta(days=7)).isoformat()
        df = get_cached_ohlcv(ticker, start, end)
        if df is not None and len(df) >= 2 and "close" in df.columns:
            prev_close = float(df["close"].iloc[-2])
            curr = current_price or float(df["close"].iloc[-1])
            if prev_close > 0:
                return round(((curr - prev_close) / prev_close) * 100, 2)
    except Exception:
        pass

    return None


class PaperTradingService:
    """Service untuk manage paper trading operations."""
    
    BUY_FEE_PCT = 0.001   # 0.1%
    SELL_FEE_PCT = 0.002  # 0.2%
    LOT_SIZE = 100        # 1 lot = 100 lembar
    
    def __init__(self, session: Optional[Session] = None):
        self.session = session or SessionLocal()
        self.user_id = None
    
    # === WALLET OPERATIONS ===
    
    def get_or_create_wallet(self) -> PaperWallet:
        """Get existing wallet or create new one (1 wallet per user)."""
        if self.user_id:
            wallet = self.session.query(PaperWallet).filter(PaperWallet.user_id == self.user_id).order_by(PaperWallet.id.asc()).first()
        else:
            wallet = self.session.query(PaperWallet).order_by(PaperWallet.id.asc()).first()
            
        if not wallet:
            wallet = PaperWallet(
                cash=Decimal("0"),
                total_topup=Decimal("0"),
                total_invested=Decimal("0"),
                total_pnl=Decimal("0"),
                user_id=self.user_id
            )
            self.session.add(wallet)
            self.session.commit()
        else:
            # Heal any existing None values in DB to prevent NoneType TypeError
            dirty = False
            if wallet.cash is None:
                wallet.cash = Decimal("0")
                dirty = True
            if wallet.total_topup is None:
                wallet.total_topup = Decimal("0")
                dirty = True
            if wallet.total_invested is None:
                wallet.total_invested = Decimal("0")
                dirty = True
            if wallet.total_pnl is None:
                wallet.total_pnl = Decimal("0")
                dirty = True
            if dirty:
                self.session.commit()
        return wallet
    
    def topup(self, amount: float) -> dict:
        """
        Topup wallet dengan modal virtual.
        
        Args:
            amount: Jumlah topup (contoh: 100_000_000 untuk 100jt)
        
        Returns:
            dict dengan status dan wallet info
        """
        wallet = self.get_or_create_wallet()
        
        topup_amount = Decimal(str(amount))
        wallet.cash += topup_amount
        wallet.total_topup += topup_amount
        wallet.updated_at = datetime.utcnow()
        
        self.session.commit()
        self.session.refresh(wallet)
        
        return {
            "status": "success",
            "message": f"Topup Rp {amount:,.0f} berhasil",
            "wallet": {
                "cash": float(wallet.cash),
                "total_topup": float(wallet.total_topup),
                "total_invested": float(wallet.total_invested),
                "total_pnl": float(wallet.total_pnl),
                "equity": float(wallet.cash + wallet.total_invested)
            }
        }
    
    def get_wallet_summary(self, auto_check_tpsl: bool = True, auto_create: bool = True) -> Optional[dict]:
        """Get wallet balance + unrealized P&L dari open positions (real-time price)."""
        if auto_create:
            wallet = self.get_or_create_wallet()
        else:
            if self.user_id:
                wallet = self.session.query(PaperWallet).filter(PaperWallet.user_id == self.user_id).order_by(PaperWallet.id.asc()).first()
            else:
                wallet = self.session.query(PaperWallet).order_by(PaperWallet.id.asc()).first()
            if not wallet:
                return None


        query = self.session.query(PaperTrade).filter(
            PaperTrade.status.in_(["OPEN", "PENDING_LIMIT", "PENDING_STOP"]),
            PaperTrade.wallet_id == wallet.id
        )
        active_trades = query.all()

        unrealized_pnl = Decimal("0")
        positions = []
        auto_closed = []

        for trade in active_trades:
            current_price = _get_current_price(trade.ticker)
            if not current_price:
                current_price = float(trade.price)  # fallback ke buy price

            day_change_pct = _get_day_change_pct(trade.ticker, current_price)

            # Auto evaluate pending order
            if trade.status in ["PENDING_LIMIT", "PENDING_STOP"]:
                matched = False
                if trade.status == "PENDING_LIMIT" and current_price <= float(trade.price):
                    matched = True
                elif trade.status == "PENDING_STOP" and current_price >= float(trade.price):
                    matched = True

                if matched:
                    # Order matched!
                    trade.status = "OPEN"
                    trade.opened_at = datetime.utcnow()
                    self.session.commit()
                else:
                    # Still pending
                    positions.append({
                        "id": trade.id,
                        "ticker": trade.ticker,
                        "lot": trade.lot,
                        "shares": trade.shares,
                        "buy_price": float(trade.price),
                        "current_price": float(current_price),
                        "day_change_pct": day_change_pct,
                        "current_value": float(trade.amount), # keep original amount
                        "unrealized_pnl": 0.0,
                        "unrealized_pnl_pct": 0.0,
                        "tp1": float(trade.tp1) if trade.tp1 else None,
                        "stop_loss": float(trade.stop_loss) if trade.stop_loss else None,
                        "opened_at": trade.opened_at.strftime("%Y-%m-%d %H:%M") if trade.opened_at else None,
                        "status": trade.status,
                    })
                    continue

            # Open position logic
            current_value = Decimal(str(current_price)) * trade.shares
            pnl = current_value - trade.amount
            pnl_pct = (pnl / trade.amount) * 100 if trade.amount > 0 else Decimal("0")

            # Auto TP/SL check
            if auto_check_tpsl:
                if trade.tp1 and current_price >= float(trade.tp1):
                    result = self.sell(trade.id, current_price, reason="TP_HIT")
                    auto_closed.append({"ticker": trade.ticker, "reason": "TP_HIT", "pnl": result.get("trade", {}).get("realized_pnl", 0)})
                    continue
                elif trade.stop_loss and current_price <= float(trade.stop_loss):
                    result = self.sell(trade.id, current_price, reason="SL_HIT")
                    auto_closed.append({"ticker": trade.ticker, "reason": "SL_HIT", "pnl": result.get("trade", {}).get("realized_pnl", 0)})
                    continue

            unrealized_pnl += pnl
            positions.append({
                "id": trade.id,
                "ticker": trade.ticker,
                "lot": trade.lot,
                "shares": trade.shares,
                "buy_price": float(trade.price),
                "current_price": float(current_price),
                "day_change_pct": day_change_pct,
                "current_value": float(current_value),
                "unrealized_pnl": float(pnl),
                "unrealized_pnl_pct": float(pnl_pct),
                "tp1": float(trade.tp1) if trade.tp1 else None,
                "stop_loss": float(trade.stop_loss) if trade.stop_loss else None,
                "opened_at": trade.opened_at.strftime("%Y-%m-%d %H:%M") if trade.opened_at else None,
                "status": trade.status,
            })

        # Refresh wallet after potential TP/SL closes
        self.session.refresh(wallet)

        # Fix out-of-sync invested amount by summing up all active/pending trades
        dynamic_invested = sum([t.amount for t in active_trades if t.status in ["OPEN", "PENDING_LIMIT", "PENDING_STOP"]])
        
        # Self-healing logic
        if wallet.total_invested != dynamic_invested:
            wallet.total_invested = dynamic_invested
            self.session.commit()

        total_equity = wallet.cash + wallet.total_invested + unrealized_pnl
        total_return_pct = (
            (total_equity - wallet.total_topup) / wallet.total_topup * 100
            if wallet.total_topup > 0 else Decimal("0")
        )

        return {
            "cash": float(wallet.cash),
            "total_topup": float(wallet.total_topup),
            "total_invested": float(wallet.total_invested),
            "realized_pnl": float(wallet.total_pnl),
            "unrealized_pnl": float(unrealized_pnl),
            "total_equity": float(total_equity),
            "total_return_pct": float(total_return_pct),
            "positions": positions,
            "auto_closed": auto_closed,
        }
    
    # === TRADING OPERATIONS ===
    
    def calculate_max_lot(self, price: float) -> int:
        """
        Calculate maximum lot yang bisa dibeli berdasarkan cash tersedia.
        
        Args:
            price: Harga saham per lembar
        
        Returns:
            Jumlah lot maksimum
        """
        wallet = self.get_or_create_wallet()
        
        # Formula: lot = floor(cash / (price × 100 × 1.001))
        # 1.001 = buy fee factor (0.1%)
        price_decimal = Decimal(str(price))
        cost_per_lot = price_decimal * self.LOT_SIZE * (1 + Decimal(str(self.BUY_FEE_PCT)))
        
        max_lot = int(wallet.cash / cost_per_lot)
        return max_lot
    
    def buy(
        self, 
        ticker: str, 
        lot: int, 
        price: float,
        signal_id: Optional[int] = None,
        tp1: Optional[float] = None,
        tp2: Optional[float] = None,
        tp3: Optional[float] = None,
        stop_loss: Optional[float] = None,
        notes: Optional[str] = None
    ) -> dict:
        """
        Execute buy order (paper trading).
        
        Args:
            ticker: Kode saham (e.g., "BBRI")
            lot: Jumlah lot (1 lot = 100 lembar)
            price: Harga beli per lembar
            signal_id: ID signal dari top picks (optional)
            tp1, tp2, tp3: Take-profit levels (optional)
            stop_loss: Stop-loss level (optional)
            notes: Catatan tambahan
        
        Returns:
            dict dengan status dan trade info
        """
        wallet = self.get_or_create_wallet()
        
        # Calculate amounts
        shares = lot * self.LOT_SIZE
        amount = Decimal(str(price)) * shares
        fee = amount * Decimal(str(self.BUY_FEE_PCT))
        total_cost = amount + fee

        # Check saldo
        if wallet.cash < total_cost:
            return {
                "status": "error",
                "message": f"Saldo tidak cukup. Butuh Rp {float(total_cost):,.0f}, tersedia Rp {float(wallet.cash):,.0f}"
            }
            
        # Validate TP / SL
        if tp1 and tp1 <= price:
            return {"status": "error", "message": f"Target TP1 ({tp1}) harus lebih besar dari harga beli ({price})"}
        if tp2 and tp2 <= price:
            return {"status": "error", "message": f"Target TP2 ({tp2}) harus lebih besar dari harga beli ({price})"}
        if tp3 and tp3 <= price:
            return {"status": "error", "message": f"Target TP3 ({tp3}) harus lebih besar dari harga beli ({price})"}
        if stop_loss and stop_loss >= price:
            return {"status": "error", "message": f"Stop Loss ({stop_loss}) harus lebih kecil dari harga beli ({price})"}

        # Check current price to determine status
        current_price = _get_current_price(ticker)
        trade_status = "OPEN"
        if current_price:
            if price < current_price:
                trade_status = "PENDING_LIMIT"
            elif price > current_price:
                trade_status = "PENDING_STOP"

        # Deduct cash
        wallet.cash -= total_cost
        wallet.total_invested += amount
        wallet.updated_at = datetime.utcnow()
        
        # Create trade
        # Create trade
        trade = PaperTrade(
            user_id=self.user_id,
            ticker=ticker,
            action="BUY",
            lot=lot,
            shares=shares,
            price=Decimal(str(price)),
            amount=amount,
            fee=fee,
            signal_id=signal_id,
            tp1=Decimal(str(tp1)) if tp1 else None,
            tp2=Decimal(str(tp2)) if tp2 else None,
            tp3=Decimal(str(tp3)) if tp3 else None,
            stop_loss=Decimal(str(stop_loss)) if stop_loss else None,
            status=trade_status,
            notes=notes,
            wallet_id=wallet.id
        )
        
        self.session.add(trade)
        self.session.commit()
        self.session.refresh(trade)
        
        return {
            "status": "success",
            "message": f"BUY {lot} lot {ticker} @ Rp {price:,.0f} berhasil",
            "trade": {
                "id": trade.id,
                "ticker": trade.ticker,
                "action": trade.action,
                "lot": trade.lot,
                "shares": trade.shares,
                "price": float(trade.price),
                "amount": float(trade.amount),
                "fee": float(trade.fee),
                "total_cost": float(total_cost),
                "opened_at": trade.opened_at.isoformat()
            },
            "wallet": self.get_wallet_summary()
        }
    def cancel_pending_order(self, trade_id: int) -> dict:
        """
        Batalkan pending order dan kembalikan dana yang terkunci ke cash wallet.
        """
        query = self.session.query(PaperTrade).filter(
            PaperTrade.id == trade_id,
            PaperTrade.status.in_(["PENDING_LIMIT", "PENDING_STOP"])
        )
        if self.user_id:
            query = query.filter(PaperTrade.user_id == self.user_id)
        
        trade = query.first()
        
        if not trade:
            return {
                "status": "error",
                "message": f"Pending order ID {trade_id} tidak ditemukan atau sudah match"
            }
            
        wallet = self.get_or_create_wallet()
        
        # Return locked cash (amount + fee)
        total_cost = trade.amount + trade.fee
        wallet.cash += total_cost
        wallet.total_invested -= trade.amount
        wallet.updated_at = datetime.utcnow()
        
        # Mark as cancelled
        trade.status = "CANCELLED"
        trade.closed_at = datetime.utcnow()
        
        self.session.commit()
        
        return {
            "status": "success",
            "message": f"Pending order {trade.ticker} dibatalkan. Cash Rp {float(total_cost):,.0f} dikembalikan."
        }
        

    def sell(self, trade_id: int, price: float, reason: str = "MANUAL") -> dict:
        """
        Execute sell order (close position).
        
        Args:
            trade_id: ID trade yang akan di-close
            price: Harga jual per lembar
            reason: Alasan jual ("MANUAL", "TP_HIT", "SL_HIT")
        
        Returns:
            dict dengan status, trade info, dan realized P&L
        """
        query = self.session.query(PaperTrade).filter(
            PaperTrade.id == trade_id,
            PaperTrade.status == "OPEN"
        )
        if self.user_id:
            query = query.filter(PaperTrade.user_id == self.user_id)
            
        trade = query.first()
        
        if not trade:
            return {
                "status": "error",
                "message": f"Trade ID {trade_id} tidak ditemukan atau sudah closed"
            }
        
        wallet = self.get_or_create_wallet()
        
        # Calculate amounts
        gross_amount = Decimal(str(price)) * trade.shares
        fee = gross_amount * Decimal(str(self.SELL_FEE_PCT))
        net_amount = gross_amount - fee
        
        # Calculate realized P&L
        realized_pnl = net_amount - trade.amount
        realized_pnl_pct = (realized_pnl / trade.amount * 100) if trade.amount > 0 else 0
        
        # Update wallet
        wallet.cash += net_amount
        wallet.total_invested -= trade.amount
        wallet.total_pnl += realized_pnl
        wallet.updated_at = datetime.utcnow()
        
        # Update trade
        trade.status = reason if reason in ["TP_HIT", "SL_HIT"] else "CLOSED"
        trade.closed_at = datetime.utcnow()
        trade.realized_pnl = realized_pnl
        trade.realized_pnl_pct = realized_pnl_pct
        trade.exit_price = price
        
        self.session.commit()
        self.session.refresh(trade)
        
        return {
            "status": "success",
            "message": f"SELL {trade.lot} lot {trade.ticker} @ Rp {price:,.0f} berhasil",
            "trade": {
                "id": trade.id,
                "ticker": trade.ticker,
                "lot": trade.lot,
                "buy_price": float(trade.price),
                "sell_price": price,
                "realized_pnl": float(realized_pnl),
                "realized_pnl_pct": float(realized_pnl_pct),
                "closed_at": trade.closed_at.isoformat()
            },
            "wallet": self.get_wallet_summary()
        }
    
    def auto_execute_signal(
        self,
        signal_id: int,
        budget_pct: float = 0.20,  # 20% dari cash
        price: Optional[float] = None
    ) -> dict:
        """
        Auto-execute buy berdasarkan signal dari top picks.
        
        Args:
            signal_id: ID signal dari top picks
            budget_pct: Persentase cash yang dialokasikan (default 20%)
            price: Harga beli (jika None, pakai entry_low dari signal)
        
        Returns:
            dict dengan status dan trade info
        """
        signal = self.session.query(Signal).filter(Signal.id == signal_id).first()
        
        if not signal:
            return {
                "status": "error",
                "message": f"Signal ID {signal_id} tidak ditemukan"
            }
        
        wallet = self.get_or_create_wallet()
        
        # Determine buy price
        if not price:
            # Pakai entry_low atau entry_high atau fallback ke current price
            price = float(signal.entry_low) if signal.entry_low else None
            if not price:
                return {
                    "status": "error",
                    "message": "Harga tidak ditemukan. Tentukan harga manual."
                }
        
        # Calculate budget
        budget = float(wallet.cash) * budget_pct
        lot = int(budget / (price * self.LOT_SIZE * (1 + self.BUY_FEE_PCT)))
        
        if lot <= 0:
            return {
                "status": "error",
                "message": f"Budget tidak cukup untuk membeli minimal 1 lot"
            }
        
        # Execute buy
        return self.buy(
            ticker=signal.ticker,
            lot=lot,
            price=price,
            signal_id=signal_id,
            tp1=float(signal.target_1) if getattr(signal, "target_1", None) else None,
            tp2=float(signal.target_2) if getattr(signal, "target_2", None) else None,
            tp3=float(signal.target_3) if getattr(signal, "target_3", None) else None,
            stop_loss=float(signal.stop_loss) if getattr(signal, "stop_loss", None) else None,
            notes=f"Auto-executed from signal #{signal_id}"
        )
    
    def check_tp_sl(self, current_prices: dict) -> list:
        """
        Check semua open positions untuk TP/SL hit, termasuk pending orders.
        """
        # Handle OPEN positions: TP/SL
        query = self.session.query(PaperTrade).filter(PaperTrade.status == "OPEN")
        if self.user_id:
            query = query.filter(PaperTrade.user_id == self.user_id)
        open_trades = query.all()

        closed_trades = []

        for trade in open_trades:
            current_price = current_prices.get(trade.ticker)
            if not current_price:
                continue
            
            # Check TP1
            if trade.tp1 and current_price >= float(trade.tp1):
                result = self.sell(trade.id, current_price, reason="TP_HIT")
                closed_trades.append(result)
            
            # Check SL
            elif trade.stop_loss and current_price <= float(trade.stop_loss):
                result = self.sell(trade.id, current_price, reason="SL_HIT")
                closed_trades.append(result)

        # Handle PENDING orders: limit buy/sell
        query_pending = self.session.query(PaperTrade).filter(PaperTrade.status == "PENDING")
        if self.user_id:
            query_pending = query_pending.filter(PaperTrade.user_id == self.user_id)
        pending_trades = query_pending.all()

        executed_pending = []
        for trade in pending_trades:
            current_price = current_prices.get(trade.ticker)
            if not current_price:
                continue
            
            pending_price = float(trade.pending_price) if trade.pending_price else None
            pending_type = trade.pending_type
            
            if not pending_price:
                continue
            
            # PENDING BUY: execute when live price <= pending price
            if pending_type == "limit_buy" and current_price <= pending_price:
                trade.status = "OPEN"
                opened_at = datetime.utcnow()
                trade.opened_at = opened_at
                trade.price = Decimal(str(current_price))
                trade.amount = Decimal(str(current_price)) * trade.shares
                fee = trade.amount * Decimal(str(self.BUY_FEE_PCT))
                trade.fee = fee
                
                wallet = self.get_or_create_wallet()
                total_cost = trade.amount + fee
                if wallet.cash >= total_cost:
                    wallet.cash -= total_cost
                    wallet.total_invested += trade.amount
                    wallet.updated_at = datetime.utcnow()
                    self.session.commit()
                    self.session.refresh(trade)
                    executed_pending.append({
                        "ticker": trade.ticker,
                        "reason": "PENDING_BUY_FILLED",
                        "price": float(current_price),
                        "lot": trade.lot
                    })
            
            # PENDING SELL: execute when live price >= pending price
            elif pending_type == "limit_sell" and current_price >= pending_price:
                result = self.sell(trade.id, current_price, reason="PENDING_SELL_FILLED")
                executed_pending.append(result)

        return closed_trades

    def get_trade_history(self, limit: int = 50) -> list:
        """Get semua trades (open + closed)."""
        query = self.session.query(PaperTrade)
        if self.user_id:
            query = query.filter(PaperTrade.user_id == self.user_id)
        trades = query.order_by(
            PaperTrade.opened_at.desc()
        ).limit(limit).all()
        return [
            {
                "id": t.id,
                "ticker": t.ticker,
                "action": t.action,
                "lot": t.lot,
                "shares": t.shares,
                "price": float(t.price),
                "exit_price": float(t.exit_price) if t.exit_price is not None else None,
                "tp1": float(t.tp1) if t.tp1 is not None else None,
                "tp2": float(t.tp2) if t.tp2 is not None else None,
                "tp3": float(t.tp3) if t.tp3 is not None else None,
                "stop_loss": float(t.stop_loss) if t.stop_loss is not None else None,
                "amount": float(t.amount),
                "status": t.status,
                "realized_pnl": float(t.realized_pnl) if t.realized_pnl is not None else None,
                "realized_pnl_pct": float(t.realized_pnl_pct) if t.realized_pnl_pct is not None else None,
                "opened_at": t.opened_at.isoformat() if t.opened_at else None,
                "closed_at": t.closed_at.isoformat() if t.closed_at else None
            }
            for t in trades
        ]

    def get_performance_metrics(self) -> dict:
        """Calculate overall performance metrics for the current user."""
        if not self.user_id:
            return {"status": "error", "message": "User ID is required"}

        wallet = self.session.query(PaperWallet).filter(PaperWallet.user_id == self.user_id).order_by(PaperWallet.id.asc()).first()
        if not wallet:
            return {
                "total_trades": 0,
                "win_rate_pct": 0.0,
                "profit_factor": 0.0,
                "total_profit": 0,
                "total_loss": 0,
                "avg_return_pct": 0.0,
                "winning_trades": 0,
                "losing_trades": 0
            }

        trades = self.session.query(PaperTrade).filter(
            PaperTrade.wallet_id == wallet.id,
            PaperTrade.status.notin_(["OPEN", "PENDING_LIMIT", "PENDING_STOP", "CANCELLED"])
        ).all()

        total_trades = len(trades)
        if total_trades == 0:
            return {
                "total_trades": 0,
                "win_rate_pct": 0.0,
                "profit_factor": 0.0,
                "total_profit": 0,
                "total_loss": 0,
                "avg_return_pct": 0.0,
                "winning_trades": 0,
                "losing_trades": 0
            }

        winning_trades = 0
        losing_trades = 0
        total_profit = Decimal("0")
        total_loss = Decimal("0")
        total_return_pct = Decimal("0")

        for t in trades:
            pnl = t.realized_pnl or Decimal("0")
            pct = t.realized_pnl_pct or Decimal("0")
            total_return_pct += pct
            
            if pnl > 0:
                winning_trades += 1
                total_profit += pnl
            elif pnl < 0:
                losing_trades += 1
                total_loss += abs(pnl)

        win_rate = (winning_trades / total_trades) * 100 if total_trades > 0 else 0.0
        profit_factor = float(total_profit) / float(total_loss) if total_loss > 0 else float(total_profit)
        avg_return = float(total_return_pct) / total_trades if total_trades > 0 else 0.0

        return {
            "total_trades": total_trades,
            "win_rate_pct": float(win_rate),
            "profit_factor": profit_factor,
            "total_profit": float(total_profit),
            "total_loss": float(total_loss),
            "avg_return_pct": avg_return,
            "winning_trades": winning_trades,
            "losing_trades": losing_trades
        }

    def get_equity_history(self) -> dict:
        """Generate equity curve dari trade history."""
        query = self.session.query(PaperTrade)
        if self.user_id:
            query = query.filter(PaperTrade.user_id == self.user_id)
        all_trades = query.order_by(
            PaperTrade.opened_at
        ).all()

        equity_points = []
        current_equity = Decimal("0")
        wallet = self.get_or_create_wallet()

        # Starting point: initial topup
        if wallet.total_topup > 0:
            equity_points.append({
                "date": wallet.created_at.date().isoformat() if wallet.created_at else datetime.utcnow().date().isoformat(),
                "equity": float(wallet.total_topup),
                "cash": float(wallet.total_topup),
                "invested": 0.0,
                "pnl": 0.0,
                "event": "INITIAL_TOPUP"
            })

        for trade in all_trades:
            trade_date = trade.opened_at.date() if trade.opened_at else datetime.utcnow().date()
            
            if trade.action == "BUY":
                # Update cash & invested
                current_cash = float(wallet.cash) - float(trade.amount + trade.fee)
                current_invested = float(wallet.total_invested) + float(trade.amount)
                current_equity = current_cash + current_invested

                equity_points.append({
                    "date": trade_date.isoformat(),
                    "equity": float(current_equity),
                    "cash": float(current_cash),
                    "invested": float(current_invested),
                    "pnl": float(wallet.total_pnl),
                    "event": f"BUY {trade.ticker} {trade.lot} lot"
                })

            elif trade.action == "SELL":
                current_cash = float(wallet.cash) + float(trade.amount - trade.fee)
                current_invested = float(wallet.total_invested) - float(trade.amount)
                current_equity = current_cash + current_invested

                equity_points.append({
                    "date": trade_date.isoformat(),
                    "equity": float(current_equity),
                    "cash": float(current_cash),
                    "invested": float(current_invested),
                    "pnl": float(wallet.total_pnl),
                    "event": f"SELL {trade.ticker} P&L Rp {float(trade.realized_pnl):+,.0f}"
                })

        # Add current snapshot
        summary = self.get_wallet_summary(auto_check_tpsl=False)
        
        # Self-heal logic if wallet completely empty (new user)
        if len(equity_points) == 0 and summary["total_equity"] == 0:
             equity_points.append({
                 "date": datetime.utcnow().date().isoformat(),
                 "equity": 0.0,
                 "cash": 0.0,
                 "invested": 0.0,
                 "pnl": 0.0,
                 "event": "NO_DATA"
             })
        else:
             equity_points.append({
                 "date": datetime.utcnow().date().isoformat(),
                 "equity": float(summary["total_equity"]),
                 "cash": float(summary["cash"]),
                 "invested": float(summary["total_invested"]),
                 "pnl": float(summary["realized_pnl"] + summary["unrealized_pnl"]),
                 "event": "CURRENT"
             })
            
        return {
            "points": equity_points,
            "start_equity": float(wallet.total_topup),
            "current_equity": float(summary["total_equity"]),
            "total_return_pct": float(summary["total_return_pct"]),
            "win_rate": float(summary.get("win_rate", 0.0))
        }

    def auto_execute_all_top_picks(self, budget_pct_per_trade: float = 0.15) -> dict:
        """
        Auto-execute semua top picks dalam satu batch.
        
        Args:
            budget_pct_per_trade: Budget per ticker (default 15%)
        
        Returns:
            dict dengan hasil semua trades
        """
        try:
            from sqlalchemy import text
            from db import engine
            
            with engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT * FROM signals
                    WHERE run_date = (SELECT MAX(run_date) FROM signals)
                    AND rank IS NOT NULL
                    ORDER BY rank
                    LIMIT 3
                """))
                signals = [dict(row._mapping) for row in result]
        except Exception as e:
            return {
                "status": "error",
                "message": f"Cannot fetch top picks: {e}"
            }

        if not signals:
            return {
                "status": "info",
                "message": "No top picks found"
            }

        results = []
        failed = []
        wallet = self.get_or_create_wallet()

        for sig in signals:
            # Recommended entry price (entry_high or entry_low)
            target_price = float(sig.get("entry_high") or sig.get("entry_low") or 0)
            
            # Get current price
            current_price = _get_current_price(sig["ticker"])
            
            # Default to target price, fallback to current price
            if target_price > 0:
                execute_price = target_price
            elif current_price:
                execute_price = current_price
            else:
                execute_price = 1000

            # Execute buy
            result = self.auto_execute_signal(
                signal_id=sig["id"],
                budget_pct=budget_pct_per_trade,
                price=execute_price
            )

            if result["status"] == "success":
                results.append(result)
            else:
                failed.append({"ticker": sig["ticker"], "error": result["message"]})

        return {
            "status": "success",
            "message": f"Executed {len(results)} trades, {len(failed)} failed",
            "results": results,
            "failed": failed,
            "total_executed": len(results)
        }

    def reset_wallet(self) -> dict:
        """Reset wallet dan hapus semua trades (untuk mulai dari awal)."""
        wallet = self.get_or_create_wallet()
        
        # Delete all trades
        query = self.session.query(PaperTrade)
        if self.user_id:
            query = query.filter(PaperTrade.user_id == self.user_id)
        query.delete()
        
        # Reset wallet
        wallet.cash = Decimal("0")
        wallet.total_topup = Decimal("0")
        wallet.total_invested = Decimal("0")
        wallet.total_pnl = Decimal("0")
        wallet.updated_at = datetime.utcnow()
        
        self.session.commit()
        
        return {
            "status": "success",
            "message": "Wallet berhasil di-reset",
            "wallet": self.get_wallet_summary(auto_check_tpsl=False)
        }
