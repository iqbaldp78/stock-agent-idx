"""
Data Fetcher — IDX
Scraping/API data dari IDX untuk fundamental lebih detail.
Saat ini menggunakan yfinance sebagai fallback.
Akan diintegrasikan dengan IDX API jika tersedia.
"""
import yfinance as yf
from config import to_yahoo_ticker


def get_financial_summary(ticker: str) -> dict:
    """
    Ambil ringkasan keuangan dari IDX.
    Fallback: yfinance quarterly financials.
    """
    try:
        t = yf.Ticker(to_yahoo_ticker(ticker))
        info = t.info

        return {
            "ticker": ticker,
            "revenue": info.get("totalRevenue"),
            "net_income": info.get("netIncomeToCommon"),
            "total_assets": info.get("totalAssets"),
            "total_debt": info.get("totalDebt"),
            "free_cash_flow": info.get("freeCashflow"),
            "dividend_yield": info.get("dividendYield"),
            "dividend_rate": info.get("dividendRate"),
            "payout_ratio": info.get("payoutRatio"),
            "sector": info.get("sector"),
            "industry": info.get("industry"),
        }
    except Exception:
        return {
            "ticker": ticker,
            "revenue": None,
            "net_income": None,
            "total_assets": None,
            "total_debt": None,
            "free_cash_flow": None,
            "dividend_yield": None,
            "dividend_rate": None,
            "payout_ratio": None,
            "sector": None,
            "industry": None,
        }


def get_corporate_actions(ticker: str) -> dict:
    """Ambil corporate actions (dividen, stock split, rights issue)."""
    try:
        t = yf.Ticker(to_yahoo_ticker(ticker))
        dividends = t.dividends
        splits = t.splits

        recent_dividends = []
        if not dividends.empty:
            recent = dividends.tail(5)
            for date, amount in recent.items():
                recent_dividends.append({
                    "date": str(date.date()),
                    "amount": float(amount),
                })

        recent_splits = []
        if not splits.empty:
            recent = splits.tail(3)
            for date, ratio in recent.items():
                recent_splits.append({
                    "date": str(date.date()),
                    "ratio": f"1:{int(ratio)}",
                })

        return {
            "ticker": ticker,
            "dividends": recent_dividends,
            "splits": recent_splits,
        }
    except Exception:
        return {
            "ticker": ticker,
            "dividends": [],
            "splits": [],
        }
