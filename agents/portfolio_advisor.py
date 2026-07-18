"""
AI Portfolio Advisor Agent
All-in-one portfolio analysis: rebalancing, DCA priority, risk analysis, performance attribution.
"""
import logging
import json
from datetime import datetime, timezone, timedelta
from typing import Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

from agents.llm_client import invoke_json
from config import LLM_MODEL_IM_FALLBACK

logger = logging.getLogger(__name__)


def _get_realtime_prices(tickers: list[str]) -> dict[str, float]:
    """
    Fetch realtime prices untuk multiple tickers dari Stockbit.
    Parallel fetch untuk kecepatan.
    Returns: {ticker: price}
    """
    try:
        from data.fetcher_stockbit import get_current_price_stockbit
    except ImportError:
        logger.warning("[Portfolio AI] Stockbit fetcher not available")
        return {}

    prices = {}
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {
            executor.submit(get_current_price_stockbit, ticker): ticker
            for ticker in tickers if ticker
        }
        for future in as_completed(futures):
            ticker = futures[future]
            try:
                price = future.result()
                if price and price > 0:
                    prices[ticker] = price
                    logger.info(f"[Portfolio AI] Realtime price: {ticker}={price}")
            except Exception as e:
                logger.warning(f"[Portfolio AI] Failed to get realtime price for {ticker}: {e}")

    return prices


def analyze_portfolio(
    holdings: list[dict],
    active_strategies: list[dict],
    top_picks: list[dict],
    monthly_budget: float,
    transactions: list[dict],
) -> dict:
    """
    AI Portfolio analysis menggunakan LLM dengan realtime prices dari Stockbit.

    Returns structured JSON dengan rebalancing, DCA priority, risk analysis, performance attribution.
    """

    # Build context
    logger.info(f"[Portfolio AI] Processing holdings: {holdings}")

    # Fetch realtime prices untuk semua tickers
    all_tickers = [h.get("ticker") for h in holdings if h.get("ticker")]
    all_tickers.extend([p.get("ticker") for p in top_picks if p.get("ticker")])
    all_tickers = list(set(all_tickers))  # Remove duplicates

    realtime_prices = _get_realtime_prices(all_tickers)
    logger.info(f"[Portfolio AI] Fetched realtime prices for {len(realtime_prices)} tickers")

    # Update holdings dan top_picks dengan realtime prices
    for h in holdings:
        ticker = h.get("ticker")
        if ticker in realtime_prices:
            h["current_price"] = realtime_prices[ticker]

    for p in top_picks:
        ticker = p.get("ticker")
        if ticker in realtime_prices:
            p["current_price"] = realtime_prices[ticker]

    context = _build_portfolio_context(holdings, active_strategies, top_picks, monthly_budget, transactions)

    # Retrieve RAG news context for holdings tickers
    news_context = _get_rag_news_context(holdings)
    
    # System prompt
    system_prompt = """Anda adalah Manajer Portofolio berpengalaman untuk pasar saham Indonesia (IDX/LQ45) yang berspesialisasi dalam investasi jangka panjang dengan strategi DCA (Dollar Cost Averaging).

Tugas Anda adalah menganalisis portofolio dan memberikan rekomendasi yang dapat ditindaklanjuti dalam format JSON.

Skema JSON Output:
{
    "summary": "Ringkasan eksekutif dalam 2-3 kalimat dalam Bahasa Indonesia",
    "rebalancing": {
        "needed": true/false,
        "overweight": ["TICKER1", "TICKER2"],
        "underweight": ["TICKER3"],
        "actions": [
            {"ticker": "TICKER", "action": "REDUCE/INCREASE/HOLD", "reason": "..."}
        ]
    },
    "dca_priority": [
        {
            "rank": 1,
            "ticker": "TICKER",
            "allocation": 800000,
            "target_price": 4000,
            "target_lots": 20,
            "timing_status": "IDEAL/ACCEPTABLE/CAUTION",
            "conviction": "HIGH/MEDIUM/LOW",
            "reasoning": "Mengapa ticker ini menjadi prioritas..."
        }
    ],
    "risk_analysis": {
        "sector_concentration": {"banking": 40, "mining": 30, "consumer": 20, "other": 10},
        "risk_level": "LOW/MEDIUM/HIGH",
        "diversification_score": 7.5,
        "recommendations": ["Tambah eksposur sektor konsumsi", "Kurangi konsentrasi perbankan"]
    },
    "performance_attribution": {
        "best_performer": {"ticker": "TICKER", "return_pct": 15.2, "reason": "..."},
        "worst_performer": {"ticker": "TICKER", "return_pct": -3.5, "reason": "..."},
        "signal_quality": "X/Y sinyal menguntungkan"
    }
}

Penting:
- Gunakan Bahasa Indonesia untuk semua output teks.
- Spesifik dengan angka (jumlah alokasi, harga, persentase).
- Fokus pada wawasan yang dapat ditindaklanjuti.
- Pertimbangkan waktu (true cost bandar) saat memberi peringkat prioritas DCA.
- Alokasikan anggaran bulanan hanya untuk 3 prioritas teratas.
- Tingkat risiko berdasarkan konsentrasi sektor + volatilitas P&L.
- Skor diversifikasi 1-10 (lebih tinggi = lebih baik).
- Untuk DCA Priority, sertakan "target_price" (harga ideal pembelian) dan "target_lots" (jumlah lot berdasarkan alokasi dan target_price; 1 lot = 100 lembar).
"""

    user_prompt = f"""PORTFOLIO SAAT INI (dengan harga realtime dari Stockbit):
{context['portfolio_summary']}

DETAIL HOLDINGS (HARGA DIUPDATE REALTIME):
{context['holdings_detail']}

STRATEGI DCA AKTIF:
{context['dca_strategies']}

TOP PICKS TERBARU (Peluang Investasi - HARGA REALTIME):
{context['top_picks_detail']}

ANGGARAN DCA BULANAN: Rp {monthly_budget:,.0f}

KINERJA HISTORIS:
{context['performance_summary']}

BERITA & SENTIMEN TERKINI (dari RAG/Vector Database):
{news_context}

Berikan analisis portofolio komprehensif yang mencakup:
1. Rebalancing: Apakah portofolio seimbang? Holding mana yang kelebihan/kekurangan bobot? Rekomendasikan tindakan.
2. Prioritas DCA: Dari TOP PICKS + holding saat ini, beri peringkat 3 ticker teratas untuk dibeli bulan ini. Alokasikan anggaran bulanan. Pertimbangkan waktu, keyakinan, dan keseimbangan. ANDA WAJIB MENGISI field "target_price" dan "target_lots" untuk SETIAP ticker prioritas. Pertimbangkan juga berita/sentimen terkini dari RAG di atas.
3. Analisis Risiko: Konsentrasi sektor, skor diversifikasi, tingkat risiko, rekomendasi.
4. Atribusi Kinerja: Peraih untung/rugi terbaik, kualitas sinyal, pelajaran yang dipetik.

CATATAN PENTING:
- Semua harga di atas adalah harga REALTIME terbaru dari Stockbit (bukan cache/stale data).
- Gunakan harga realtime ini untuk menghitung target allocation, target price, dan target lots yang akurat.
- Output harus berupa JSON ketat sesuai skema yang disediakan.
"""

    try:
        result = invoke_json(
            model=LLM_MODEL_IM_FALLBACK,
            system=system_prompt,
            user=user_prompt,
            temperature=0.3,
            max_tokens=4096,
            agent="portfolio_advisor",
        )

        if result is None:
            logger.error("[Portfolio AI] invoke_json returned None")
            return _error_response("LLM returned no valid JSON response")

        result["generated_at"] = datetime.now(timezone.utc).astimezone(timezone(timedelta(hours=7))).strftime("%Y-%m-%d %H:%M:%S WIB")
        
        # Post-process dca_priority to guarantee target_price and target_lots
        try:
            price_map = {}
            for h in holdings:
                if h.get("ticker"):
                    p = h.get("current_price")
                    if not p or p <= 0:
                        p = h.get("avg_cost", 0)
                    price_map[h["ticker"]] = p
            for tp in top_picks:
                if tp.get("ticker"):
                    p = tp.get("current_price")
                    if not p or p <= 0:
                        p = tp.get("target_price", 0)
                    price_map[tp["ticker"]] = p
            
            dca = result.get("dca_priority")
            if dca and isinstance(dca, list):
                for item in dca:
                    ticker = item.get("ticker")
                    alloc = item.get("allocation", 0)
                    if ticker and alloc > 0 and ticker in price_map:
                        price = price_map[ticker]
                        if price and price > 0:
                            item["target_price"] = price
                            item["target_lots"] = int(alloc // (price * 100))
        except Exception as e:
            logger.error(f"[Portfolio AI] Post-process error: {e}")

        logger.info(f"[Portfolio AI] Analysis completed: {result.get('summary', '')[:100]}")
        return result

    except Exception as e:
        logger.error(f"[Portfolio AI] Error: {e}")
        return _error_response(str(e))


def _get_rag_news_context(holdings: list[dict]) -> str:
    """Retrieve recent news from RAG (pgvector) for each ticker in holdings."""
    try:
        from scripts.rag_retriever import search_by_ticker, format_for_prompt
        
        tickers = [h.get("ticker") for h in holdings if h.get("ticker")]
        if not tickers:
            return "Tidak ada berita terkini yang tersedia."
        
        all_news = []
        for ticker in tickers:
            try:
                news = search_by_ticker(ticker, limit=3)
                if news:
                    all_news.append(f"--- {ticker} ---")
                    all_news.append(format_for_prompt(news))
            except Exception as e:
                logger.warning(f"[Portfolio AI] RAG search failed for {ticker}: {e}")
                continue
        
        if not all_news:
            return "Tidak ada berita terkini yang tersedia untuk ticker di portofolio."
        
        logger.info(f"[Portfolio AI] RAG retrieved news for {len(tickers)} tickers")
        return "\n".join(all_news)
    except ImportError:
        logger.warning("[Portfolio AI] RAG retriever not available")
        return "RAG retriever tidak tersedia."
    except Exception as e:
        logger.error(f"[Portfolio AI] RAG retrieval error: {e}")
        return "Gagal mengambil berita dari RAG."


def _build_portfolio_context(
    holdings: list[dict],
    active_strategies: list[dict],
    top_picks: list[dict],
    monthly_budget: float,
    transactions: list[dict],
) -> dict:
    """Build structured context string dari data portfolio."""

    # Portfolio summary
    total_invested = sum(h.get('total_invested', 0) for h in holdings)
    total_current = sum(h.get('current_value', 0) or 0 for h in holdings)
    total_pnl = total_current - total_invested if total_current > 0 else 0
    total_pnl_pct = (total_pnl / total_invested * 100) if total_invested > 0 else 0

    portfolio_summary = f"""Total Holdings: {len(holdings)}
Total Invested: Rp {total_invested:,.0f}
Current Value: Rp {total_current:,.0f}
Unrealized P&L: Rp {total_pnl:+,.0f} ({total_pnl_pct:+.2f}%)
"""

    # Holdings detail
    holdings_lines = []
    for h in holdings:
        ticker = h['ticker']
        lots = h.get('total_lots', 0)
        avg = h.get('avg_cost', 0)
        curr = h.get('current_price') or 0
        pnl_pct = h.get('unrealized_pnl_pct')
        invested = h.get('total_invested', 0)
        weight = (invested / total_invested * 100) if total_invested > 0 else 0
        current_value = lots * curr

        # Pastikan data tersedia dengan memberikan nilai default jika kosong
        line = f"- {ticker}: {lots} lot, Nilai: Rp {current_value:,.0f} (Avg: Rp {avg:,.0f})"
        if curr:
            line += f" | Harga Terkini: Rp {curr:,.0f}"
        if pnl_pct is not None:
            line += f" | P&L: {pnl_pct:+.2f}%"
        line += f" | Bobot: {weight:.1f}%"
        holdings_lines.append(line)

    holdings_detail = "\n".join(holdings_lines) if holdings_lines else "No holdings yet."

    # DCA strategies
    dca_lines = []
    for s in active_strategies:
        ticker = s['ticker']
        budget = s.get('total_budget', 0)
        used = s.get('used_budget', 0)
        remaining = s.get('remaining_budget', 0)
        next_buy = s.get('next_buy_price')

        line = f"- {ticker}: Budget Rp {budget:,.0f}, Used Rp {used:,.0f}, Remaining Rp {remaining:,.0f}"
        if next_buy:
            line += f", Next Buy @ Rp {next_buy:,.0f}"
        dca_lines.append(line)

    dca_strategies = "\n".join(dca_lines) if dca_lines else "No active DCA strategies."

    # TOP PICKS
    picks_lines = []
    for p in top_picks[:5]:  # Top 5 only
        ticker = p.get('ticker')
        entry_low = p.get('entry_low')
        max_entry = p.get('max_entry')
        conviction = p.get('conviction', 'N/A')
        thesis = p.get('thesis', '')[:100]
        bandar_1m = p.get('bandar_avg_1m')

        line = f"- {ticker}: Entry {entry_low}-{max_entry}, Conviction: {conviction}"
        if bandar_1m:
            line += f", True Cost Bandar 1M: Rp {bandar_1m:,.0f}"
        if thesis:
            line += f"\n  Thesis: {thesis}..."
        picks_lines.append(line)

    top_picks_detail = "\n".join(picks_lines) if picks_lines else "No TOP PICKS available."

    # Performance summary
    buy_txns = [t for t in transactions if t.get('transaction_type') == 'BUY']
    sell_txns = [t for t in transactions if t.get('transaction_type') == 'SELL']

    performance_summary = f"""Total Transactions: {len(transactions)}
- BUY: {len(buy_txns)}
- SELL: {len(sell_txns)}

Recent activity (last 30 days): {len([t for t in transactions if _is_recent(t.get('transaction_date'))])} transactions
"""

    return {
        "portfolio_summary": portfolio_summary,
        "holdings_detail": holdings_detail,
        "dca_strategies": dca_strategies,
        "top_picks_detail": top_picks_detail,
        "performance_summary": performance_summary,
    }


def _is_recent(date_str: Optional[str], days: int = 30) -> bool:
    """Check if date is within last N days."""
    if not date_str:
        return False
    try:
        from datetime import date, timedelta
        txn_date = datetime.strptime(str(date_str), "%Y-%m-%d").date()
        return (date.today() - txn_date).days <= days
    except Exception:
        return False


def _error_response(error_msg: str) -> dict:
    """Return error response in expected schema."""
    wib_tz = timezone(timedelta(hours=7))
    now_wib = datetime.now(wib_tz).strftime("%Y-%m-%d %H:%M:%S WIB")

    return {
        "summary": f"Analysis failed: {error_msg}",
        "rebalancing": {
            "needed": False,
            "overweight": [],
            "underweight": [],
            "actions": [],
        },
        "dca_priority": [],
        "risk_analysis": {
            "sector_concentration": {},
            "risk_level": "UNKNOWN",
            "diversification_score": 0,
            "recommendations": [f"Error: {error_msg}"],
        },
        "performance_attribution": {
            "best_performer": None,
            "worst_performer": None,
            "signal_quality": "N/A",
        },
        "generated_at": now_wib,
        "error": error_msg,
    }
