"use client";
import React, { useState, useEffect } from 'react';
import { useApp } from '../../context/AppContext';

const PORTFOLIO_TABS = [
  { id: "holdings", label: "📊 Holdings Overview" },
  { id: "dca", label: "💰 DCA Manager" },
  { id: "history", label: "📜 Transaction History" },
  { id: "performance", label: "📈 Performance Report" },
  { id: "ai", label: "🤖 AI Analysis" },
] as const;

type PortfolioSubTab = typeof PORTFOLIO_TABS[number]['id'];

export default function PortfolioPage() {
  const { picks, showToast } = useApp();
  const [portfolioTab, setPortfolioTab] = useState<PortfolioSubTab>("holdings");

  // --- State: Holdings ---
  const [portfolioHoldings, setPortfolioHoldings] = useState<any[]>([]);
  const [portfolioSummary, setPortfolioSummary] = useState<any>({});
  const [newHoldingTicker, setNewHoldingTicker] = useState("");
  const [newHoldingLots, setNewHoldingLots] = useState(10);
  const [newHoldingAvg, setNewHoldingAvg] = useState(1000);
  const [newHoldingNotes, setNewHoldingNotes] = useState("");

  // --- State: DCA ---
  const [dcaStrategies, setDcaStrategies] = useState<any[]>([]);
  const [dcaBudget, setDcaBudget] = useState(10000000);
  const [dcaCount, setDcaCount] = useState(3);
  const [dcaMode, setDcaMode] = useState<"signal" | "manual">("signal");
  const [selectedSignalId, setSelectedSignalId] = useState<number | null>(null);
  const [previewDcaLevels, setPreviewDcaLevels] = useState<any[]>([]);
  const [dcaLevelsLoading, setDcaLevelsLoading] = useState(false);
  const [manualDcaTicker, setManualDcaTicker] = useState("");
  const [manualEntryLow, setManualEntryLow] = useState(0);
  const [manualEntryHigh, setManualEntryHigh] = useState(0);
  const [manualMaxEntry, setManualMaxEntry] = useState(0);
  const [timingTicker, setTimingTicker] = useState("");
  const [timingResult, setTimingResult] = useState<any>(null);
  const [timingLoading, setTimingLoading] = useState(false);

  // --- State: Transactions ---
  const [portfolioTxns, setPortfolioTxns] = useState<any[]>([]);
  const [txnFilterTicker, setTxnFilterTicker] = useState("ALL");
  const [txnFilterType, setTxnFilterType] = useState("ALL");
  const [recordTxnTicker, setRecordTxnTicker] = useState("");
  const [recordTxnType, setRecordTxnType] = useState<"BUY" | "SELL">("BUY");
  const [recordTxnLots, setRecordTxnLots] = useState(10);
  const [recordTxnPrice, setRecordTxnPrice] = useState(1000);
  const [recordTxnNotes, setRecordTxnNotes] = useState("");
  const [buyPreview, setBuyPreview] = useState<any>(null);

  // --- State: AI Analysis ---
  const [aiMonthlyBudget, setAiMonthlyBudget] = useState(5000000);
  const [aiAnalysisLoading, setAiAnalysisLoading] = useState(false);
  const [aiAnalysisResult, setAiAnalysisResult] = useState<any>(null);

  // --- Data Fetching ---
  const fetchPortfolioData = async () => {
    const token = localStorage.getItem("token");
    try {
      const res = await fetch("/api/portfolio/holdings", { headers: { Authorization: `Bearer ${token}` } });
      const data = await res.json();
      if (data.holdings) setPortfolioHoldings(data.holdings);
      if (data.summary) setPortfolioSummary(data.summary);
    } catch (e) { console.error(e); }
  };

  const fetchDcaStrategies = async () => {
    const token = localStorage.getItem("token");
    try {
      const res = await fetch("/api/portfolio/dca", { headers: { Authorization: `Bearer ${token}` } });
      const data = await res.json();
      if (data.strategies) setDcaStrategies(data.strategies);
    } catch (e) { console.error(e); }
  };

  const fetchTransactions = async () => {
    const token = localStorage.getItem("token");
    try {
      const res = await fetch("/api/portfolio/transactions", { headers: { Authorization: `Bearer ${token}` } });
      const data = await res.json();
      if (data.transactions) setPortfolioTxns(data.transactions);
    } catch (e) { console.error(e); }
  };

  useEffect(() => {
    fetchPortfolioData();
    fetchDcaStrategies();
    fetchTransactions();
  }, []);

  // Buy Preview useEffect
  useEffect(() => {
    if (recordTxnType !== "BUY" || !recordTxnTicker || !recordTxnLots || !recordTxnPrice) { setBuyPreview(null); return; }
    const holding = portfolioHoldings.find(h => h.ticker === recordTxnTicker);
    if (!holding) { setBuyPreview(null); return; }
    const currentShares = holding.shares;
    const currentAvg = holding.avg_cost;
    const newShares = recordTxnLots * 100;
    const totalShares = currentShares + newShares;
    const newAvgCost = ((currentShares * currentAvg) + (newShares * recordTxnPrice)) / totalShares;
    setBuyPreview({ current_avg: currentAvg, new_avg_cost: newAvgCost, total_lots_after: totalShares / 100 });
  }, [recordTxnTicker, recordTxnType, recordTxnLots, recordTxnPrice, portfolioHoldings]);

  // --- Handlers ---
  const handleAddHolding = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newHoldingTicker.trim()) { showToast("Ticker tidak boleh kosong", 'error'); return; }
    const token = localStorage.getItem("token");
    const res = await fetch("/api/portfolio/holdings/add", {
      method: "POST", headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
      body: JSON.stringify({ ticker: newHoldingTicker.toUpperCase(), lot: newHoldingLots, avg_cost: newHoldingAvg, notes: newHoldingNotes })
    });
    const data = await res.json();
    if (res.ok) { showToast(data.message || "Holding berhasil ditambahkan"); fetchPortfolioData(); setNewHoldingTicker(""); setNewHoldingLots(10); setNewHoldingAvg(1000); setNewHoldingNotes(""); }
    else showToast(data.detail || "Gagal menambahkan holding", 'error');
  };

  const handleRecordTransaction = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!recordTxnTicker) { showToast("Pilih ticker terlebih dahulu", 'error'); return; }
    const token = localStorage.getItem("token");
    const res = await fetch("/api/portfolio/transactions", {
      method: "POST", headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
      body: JSON.stringify({ ticker: recordTxnTicker, transaction_type: recordTxnType, lot: recordTxnLots, price: recordTxnPrice, notes: recordTxnNotes })
    });
    const data = await res.json();
    if (res.ok) { showToast(data.message || "Transaksi berhasil dicatat"); fetchPortfolioData(); fetchTransactions(); setRecordTxnNotes(""); }
    else showToast(data.detail || "Gagal mencatat transaksi", 'error');
  };

  const handleResetHoldings = async () => {
    if (!confirm("Apakah Anda yakin ingin mereset SELURUH data portfolio?")) return;
    const token = localStorage.getItem("token");
    const res = await fetch("/api/portfolio/reset", { method: "POST", headers: { Authorization: `Bearer ${token}` } });
    const data = await res.json();
    if (res.ok) { showToast(data.message || "Data portfolio berhasil direset"); fetchPortfolioData(); fetchTransactions(); }
    else showToast(data.detail || "Gagal mereset portfolio", 'error');
  };

  const handleDeactivateDca = async (id: number) => {
    const token = localStorage.getItem("token");
    const res = await fetch(`/api/portfolio/dca/${id}/deactivate`, { method: "POST", headers: { Authorization: `Bearer ${token}` } });
    const data = await res.json();
    if (res.ok) { showToast(data.message || "DCA strategy dinonaktifkan"); fetchDcaStrategies(); }
    else showToast(data.detail || "Gagal menonaktifkan DCA", 'error');
  };

  const handlePreviewDcaLevels = async () => {
    setDcaLevelsLoading(true);
    const token = localStorage.getItem("token");
    const body = dcaMode === "signal"
      ? { signal_id: selectedSignalId, total_budget: dcaBudget, dca_count: dcaCount }
      : { ticker: manualDcaTicker, entry_low: manualEntryLow, entry_high: manualEntryHigh, max_entry: manualMaxEntry, total_budget: dcaBudget, dca_count: dcaCount };
    try {
      const res = await fetch("/api/portfolio/dca/preview", { method: "POST", headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` }, body: JSON.stringify(body) });
      const data = await res.json();
      if (data.levels) setPreviewDcaLevels(data.levels);
      else showToast(data.detail || "Gagal generate preview", 'error');
    } finally { setDcaLevelsLoading(false); }
  };

  const handleCreateDca = async (e: React.FormEvent) => {
    e.preventDefault();
    const token = localStorage.getItem("token");
    const body = dcaMode === "signal"
      ? { signal_id: selectedSignalId, total_budget: dcaBudget, dca_count: dcaCount }
      : { ticker: manualDcaTicker, entry_low: manualEntryLow, entry_high: manualEntryHigh, max_entry: manualMaxEntry, total_budget: dcaBudget, dca_count: dcaCount };
    const res = await fetch("/api/portfolio/dca", { method: "POST", headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` }, body: JSON.stringify(body) });
    const data = await res.json();
    if (res.ok) { showToast(data.message || "DCA Strategy berhasil dibuat"); fetchDcaStrategies(); setPreviewDcaLevels([]); }
    else showToast(data.detail || "Gagal membuat DCA Strategy", 'error');
  };

  const handleAiDcaRecommend = async () => {
    if (!manualDcaTicker.trim()) { showToast("Masukkan ticker terlebih dahulu", 'error'); return; }
    const token = localStorage.getItem("token");
    const res = await fetch("/api/portfolio/dca/ai-recommend", { method: "POST", headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` }, body: JSON.stringify({ ticker: manualDcaTicker.toUpperCase() }) });
    const data = await res.json();
    if (res.ok) {
      setManualEntryLow(data.entry_low); setManualEntryHigh(data.entry_high); setManualMaxEntry(data.max_entry);
      showToast(`AI Entry Level untuk ${manualDcaTicker.toUpperCase()} berhasil diisi!`);
    } else showToast(data.detail || "Gagal mendapatkan rekomendasi AI", 'error');
  };

  const handleCheckTiming = async () => {
    if (!timingTicker) { showToast("Pilih saham terlebih dahulu", 'error'); return; }
    setTimingLoading(true);
    const token = localStorage.getItem("token");
    try {
      const res = await fetch("/api/portfolio/dca/timing", { method: "POST", headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` }, body: JSON.stringify({ ticker: timingTicker }) });
      const data = await res.json();
      if (res.ok) setTimingResult(data);
      else showToast(data.detail || "Gagal cek timing DCA", 'error');
    } finally { setTimingLoading(false); }
  };

  const handleRunAiAnalysis = async () => {
    setAiAnalysisLoading(true);
    const token = localStorage.getItem("token");
    try {
      const res = await fetch("/api/portfolio/ai-analysis", { method: "POST", headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` }, body: JSON.stringify({ monthly_budget: aiMonthlyBudget }) });
      const data = await res.json();
      if (res.ok) setAiAnalysisResult(data);
      else showToast(data.detail || "Gagal menjalankan AI Analysis", 'error');
    } catch { showToast("Kesalahan jaringan", 'error'); }
    finally { setAiAnalysisLoading(false); }
  };

  const getMonthlyFlow = () => {
    const monthly: Record<string, number> = {};
    portfolioTxns.forEach(t => {
      const month = t.transaction_date?.substring(0, 7);
      if (!month) return;
      if (!monthly[month]) monthly[month] = 0;
      monthly[month] += t.transaction_type === 'SELL' ? t.amount : -t.amount;
    });
    return Object.entries(monthly).map(([month, net_flow]) => ({ month, net_flow })).sort((a, b) => a.month.localeCompare(b.month));
  };

  const getTickerStats = () => {
    const stats: Record<string, { ticker: string; amount: number; lots: number; count: number }> = {};
    portfolioTxns.forEach(t => {
      if (!stats[t.ticker]) stats[t.ticker] = { ticker: t.ticker, amount: 0, lots: 0, count: 0 };
      stats[t.ticker].amount += t.amount;
      stats[t.ticker].lots += t.lots;
      stats[t.ticker].count++;
    });
    return Object.values(stats).sort((a, b) => b.amount - a.amount);
  };

  return (
    <div className="space-y-8 animate-fade-in">
      <div>
        <h2 className="text-3xl font-bold text-text mb-2">💼 Portfolio <span className="text-accent">Management</span></h2>
        <p className="text-secondary">Manajemen holdings aktif, strategi Dollar Cost Averaging (DCA), riwayat transaksi, dan analisis portofolio bertenaga AI.</p>
      </div>

      {/* Sub-Tabs Nav */}
      <div className="flex bg-card backdrop-blur-md p-1.5 rounded-2xl border border-border overflow-x-auto max-w-max">
        {PORTFOLIO_TABS.map((tab) => (
          <button key={tab.id} onClick={() => setPortfolioTab(tab.id)}
            className={`px-4 py-2.5 rounded-xl text-sm font-semibold transition whitespace-nowrap ${portfolioTab === tab.id ? "bg-accent text-text shadow-lg shadow-accent/20" : "text-secondary hover:text-text hover:bg-white/5"}`}>
            {tab.label}
          </button>
        ))}
      </div>

      {/* SUB-TAB: HOLDINGS */}
      {portfolioTab === "holdings" && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {[
              { label: "Total Invested", value: `Rp ${(portfolioSummary.total_invested || 0).toLocaleString("id-ID")}` },
              { label: "Current Value", value: `Rp ${(portfolioSummary.total_current_value || 0).toLocaleString("id-ID")}`, sub: portfolioSummary.total_pnl !== 0 ? `${portfolioSummary.total_pnl > 0 ? "▲ +" : "▼ "}Rp ${Math.abs(portfolioSummary.total_pnl || 0).toLocaleString("id-ID")}` : undefined, subColor: portfolioSummary.total_pnl > 0 ? "text-profit" : "text-loss" },
              { label: "Total P&L", value: `${portfolioSummary.total_pnl_pct > 0 ? "+" : ""}${(portfolioSummary.total_pnl_pct || 0).toFixed(2)}%`, valueColor: portfolioSummary.total_pnl_pct > 0 ? "text-profit" : portfolioSummary.total_pnl_pct < 0 ? "text-loss" : "text-text" },
              { label: "Best Performer", value: portfolioSummary.best_performer || "N/A", sub: portfolioSummary.best_performer ? `+${(portfolioSummary.best_pnl_pct || 0).toFixed(2)}%` : undefined, subColor: "text-profit" },
            ].map((card, i) => (
              <div key={i} className="bg-card border border-border rounded-2xl p-5">
                <p className="text-xs text-secondary font-bold uppercase tracking-wider mb-1">{card.label}</p>
                <p className={`text-2xl font-black font-mono ${card.valueColor || "text-text"}`}>{card.value}</p>
                {card.sub && <p className={`text-xs font-mono font-bold mt-1 ${card.subColor}`}>{card.sub}</p>}
              </div>
            ))}
          </div>

          <div className="bg-card backdrop-blur-md border border-border rounded-3xl p-6">
            <div className="flex items-center justify-between gap-4 flex-wrap mb-4">
              <h3 className="text-lg font-bold text-text">📋 Holdings</h3>
              <div className="bg-accent/20 border border-accent/30 rounded-lg px-3 py-1.5 flex items-center gap-2 text-xs font-semibold text-accent whitespace-nowrap">
                <span className="inline-block w-2 h-2 bg-accent rounded-full animate-pulse"></span>
                📡 Realtime Prices
              </div>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-sm text-left text-secondary">
                <thead className="text-xs text-secondary uppercase bg-white/5 border-b border-border">
                  <tr>
                    <th className="px-4 py-4 rounded-tl-lg">Ticker</th><th className="px-4 py-4 text-right">Lot</th><th className="px-4 py-4 text-right">Avg Cost</th><th className="px-4 py-4 text-right">Current</th><th className="px-4 py-4 text-right">Value</th><th className="px-4 py-4 text-right">P&L (Rp)</th><th className="px-4 py-4 text-right">P&L (%)</th><th className="px-4 py-4 text-center rounded-tr-lg">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {portfolioHoldings.map((h, i) => {
                    const totalInvested = h.avg_cost * h.shares;
                    const pnlValue = h.value - totalInvested;
                    return (
                      <tr key={i} className="border-b border-border hover:bg-white/5 transition">
                        <td className="px-4 py-4 font-bold text-text text-base">{h.ticker}</td>
                        <td className="px-4 py-4 text-right font-mono">{(h.shares / 100).toFixed(0)}</td>
                        <td className="px-4 py-4 text-right font-mono">Rp {h.avg_cost.toLocaleString("id-ID")}</td>
                        <td className="px-4 py-4 text-right font-mono">Rp {h.current_price.toLocaleString("id-ID")}</td>
                        <td className="px-4 py-4 text-right font-mono">Rp {h.value.toLocaleString("id-ID")}</td>
                        <td className={`px-4 py-4 text-right font-mono font-bold ${pnlValue > 0 ? "text-profit" : pnlValue < 0 ? "text-loss" : "text-secondary"}`}>{pnlValue > 0 ? "+" : ""}{pnlValue.toLocaleString("id-ID")}</td>
                        <td className={`px-4 py-4 text-right font-mono font-bold ${h.pnl_pct > 0 ? "text-profit" : h.pnl_pct < 0 ? "text-loss" : "text-secondary"}`}>{h.pnl_pct > 0 ? "+" : ""}{h.pnl_pct.toFixed(2)}%</td>
                        <td className="px-4 py-4 text-center"><span className="px-2.5 py-1 rounded bg-accent/10 text-accent border border-accent/20 text-xs font-semibold uppercase">Active</span></td>
                      </tr>
                    );
                  })}
                  {portfolioHoldings.length === 0 && <tr><td colSpan={8} className="px-4 py-12 text-center text-secondary">Belum ada holdings aktif. Tambahkan holdings pertama di bawah.</td></tr>}
                </tbody>
              </table>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="bg-card backdrop-blur-md border border-border rounded-3xl p-6">
              <h3 className="text-lg font-bold text-text mb-4">➕ Add New Holding</h3>
              <form onSubmit={handleAddHolding} className="space-y-4">
                <div><label className="block text-xs font-bold uppercase tracking-wider text-secondary mb-2">Ticker</label><input type="text" className="w-full bg-background border border-border rounded-xl px-4 py-3 text-text font-medium focus:outline-none focus:border-accent" placeholder="TLKM" value={newHoldingTicker} onChange={(e) => setNewHoldingTicker(e.target.value)} /></div>
                <div className="grid grid-cols-2 gap-4">
                  <div><label className="block text-xs font-bold uppercase tracking-wider text-secondary mb-2">Lot</label><input type="number" className="w-full bg-background border border-border rounded-xl px-4 py-3 text-text font-medium focus:outline-none focus:border-accent" value={newHoldingLots} onChange={(e) => setNewHoldingLots(Number(e.target.value))} /></div>
                  <div><label className="block text-xs font-bold uppercase tracking-wider text-secondary mb-2">Avg Cost (Rp/share)</label><input type="number" className="w-full bg-background border border-border rounded-xl px-4 py-3 text-text font-medium focus:outline-none focus:border-accent" value={newHoldingAvg} onChange={(e) => setNewHoldingAvg(Number(e.target.value))} /></div>
                </div>
                <div><label className="block text-xs font-bold uppercase tracking-wider text-secondary mb-2">Notes</label><input type="text" className="w-full bg-background border border-border rounded-xl px-4 py-3 text-text font-medium focus:outline-none focus:border-accent" placeholder="Catatan tambahan..." value={newHoldingNotes} onChange={(e) => setNewHoldingNotes(e.target.value)} /></div>
                <button type="submit" className="w-full bg-accent text-text font-bold py-3 px-4 rounded-xl transition hover:opacity-90 shadow-lg shadow-accent/20">Add Holding</button>
              </form>
            </div>

            <div className="bg-card backdrop-blur-md border border-border rounded-3xl p-6">
              <h3 className="text-lg font-bold text-text mb-4">💵 Record Buy / Sell</h3>
              <form onSubmit={handleRecordTransaction} className="space-y-4">
                <div>
                  <label className="block text-xs font-bold uppercase tracking-wider text-secondary mb-2">Type</label>
                  <div className="flex bg-background p-1 rounded-xl border border-border max-w-max">
                    <button type="button" onClick={() => setRecordTxnType("BUY")} className={`px-4 py-2 rounded-lg text-xs font-bold transition ${recordTxnType === "BUY" ? "bg-[#22C55E] text-text" : "text-secondary hover:text-text"}`}>BUY</button>
                    <button type="button" onClick={() => setRecordTxnType("SELL")} className={`px-4 py-2 rounded-lg text-xs font-bold transition ${recordTxnType === "SELL" ? "bg-[#EF4444] text-text" : "text-secondary hover:text-text"}`}>SELL</button>
                  </div>
                </div>
                <div><label className="block text-xs font-bold uppercase tracking-wider text-secondary mb-2">Ticker</label><select className="w-full bg-background border border-border rounded-xl px-4 py-3 text-text font-medium focus:outline-none focus:border-accent" value={recordTxnTicker} onChange={(e) => setRecordTxnTicker(e.target.value)}><option value="">-- Pilih Saham --</option>{portfolioHoldings.map(h => <option key={h.ticker} value={h.ticker}>{h.ticker}</option>)}</select></div>
                <div className="grid grid-cols-2 gap-4">
                  <div><label className="block text-xs font-bold uppercase tracking-wider text-secondary mb-2">Lot</label><input type="number" className="w-full bg-background border border-border rounded-xl px-4 py-3 text-text font-medium focus:outline-none focus:border-accent" value={recordTxnLots} onChange={(e) => setRecordTxnLots(Number(e.target.value))} /></div>
                  <div><label className="block text-xs font-bold uppercase tracking-wider text-secondary mb-2">Price (Rp/share)</label><input type="number" className="w-full bg-background border border-border rounded-xl px-4 py-3 text-text font-medium focus:outline-none focus:border-accent" value={recordTxnPrice} onChange={(e) => setRecordTxnPrice(Number(e.target.value))} /></div>
                </div>
                <div><label className="block text-xs font-bold uppercase tracking-wider text-secondary mb-2">Notes</label><input type="text" className="w-full bg-background border border-border rounded-xl px-4 py-3 text-text font-medium focus:outline-none focus:border-accent" placeholder="Catatan..." value={recordTxnNotes} onChange={(e) => setRecordTxnNotes(e.target.value)} /></div>
                {recordTxnType === "BUY" && buyPreview && (
                  <div className="bg-profit/10 border border-profit/20 text-emerald-300 p-4 rounded-xl text-xs font-mono space-y-1">
                    <p className="font-bold text-text uppercase text-[10px] tracking-wider mb-1">Preview New Avg Cost</p>
                    <p>Avg Cost Saat Ini: <span className="text-text font-bold">Rp {buyPreview.current_avg?.toLocaleString("id-ID")}</span></p>
                    <p>Avg Cost Baru: <span className="text-text font-bold">Rp {buyPreview.new_avg_cost?.toLocaleString("id-ID")}</span></p>
                    <p>Total Lot Setelah Trx: <span className="text-text font-bold">{buyPreview.total_lots_after} Lot</span></p>
                  </div>
                )}
                <button type="submit" className={`w-full text-text font-bold py-3 px-4 rounded-xl transition hover:opacity-90 shadow-lg ${recordTxnType === "BUY" ? "bg-emerald-600 shadow-emerald-600/20" : "bg-loss shadow-loss/20"}`}>Record {recordTxnType}</button>
              </form>
            </div>
          </div>

          <div className="bg-[#EF4444]/5 border border-[#EF4444]/10 rounded-3xl p-6 mt-8">
            <h4 className="text-lg font-bold text-loss mb-2">⚠️ Danger Zone: Reset Portfolio</h4>
            <p className="text-sm text-secondary mb-4">Tindakan ini akan menghapus semua riwayat transaksi, DCA, dan data kepemilikan saham di portofolio secara permanen!</p>
            <button onClick={handleResetHoldings} className="bg-[#EF4444] hover:bg-red-700 text-text font-bold py-2.5 px-6 rounded-xl text-sm transition">🚨 Reset All Data Holding</button>
          </div>
        </div>
      )}

      {/* SUB-TAB: DCA MANAGER */}
      {portfolioTab === "dca" && (
        <div className="space-y-8">
          <div className="bg-card backdrop-blur-md border border-border rounded-3xl p-6">
            <h3 className="text-lg font-bold text-text mb-4">📋 Active DCA Strategies</h3>
            <div className="overflow-x-auto">
              <table className="w-full text-sm text-left text-secondary">
                <thead className="text-xs text-secondary uppercase bg-white/5 border-b border-border">
                  <tr>
                    <th className="px-4 py-4 rounded-tl-lg">Ticker</th><th className="px-4 py-4 text-right">Budget</th><th className="px-4 py-4 text-right">Used</th><th className="px-4 py-4 text-right">Remaining</th><th className="px-4 py-4">Progress</th><th className="px-4 py-4 text-center">Levels</th><th className="px-4 py-4 text-right">Next Buy</th><th className="px-4 py-4 text-center">Status</th><th className="px-4 py-4 text-center rounded-tr-lg">Action</th>
                  </tr>
                </thead>
                <tbody>
                  {dcaStrategies.map((strat, i) => {
                    const usedPct = (strat.used_budget / strat.total_budget) * 100;
                    return (
                      <tr key={i} className="border-b border-border hover:bg-white/5 transition">
                        <td className="px-4 py-4 font-bold text-text">{strat.ticker}</td>
                        <td className="px-4 py-4 text-right font-mono">Rp {strat.total_budget.toLocaleString("id-ID")}</td>
                        <td className="px-4 py-4 text-right font-mono">Rp {strat.used_budget.toLocaleString("id-ID")}</td>
                        <td className="px-4 py-4 text-right font-mono">Rp {strat.remaining_budget.toLocaleString("id-ID")}</td>
                        <td className="px-4 py-4 min-w-[120px]"><div className="flex items-center gap-2"><div className="h-2 w-20 bg-slate-800 rounded-full overflow-hidden"><div className="h-full bg-accent rounded-full" style={{ width: `${Math.min(usedPct, 100)}%` }}></div></div><span className="text-xs font-mono">{usedPct.toFixed(0)}%</span></div></td>
                        <td className="px-4 py-4 text-center font-mono">{strat.dca_count}</td>
                        <td className="px-4 py-4 text-right font-mono text-accent">{strat.next_buy_price ? `Rp ${strat.next_buy_price.toLocaleString("id-ID")}` : "-"}</td>
                        <td className="px-4 py-4 text-center"><span className="px-2 py-0.5 rounded bg-profit/10 text-profit border border-profit/20 text-xs font-semibold">{strat.status}</span></td>
                        <td className="px-4 py-4 text-center"><button onClick={() => handleDeactivateDca(strat.id)} className="text-loss hover:text-red-300 text-xs font-bold uppercase transition">Deactivate</button></td>
                      </tr>
                    );
                  })}
                  {dcaStrategies.length === 0 && <tr><td colSpan={9} className="px-4 py-10 text-center text-secondary">Belum ada DCA strategy aktif.</td></tr>}
                </tbody>
              </table>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="bg-card backdrop-blur-md border border-border rounded-3xl p-6">
              <h3 className="text-lg font-bold text-text mb-4">➕ Create New DCA Strategy</h3>
              <div className="flex bg-background p-1 rounded-xl border border-border max-w-max mb-6">
                <button type="button" onClick={() => { setDcaMode("signal"); setPreviewDcaLevels([]); }} className={`px-4 py-2 rounded-lg text-xs font-bold transition ${dcaMode === "signal" ? "bg-accent text-text" : "text-secondary hover:text-text"}`}>From TOP PICKS Signal</button>
                <button type="button" onClick={() => { setDcaMode("manual"); setPreviewDcaLevels([]); }} className={`px-4 py-2 rounded-lg text-xs font-bold transition ${dcaMode === "manual" ? "bg-accent text-text" : "text-secondary hover:text-text"}`}>Manual Input</button>
              </div>
              <form onSubmit={handleCreateDca} className="space-y-4">
                {dcaMode === "signal" ? (
                  <div>
                    <label className="block text-xs font-bold uppercase tracking-wider text-secondary mb-2">Pilih Sinyal Top Picks</label>
                    {picks.length > 0 ? (
                      <select className="w-full bg-background border border-border rounded-xl px-4 py-3 text-text font-medium focus:outline-none focus:border-accent" value={selectedSignalId || ""} onChange={(e) => { setSelectedSignalId(Number(e.target.value)); setPreviewDcaLevels([]); }}>
                        <option value="">-- Pilih Rekomendasi Sinyal --</option>
                        {picks.map(p => <option key={p.id} value={p.id}>{p.ticker} (Entry: {p.entry_low} - {p.max_entry} | Conviction: {p.conviction})</option>)}
                      </select>
                    ) : <div className="text-xs text-warning bg-warning/10 border border-warning/20 p-3 rounded-xl">⚠️ Belum ada TOP PICKS signal. Run analysis dulu di tab Top Picks.</div>}
                  </div>
                ) : (
                  <div className="space-y-4">
                    <div>
                      <label className="block text-xs font-bold uppercase tracking-wider text-secondary mb-2">Ticker</label>
                      <div className="flex gap-2">
                        <input type="text" className="flex-1 bg-background border border-border rounded-xl px-4 py-3 text-text font-medium focus:outline-none focus:border-accent" placeholder="TLKM" value={manualDcaTicker} onChange={(e) => setManualDcaTicker(e.target.value)} />
                        <button type="button" onClick={handleAiDcaRecommend} className="bg-slate-800 border border-border hover:bg-slate-700 text-text font-bold px-3 rounded-xl text-xs transition">🤖 AI Entry</button>
                      </div>
                    </div>
                    <div className="grid grid-cols-3 gap-2">
                      <div><label className="block text-[10px] font-bold uppercase tracking-wider text-secondary mb-1">Entry Low</label><input type="number" className="w-full bg-background border border-border rounded-xl px-3 py-2.5 text-xs text-text font-mono focus:outline-none focus:border-accent" value={manualEntryLow} onChange={(e) => setManualEntryLow(Number(e.target.value))} /></div>
                      <div><label className="block text-[10px] font-bold uppercase tracking-wider text-secondary mb-1">Entry High</label><input type="number" className="w-full bg-background border border-border rounded-xl px-3 py-2.5 text-xs text-text font-mono focus:outline-none focus:border-accent" value={manualEntryHigh} onChange={(e) => setManualEntryHigh(Number(e.target.value))} /></div>
                      <div><label className="block text-[10px] font-bold uppercase tracking-wider text-secondary mb-1">Max Entry</label><input type="number" className="w-full bg-background border border-border rounded-xl px-3 py-2.5 text-xs text-text font-mono focus:outline-none focus:border-accent" value={manualMaxEntry} onChange={(e) => setManualMaxEntry(Number(e.target.value))} /></div>
                    </div>
                  </div>
                )}
                <div className="grid grid-cols-2 gap-4">
                  <div><label className="block text-xs font-bold uppercase tracking-wider text-secondary mb-2">Total Budget (Rp)</label><input type="number" className="w-full bg-background border border-border rounded-xl px-4 py-3 text-text font-medium focus:outline-none focus:border-accent" value={dcaBudget} onChange={(e) => setDcaBudget(Number(e.target.value))} /></div>
                  <div><label className="block text-xs font-bold uppercase tracking-wider text-secondary mb-2">DCA Levels (2 - 5)</label><input type="number" min={2} max={5} className="w-full bg-background border border-border rounded-xl px-4 py-3 text-text font-medium focus:outline-none focus:border-accent" value={dcaCount} onChange={(e) => setDcaCount(Number(e.target.value))} /></div>
                </div>
                <div className="flex gap-3">
                  <button type="button" onClick={handlePreviewDcaLevels} className="flex-1 bg-slate-800 hover:bg-slate-700 text-text font-bold py-3 rounded-xl text-sm transition">{dcaLevelsLoading ? "Calculating..." : "Preview DCA Levels"}</button>
                  <button type="submit" className="flex-1 bg-accent text-text font-bold py-3 rounded-xl text-sm transition hover:opacity-90 shadow-lg shadow-accent/20">✅ Activate DCA</button>
                </div>
              </form>
              {previewDcaLevels.length > 0 && (
                <div className="mt-6 bg-card border border-border rounded-2xl p-4 space-y-3">
                  <h4 className="text-xs font-bold uppercase tracking-wider text-secondary">Preview Levels:</h4>
                  <div className="overflow-x-auto">
                    <table className="w-full text-xs text-left text-secondary">
                      <thead><tr className="border-b border-border text-secondary"><th className="pb-2">Level</th><th className="pb-2 text-right">Price</th><th className="pb-2 text-right">Budget</th><th className="pb-2 text-right">Actual</th><th className="pb-2 text-right">Lot</th></tr></thead>
                      <tbody>{previewDcaLevels.map((lvl, idx) => (<tr key={idx} className="border-b border-white/[0.02]"><td className="py-2 font-bold">{lvl.level}</td><td className="py-2 text-right font-mono">Rp {lvl.price.toLocaleString("id-ID")}</td><td className="py-2 text-right font-mono">Rp {lvl.amount_budget.toLocaleString("id-ID")}</td><td className="py-2 text-right font-mono">Rp {lvl.actual_amount.toLocaleString("id-ID")}</td><td className="py-2 text-right font-mono">{lvl.lots} Lot</td></tr>))}</tbody>
                    </table>
                  </div>
                </div>
              )}
            </div>

            <div className="bg-card backdrop-blur-md border border-border rounded-3xl p-6">
              <h3 className="text-lg font-bold text-text mb-4">🕐 DCA Timing Recommendation</h3>
              <div className="space-y-4">
                <div><label className="block text-xs font-bold uppercase tracking-wider text-secondary mb-2">Select Ticker</label><select className="w-full bg-background border border-border rounded-xl px-4 py-3 text-text font-medium focus:outline-none focus:border-[#7C3AED]" value={timingTicker} onChange={(e) => setTimingTicker(e.target.value)}><option value="">-- Pilih Saham Anda --</option>{portfolioHoldings.map(h => <option key={h.ticker} value={h.ticker}>{h.ticker}</option>)}</select></div>
                <button onClick={handleCheckTiming} disabled={timingLoading} className="w-full bg-slate-800 hover:bg-slate-700 text-text font-bold py-3 rounded-xl text-sm transition">{timingLoading ? "Checking..." : "Check Timing"}</button>
                {timingResult && (
                  <div className="bg-background border border-border rounded-2xl p-5 space-y-4">
                    <div className="flex items-center justify-between">
                      <span className="text-xs text-secondary font-bold uppercase">Status</span>
                      <span className={`px-3 py-1 rounded-full text-xs font-bold ${timingResult.status === "IDEAL" ? "bg-[#22C55E]/10 text-[#22C55E] border border-[#22C55E]/20" : timingResult.status === "ACCEPTABLE" ? "bg-[#F59E0B]/10 text-[#F59E0B] border border-[#F59E0B]/20" : timingResult.status === "CAUTION" ? "bg-orange-500/10 text-orange-400 border border-orange-500/20" : "bg-loss/10 text-loss border border-loss/20"}`}>
                        {timingResult.status === "IDEAL" ? "🟢 IDEAL" : timingResult.status === "ACCEPTABLE" ? "🟡 ACCEPTABLE" : timingResult.status === "CAUTION" ? "🟠 CAUTION" : "🔴 AVOID"}
                      </span>
                    </div>
                    <div className="grid grid-cols-3 gap-2 text-center border-t border-b border-border py-4">
                      <div><p className="text-[10px] text-secondary font-bold uppercase">Current Price</p><p className="font-mono font-bold text-text mt-1">Rp {timingResult.current_price?.toLocaleString("id-ID")}</p></div>
                      <div><p className="text-[10px] text-secondary font-bold uppercase">True Cost 1M</p><p className="font-mono font-bold text-text mt-1">Rp {timingResult.true_cost_1m?.toLocaleString("id-ID")}</p></div>
                      <div><p className="text-[10px] text-secondary font-bold uppercase">Distance</p><p className={`font-mono font-bold mt-1 ${timingResult.distance_pct > 0 ? "text-loss" : "text-[#22C55E]"}`}>{timingResult.distance_pct > 0 ? "+" : ""}{timingResult.distance_pct?.toFixed(2)}%</p></div>
                    </div>
                    <div className="text-xs text-secondary leading-relaxed bg-card border border-border p-3 rounded-xl">{timingResult.reason}</div>
                    {timingResult.recommended_buy && (
                      <div className="text-xs font-bold text-[#22C55E] bg-[#22C55E]/10 border border-[#22C55E]/20 p-3.5 rounded-xl flex items-center justify-between">
                        <span>💡 Recommended Buy Price:</span><span className="font-mono text-text text-sm">Rp {timingResult.recommended_buy.toLocaleString("id-ID")}</span>
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* SUB-TAB: TRANSACTION HISTORY */}
      {portfolioTab === "history" && (
        <div className="bg-card backdrop-blur-md border border-border rounded-3xl p-6 space-y-6">
          <div className="flex justify-between items-center flex-wrap gap-4 border-b border-border pb-4">
            <h3 className="text-lg font-bold text-text">📜 Transaction History</h3>
            {portfolioTxns.length > 0 && (
              <button onClick={() => { const csv = "data:text/csv;charset=utf-8,Date,Ticker,Type,Lots,Price,Amount,Notes\n" + portfolioTxns.map(t => `${t.transaction_date},${t.ticker},${t.transaction_type},${t.lots},${t.price},${t.amount},"${t.notes || ""}"`).join("\n"); const link = document.createElement("a"); link.href = encodeURI(csv); link.download = `transactions_${new Date().toISOString()}.csv`; document.body.appendChild(link); link.click(); document.body.removeChild(link); }}
                className="bg-accent hover:bg-indigo-600 text-text font-bold py-2 px-4 rounded-xl text-xs transition">📥 Export to CSV</button>
            )}
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div><label className="block text-xs font-bold uppercase tracking-wider text-secondary mb-2">Filter Ticker</label><select className="w-full bg-background border border-border rounded-xl px-4 py-3 text-text font-medium focus:outline-none" value={txnFilterTicker} onChange={(e) => setTxnFilterTicker(e.target.value)}><option value="ALL">ALL</option>{Array.from(new Set(portfolioTxns.map(t => t.ticker))).map(t => <option key={t} value={t}>{t}</option>)}</select></div>
            <div><label className="block text-xs font-bold uppercase tracking-wider text-secondary mb-2">Filter Type</label><select className="w-full bg-background border border-border rounded-xl px-4 py-3 text-text font-medium focus:outline-none" value={txnFilterType} onChange={(e) => setTxnFilterType(e.target.value)}><option value="ALL">ALL</option><option value="BUY">BUY</option><option value="SELL">SELL</option></select></div>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm text-left text-secondary">
              <thead className="text-xs text-secondary uppercase bg-white/5 border-b border-border"><tr><th className="px-4 py-4">Date</th><th className="px-4 py-4">Ticker</th><th className="px-4 py-4">Type</th><th className="px-4 py-4 text-right">Lot</th><th className="px-4 py-4 text-right">Price</th><th className="px-4 py-4 text-right">Amount</th><th className="px-4 py-4">Notes</th></tr></thead>
              <tbody>
                {portfolioTxns.filter(t => txnFilterTicker === "ALL" || t.ticker === txnFilterTicker).filter(t => txnFilterType === "ALL" || t.transaction_type === txnFilterType).map((t, idx) => (
                  <tr key={idx} className="border-b border-border hover:bg-white/5 transition">
                    <td className="px-4 py-4">{t.transaction_date}</td>
                    <td className="px-4 py-4 font-bold text-text">{t.ticker}</td>
                    <td className="px-4 py-4"><span className={`px-2.5 py-1 rounded text-xs font-bold border ${t.transaction_type === "BUY" ? "bg-[#22C55E]/10 text-[#22C55E] border-[#22C55E]/20" : "bg-loss/10 text-loss border-loss/20"}`}>{t.transaction_type}</span></td>
                    <td className="px-4 py-4 text-right font-mono">{t.lots}</td>
                    <td className="px-4 py-4 text-right font-mono">Rp {t.price.toLocaleString("id-ID")}</td>
                    <td className="px-4 py-4 text-right font-mono">Rp {t.amount.toLocaleString("id-ID")}</td>
                    <td className="px-4 py-4 text-secondary italic text-xs max-w-xs truncate">{t.notes}</td>
                  </tr>
                ))}
                {portfolioTxns.length === 0 && <tr><td colSpan={7} className="px-4 py-10 text-center text-secondary">Belum ada riwayat transaksi.</td></tr>}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* SUB-TAB: PERFORMANCE REPORT */}
      {portfolioTab === "performance" && (
        <div className="space-y-6">
          <div className="bg-card backdrop-blur-md border border-border rounded-3xl p-6">
            <h3 className="text-lg font-bold text-text mb-2">📊 Monthly Transaction Flow</h3>
            <p className="text-xs text-secondary mb-6">Distribusi pergerakan dana bersih (Total SELL - Total BUY) per bulan.</p>
            {(() => {
              const flows = getMonthlyFlow();
              if (flows.length === 0) return <div className="text-center py-10 text-secondary text-sm">Belum ada transaksi untuk memetakan bulanan.</div>;
              const maxAbs = Math.max(...flows.map(f => Math.abs(f.net_flow))) || 1;
              return (
                <div className="space-y-4">
                  {flows.map((flow, idx) => {
                    const ratio = Math.min(Math.abs(flow.net_flow) / maxAbs, 1);
                    const isPos = flow.net_flow >= 0;
                    return (
                      <div key={idx} className="flex items-center gap-4 text-xs font-mono">
                        <span className="w-16 font-bold text-secondary">{flow.month}</span>
                        <div className="flex-1 h-6 bg-slate-900 rounded-lg relative overflow-hidden flex items-center px-2">
                          <div className={`h-full absolute top-0 transition-all ${isPos ? "bg-[#22C55E]/20 border-l border-[#22C55E]" : "bg-[#EF4444]/20 border-r border-[#EF4444]"}`} style={{ width: `${ratio * 50}%`, left: isPos ? "50%" : "auto", right: isPos ? "auto" : "50%" }}></div>
                          <span className={`relative z-10 font-bold ml-auto font-mono ${isPos ? "text-[#22C55E]" : "text-loss"}`}>{isPos ? "+" : "-"}Rp {Math.abs(flow.net_flow).toLocaleString("id-ID")}</span>
                        </div>
                      </div>
                    );
                  })}
                </div>
              );
            })()}
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="bg-card border border-border rounded-3xl p-6">
              <h3 className="text-lg font-bold text-text mb-4">📋 Per-Ticker Transaction Summary</h3>
              <table className="w-full text-sm text-left text-secondary">
                <thead><tr className="border-b border-border text-xs text-secondary uppercase"><th className="pb-3">Ticker</th><th className="pb-3 text-right">Total Amount</th><th className="pb-3 text-right">Total Lot</th><th className="pb-3 text-center">Txns</th></tr></thead>
                <tbody>{getTickerStats().map((stat, idx) => (<tr key={idx} className="border-b border-border"><td className="py-3 font-bold text-text">{stat.ticker}</td><td className="py-3 text-right font-mono">Rp {stat.amount.toLocaleString("id-ID")}</td><td className="py-3 text-right font-mono">{stat.lots} Lot</td><td className="py-3 text-center font-mono">{stat.count}</td></tr>))}{getTickerStats().length === 0 && <tr><td colSpan={4} className="py-10 text-center text-secondary text-xs">Belum ada transaksi.</td></tr>}</tbody>
              </table>
            </div>

            <div className="bg-card border border-border rounded-3xl p-6">
              <h3 className="text-lg font-bold text-text mb-4">💼 Current Holdings P&L</h3>
              <table className="w-full text-sm text-left text-secondary">
                <thead><tr className="border-b border-border text-xs text-secondary uppercase"><th className="pb-3">Ticker</th><th className="pb-3 text-right">P&L (Rp)</th><th className="pb-3 text-right">P&L (%)</th></tr></thead>
                <tbody>{portfolioHoldings.map((h, idx) => { const pnlValue = h.value - (h.avg_cost * h.shares); return (<tr key={idx} className="border-b border-border"><td className="py-3 font-bold text-text">{h.ticker}</td><td className={`py-3 text-right font-mono font-bold ${pnlValue > 0 ? "text-[#22C55E]" : pnlValue < 0 ? "text-loss" : "text-secondary"}`}>{pnlValue > 0 ? "+" : ""}{pnlValue.toLocaleString("id-ID")}</td><td className={`py-3 text-right font-mono font-bold ${h.pnl_pct > 0 ? "text-[#22C55E]" : h.pnl_pct < 0 ? "text-loss" : "text-secondary"}`}>{h.pnl_pct > 0 ? "+" : ""}{h.pnl_pct.toFixed(2)}%</td></tr>); })}{portfolioHoldings.length === 0 && <tr><td colSpan={3} className="py-10 text-center text-secondary text-xs">Belum ada holdings aktif.</td></tr>}</tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* SUB-TAB: AI ANALYSIS */}
      {portfolioTab === "ai" && (
        <div className="space-y-6">
          <div className="bg-card backdrop-blur-md border border-border rounded-3xl p-6">
            <h3 className="text-lg font-bold text-text mb-2">🤖 AI Portfolio Analysis</h3>
            <p className="text-xs text-secondary mb-6">Analisis portofolio komprehensif: rebalancing target, prioritas DCA bulan ini, analisis risiko diversifikasi, serta atribusi performa.</p>
            <div className="flex flex-col sm:flex-row items-end gap-4">
              <div className="flex-1"><label className="block text-xs font-bold uppercase tracking-wider text-secondary mb-2">Monthly DCA Budget (Rp)</label><input type="number" className="w-full bg-background border border-border rounded-xl px-4 py-3 text-text font-medium focus:outline-none" value={aiMonthlyBudget} onChange={(e) => setAiMonthlyBudget(Number(e.target.value))} /></div>
              <button onClick={handleRunAiAnalysis} disabled={aiAnalysisLoading} className="bg-accent text-text font-bold py-3 px-6 rounded-xl transition hover:opacity-90 shadow-lg shadow-accent/20 disabled:opacity-50">{aiAnalysisLoading ? "🤖 AI sedang menganalisis..." : "🤖 Get AI Portfolio Analysis"}</button>
            </div>
          </div>

          {aiAnalysisLoading && (
            <div className="bg-card border border-border rounded-3xl p-12 text-center space-y-4">
              <div className="w-10 h-10 border-4 border-[#7C3AED] border-t-transparent rounded-full animate-spin mx-auto"></div>
              <p className="text-secondary font-medium text-sm">AI sedang menganalisis portfolio... (proses LLM & perdebatan bisa memakan waktu 30-60 detik)</p>
            </div>
          )}

          {!aiAnalysisLoading && aiAnalysisResult && (
            <div className="space-y-6 animate-fade-in">
              {aiAnalysisResult.generated_at && <p className="text-xs text-secondary font-mono">Generated: {aiAnalysisResult.generated_at.substring(0, 19).replace("T", " ")} WIB</p>}
              {aiAnalysisResult.summary && <div className="bg-gray-800/60 border border-gray-600/30 p-5 rounded-2xl text-gray-300 text-sm leading-relaxed"><span className="font-bold text-text block mb-1">📋 AI Summary:</span>{aiAnalysisResult.summary}</div>}
              
              <div className="bg-card border border-border rounded-3xl p-6 space-y-4">
                <h4 className="text-base font-bold text-text">⚖️ Rebalancing Recommendations</h4>
                {aiAnalysisResult.rebalancing?.needed ? (
                  <div className="text-[#F59E0B] bg-[#F59E0B]/10 border border-[#F59E0B]/20 p-3.5 rounded-xl text-xs font-semibold">⚠️ Rebalancing diperlukan agar sesuai target diversifikasi profil Anda.</div>
                ) : (
                  <div className="text-[#22C55E] bg-[#22C55E]/10 border border-[#22C55E]/20 p-3.5 rounded-xl text-xs font-semibold">✅ Portfolio saat ini sudah terdistribusi dengan seimbang.</div>
                )}
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div className="bg-background p-4 rounded-xl border border-border"><p className="text-xs font-bold text-loss uppercase tracking-wider mb-2">🔴 Overweight:</p>{aiAnalysisResult.rebalancing?.overweight?.length > 0 ? <ul className="list-disc pl-5 text-secondary space-y-1">{aiAnalysisResult.rebalancing.overweight.map((t: string) => <li key={t}>{t}</li>)}</ul> : <p className="text-secondary text-xs italic">Tidak ada</p>}</div>
                  <div className="bg-background p-4 rounded-xl border border-border"><p className="text-xs font-bold text-[#F59E0B] uppercase tracking-wider mb-2">🟡 Underweight:</p>{aiAnalysisResult.rebalancing?.underweight?.length > 0 ? <ul className="list-disc pl-5 text-secondary space-y-1">{aiAnalysisResult.rebalancing.underweight.map((t: string) => <li key={t}>{t}</li>)}</ul> : <p className="text-secondary text-xs italic">Tidak ada</p>}</div>
                </div>
              </div>

              <div className="bg-card border border-border rounded-3xl p-6 space-y-4">
                <div className="flex items-center justify-between gap-4 flex-wrap">
                  <h4 className="text-base font-bold text-text">💰 DCA Priority This Month (Budget: Rp {aiMonthlyBudget.toLocaleString("id-ID")})</h4>
                  <div className="bg-accent/20 border border-accent/30 rounded-lg px-3 py-1.5 flex items-center gap-2 text-xs font-semibold text-accent whitespace-nowrap">
                    <span className="inline-block w-2 h-2 bg-accent rounded-full animate-pulse"></span>
                    📡 Realtime Prices (Stockbit)
                  </div>
                </div>
                <p className="text-xs text-secondary">Semua harga target berbasis data realtime terbaru dari Stockbit. Rekomendasi DCA diperhitungkan dengan market condition terkini.</p>
                <div className="space-y-3">
                  {aiAnalysisResult.dca_priority?.map((p: any, idx: number) => {
                    const amount = p.allocation || p.suggested_amount;
                    const reason = p.reasoning || p.reason;
                    return (
                      <div key={idx} className="bg-background border border-border p-4 rounded-xl flex flex-col md:flex-row gap-4 justify-between items-start md:items-center">
                        <div className="flex items-center gap-3">
                          <span className="text-lg font-black text-emerald-400 font-mono">#{p.rank}</span>
                          <div>
                            <h5 className="font-bold text-text">{p.ticker}</h5>
                            <p className="text-xs text-gray-400">
                              Timing: <span className="text-yellow-400 font-mono font-bold">{p.timing_status}</span> | 
                              Conviction: <span className="text-yellow-400 font-mono font-bold">{p.conviction}</span>
                            </p>
                            {(p.target_lots || p.target_price) && (
                              <p className="text-xs text-emerald-400 mt-1 font-mono font-bold">
                                Target Beli: {p.target_lots ? `${p.target_lots} Lot` : ''} 
                                {p.target_price ? ` @ Rp ${p.target_price.toLocaleString("id-ID")}` : ''}
                              </p>
                            )}
                          </div>
                        </div>
                        <div className="text-right md:max-w-[45%]">
                          <p className="font-mono font-bold text-text">
                            Rp {amount?.toLocaleString("id-ID") || 0}
                          </p>
                          <p className="text-[11px] text-gray-400 italic mt-1 leading-tight">{reason}</p>
                        </div>
                      </div>
                    );
                  })}
                  {!aiAnalysisResult.dca_priority?.length && <p className="text-secondary text-sm">Tidak ada prioritas DCA yang disarankan.</p>}
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
