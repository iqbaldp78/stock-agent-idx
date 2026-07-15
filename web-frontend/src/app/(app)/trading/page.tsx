"use client";
import React, { useState, useEffect } from 'react';
import { useApp } from '../../context/AppContext';

const CustomEquityChart = ({ points }: { points: any[] }) => {
  if (!points || points.length === 0) {
    return (
      <div className="relative w-full h-[220px] bg-white/[0.02] border border-white/5 rounded-3xl p-6 flex items-center justify-center text-slate-500 text-sm">
        Equity curve akan muncul setelah ada trades.
      </div>
    );
  }
  const values = points.map(p => p.equity);
  const minVal = Math.min(...values) * 0.99;
  const maxVal = Math.max(...values) * 1.01;
  const range = maxVal - minVal || 1;
  const width = 500; const height = 150; const paddingX = 25; const paddingY = 15;
  const pointsCount = points.length;
  const svgPoints = points.map((p, idx) => {
    const x = paddingX + (idx / (pointsCount - 1 || 1)) * (width - 2 * paddingX);
    const y = height - paddingY - ((p.equity - minVal) / range) * (height - 2 * paddingY);
    return { x, y, data: p };
  });
  const pathD = svgPoints.reduce((acc, p, idx) => acc + `${idx === 0 ? 'M' : 'L'} ${p.x} ${p.y}`, "");
  const fillD = svgPoints.length > 0 ? `${pathD} L ${svgPoints[svgPoints.length - 1].x} ${height - paddingY} L ${svgPoints[0].x} ${height - paddingY} Z` : "";

  return (
    <div className="relative w-full h-[220px] bg-white/[0.02] border border-white/5 rounded-3xl p-6">
      <div className="flex justify-between items-center mb-4">
        <div>
          <h4 className="text-sm font-bold text-slate-400 uppercase tracking-wider">Equity Growth</h4>
          <p className="text-[10px] text-slate-500 font-medium">Virtual portfolio value progression</p>
        </div>
        <div className="flex gap-4 text-xs font-mono">
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-[#00d4aa]"></span>
            <span className="text-slate-300">Total Equity</span>
          </div>
        </div>
      </div>
      <div className="w-full h-[120px] relative">
        <svg viewBox={`0 0 ${width} ${height}`} className="w-full h-full overflow-visible" preserveAspectRatio="none">
          <defs>
            <linearGradient id="chartGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#00d4aa" stopOpacity="0.2" />
              <stop offset="100%" stopColor="#00d4aa" stopOpacity="0.00" />
            </linearGradient>
            <filter id="glow" x="-20%" y="-20%" width="140%" height="140%">
              <feDropShadow dx="0" dy="4" stdDeviation="4" floodColor="#00d4aa" floodOpacity="0.3" />
            </filter>
          </defs>
          <line x1={paddingX} y1={paddingY} x2={width - paddingX} y2={paddingY} stroke="rgba(255,255,255,0.03)" strokeDasharray="3" />
          <line x1={paddingX} y1={height / 2} x2={width - paddingX} y2={height / 2} stroke="rgba(255,255,255,0.03)" strokeDasharray="3" />
          <line x1={paddingX} y1={height - paddingY} x2={width - paddingX} y2={height - paddingY} stroke="rgba(255,255,255,0.03)" strokeDasharray="3" />
          {fillD && <path d={fillD} fill="url(#chartGradient)" />}
          {pathD && <path d={pathD} fill="none" stroke="#00d4aa" strokeWidth="2.5" filter="url(#glow)" />}
          {svgPoints.map((p, idx) => (
            <g key={idx} className="cursor-pointer">
              <circle cx={p.x} cy={p.y} r="3" fill="#030712" stroke="#00d4aa" strokeWidth="1.5" />
              <title>{`${p.data.date}: Rp ${p.data.equity.toLocaleString('id-ID')} (${p.data.event || 'Trade'})`}</title>
            </g>
          ))}
        </svg>
      </div>
    </div>
  );
};

export default function TradingPage() {
  const { picks, showToast } = useApp();
  const [tradingData, setTradingData] = useState<any>(null);
  const [equityData, setEquityData] = useState<any>(null);
  const [tradingLoading, setTradingLoading] = useState(false);
  const [tradingError, setTradingError] = useState("");
  const [topupAmount, setTopupAmount] = useState(100000000);

  // Buy form state — can be prefilled from Top Picks via sessionStorage
  const [buyTicker, setBuyTicker] = useState("MEDC");
  const [buyLot, setBuyLot] = useState(10);
  const [buyPrice, setBuyPrice] = useState(1150);
  const [buyTp, setBuyTp] = useState(0);
  const [buySl, setBuySl] = useState(0);
  const [buySignalId, setBuySignalId] = useState<number | null>(null);

  const fetchTradingData = async () => {
    setTradingLoading(true);
    setTradingError("");
    try {
      const res = await fetch("/api/trading/summary", {
        headers: { 'Authorization': `Bearer ${localStorage.getItem("token")}` }
      });
      if (!res.ok) throw new Error("Gagal mengambil data Trading Engine");
      const data = await res.json();
      setTradingData(data);
    } catch (err: any) {
      setTradingError(err.message || "Kesalahan jaringan");
    } finally {
      setTradingLoading(false);
    }
  };

  const fetchEquityData = async () => {
    try {
      const res = await fetch("/api/trading/equity-history", {
        headers: { 'Authorization': `Bearer ${localStorage.getItem("token")}` }
      });
      if (res.ok) { const data = await res.json(); setEquityData(data); }
    } catch (err) { console.error("Gagal mengambil riwayat ekuitas:", err); }
  };

  useEffect(() => {
    fetchTradingData();
    fetchEquityData();
    // Check if we have prefill data from Top Picks navigation
    const prefill = sessionStorage.getItem('tradingPrefill');
    if (prefill) {
      try {
        const p = JSON.parse(prefill);
        setBuyTicker(p.ticker || "MEDC");
        setBuyPrice(p.price || 1150);
        setBuyTp(p.tp || 0);
        setBuySl(p.sl || 0);
        setBuySignalId(p.signalId || null);
        sessionStorage.removeItem('tradingPrefill');
      } catch {}
    }
  }, []);

  const handleTopup = async (amount: number) => {
    try {
      const res = await fetch("/api/trading/topup", {
        method: "POST",
        headers: { "Content-Type": "application/json", "Authorization": `Bearer ${localStorage.getItem("token")}` },
        body: JSON.stringify({ amount })
      });
      const data = await res.json();
      if (data.status === "success") { showToast(data.message, 'success'); fetchTradingData(); fetchEquityData(); }
      else showToast(data.message || "Gagal melakukan topup", 'error');
    } catch { showToast("Kesalahan jaringan saat melakukan topup", 'error'); }
  };

  const handleResetPortfolio = async () => {
    if (!confirm("Apakah Anda yakin ingin mereset seluruh posisi dan transaksi virtual?")) return;
    try {
      const res = await fetch("/api/trading/reset", { method: "POST", headers: { "Authorization": `Bearer ${localStorage.getItem("token")}` } });
      const data = await res.json();
      showToast(data.message || "Portfolio berhasil direset", 'success');
      fetchTradingData(); fetchEquityData();
    } catch { showToast("Kesalahan jaringan saat mereset portfolio", 'error'); }
  };

  const handleBuy = async (ticker: string, lot: number, price: number, signalId: number | null, tp1: number, stopLoss: number) => {
    try {
      const res = await fetch("/api/trading/buy", {
        method: "POST",
        headers: { "Content-Type": "application/json", "Authorization": `Bearer ${localStorage.getItem("token")}` },
        body: JSON.stringify({ ticker: ticker.toUpperCase(), lot, price, signal_id: signalId, tp1: tp1 > 0 ? tp1 : null, stop_loss: stopLoss > 0 ? stopLoss : null })
      });
      const data = await res.json();
      if (data.status === "error") showToast(data.message, 'error');
      else { showToast(data.message || "Order berhasil ditempatkan", 'success'); fetchTradingData(); fetchEquityData(); }
    } catch { showToast("Kesalahan jaringan saat melakukan pembelian", 'error'); }
  };

  const handleSell = async (tradeId: number, price: number) => {
    try {
      const res = await fetch("/api/trading/sell", {
        method: "POST",
        headers: { "Content-Type": "application/json", "Authorization": `Bearer ${localStorage.getItem("token")}` },
        body: JSON.stringify({ trade_id: tradeId, price, reason: "MANUAL" })
      });
      const data = await res.json();
      if (data.status === "success") { showToast(`Berhasil menjual: ${data.message || ''}`, 'success'); fetchTradingData(); fetchEquityData(); }
      else showToast(data.message || "Gagal melakukan penjualan", 'error');
    } catch { showToast("Kesalahan jaringan saat melakukan penjualan", 'error'); }
  };

  const handleCancelPending = async (tradeId: number) => {
    try {
      const res = await fetch("/api/trading/cancel-pending", {
        method: "POST",
        headers: { "Content-Type": "application/json", "Authorization": `Bearer ${localStorage.getItem("token")}` },
        body: JSON.stringify({ trade_id: tradeId })
      });
      const data = await res.json();
      if (data.status === "success") { showToast(data.message || "Order berhasil dibatalkan", 'success'); fetchTradingData(); fetchEquityData(); }
      else showToast(data.message || "Gagal membatalkan order", 'error');
    } catch { showToast("Kesalahan jaringan saat membatalkan order", 'error'); }
  };

  const handleAutoInvestAll = async () => {
    try {
      const res = await fetch("/api/trading/auto-invest-all", {
        method: "POST",
        headers: { "Content-Type": "application/json", "Authorization": `Bearer ${localStorage.getItem("token")}` },
        body: JSON.stringify({ budget_pct: 0.15 })
      });
      const data = await res.json();
      showToast(data.message || "Auto-invest berhasil dijalankan", 'success');
      fetchTradingData(); fetchEquityData();
    } catch { showToast("Kesalahan jaringan saat auto-invest", 'error'); }
  };

  const handleAutoInvestSingle = async (signalId: number, price: number) => {
    try {
      const res = await fetch("/api/trading/auto-invest-single", {
        method: "POST",
        headers: { "Content-Type": "application/json", "Authorization": `Bearer ${localStorage.getItem("token")}` },
        body: JSON.stringify({ signal_id: signalId, budget_pct: 0.20, price })
      });
      const data = await res.json();
      showToast(data.message || "Auto-invest tunggal berhasil", 'success');
      fetchTradingData(); fetchEquityData();
    } catch { showToast("Kesalahan jaringan saat auto-invest tunggal", 'error'); }
  };

  const handleCheckTpsl = async () => {
    try {
      const res = await fetch("/api/trading/check-tpsl", { method: "POST", headers: { "Authorization": `Bearer ${localStorage.getItem("token")}` } });
      const data = await res.json();
      showToast(data.message || "Pengecekan TP/SL selesai", 'success');
      fetchTradingData(); fetchEquityData();
    } catch { showToast("Kesalahan jaringan saat mengecek TP/SL", 'error'); }
  };

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h2 className="text-3xl font-bold text-white mb-2">Trading <span className="text-indigo-400">Engine</span></h2>
          <p className="text-slate-400">Virtual Portfolio Validator — Uji strategi trading Anda dengan modal virtual secara real-time.</p>
        </div>
        <div className="flex gap-3">
          <button onClick={handleCheckTpsl} className="px-4 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white font-bold rounded-xl text-sm transition flex items-center gap-2 shadow-lg shadow-indigo-600/20">
            🔍 Cek TP/SL Sekarang
          </button>
          <button onClick={handleResetPortfolio} className="px-4 py-2.5 bg-red-500/10 hover:bg-red-500/20 border border-red-500/20 text-red-400 font-semibold rounded-xl text-sm transition">
            🔄 Reset Portfolio
          </button>
        </div>
      </div>

      {tradingLoading && !tradingData && (
        <div className="flex flex-col items-center justify-center py-20 gap-4">
          <span className="w-10 h-10 border-4 border-indigo-500 border-t-transparent rounded-full animate-spin"></span>
          <span className="text-slate-400 font-medium">Memuat data portfolio virtual...</span>
        </div>
      )}

      {tradingError && <div className="p-4 bg-red-500/10 border border-red-500/20 text-red-300 rounded-2xl text-center">⚠️ {tradingError}</div>}

      {!tradingLoading && tradingData && (() => {
        if (tradingData.status === 'not_setup') {
          return (
            <div className="flex flex-col items-center justify-center py-24 gap-6 text-center animate-fade-in">
              <div className="w-20 h-20 bg-indigo-500/10 rounded-full flex items-center justify-center mb-2">
                <span className="text-4xl">🚀</span>
              </div>
              <h3 className="text-3xl font-bold text-white">Trading Engine Belum Aktif</h3>
              <p className="text-slate-400 max-w-md text-sm leading-relaxed">
                Anda belum memiliki portfolio virtual. Silakan setup akun virtual trading Anda dengan melakukan deposit dana awal untuk mulai simulasi.
              </p>
              <div className="bg-[#030712] border border-white/10 p-8 rounded-3xl flex flex-col items-center gap-5 w-full max-w-md mt-4 shadow-xl relative overflow-hidden">
                <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-indigo-500 to-purple-500"></div>
                <div className="w-full text-left">
                  <label className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-2 block">Pilih Modal Awal (Rp)</label>
                  <input 
                    type="number" 
                    value={topupAmount} 
                    onChange={(e) => setTopupAmount(Number(e.target.value))} 
                    className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 font-mono font-bold text-white text-lg focus:outline-none focus:border-indigo-500 transition" 
                  />
                </div>
                <div className="flex flex-wrap gap-2 w-full justify-center">
                  {[10000000, 50000000, 100000000, 250000000].map((amt) => (
                    <button key={amt} onClick={() => setTopupAmount(amt)} className={`px-3 py-1.5 rounded-lg text-xs font-mono font-bold border transition ${topupAmount === amt ? 'bg-indigo-600/20 border-indigo-500 text-indigo-300' : 'bg-transparent border-white/10 text-slate-500 hover:text-slate-300'}`}>
                      {amt >= 1e6 ? `${amt / 1e6}jt` : amt.toLocaleString('id-ID')}
                    </button>
                  ))}
                </div>
                <button onClick={() => handleTopup(topupAmount)} className="w-full py-4 bg-indigo-600 hover:bg-indigo-500 text-white font-bold rounded-xl transition text-sm shadow-lg shadow-indigo-600/20 mt-2">
                  Mulai Simulasi Trading
                </button>
              </div>
            </div>
          );
        }

        const summary = tradingData?.summary || {};
        const history = tradingData?.history || [];
        const positions = summary?.positions || [];
        const activePositions = positions.filter((p: any) => p.status === 'OPEN') || [];
        const pendingOrders = positions.filter((p: any) => p.status?.startsWith('PENDING')) || [];
        const closedTrades = history.filter((t: any) => t.status !== 'OPEN' && !t.status?.startsWith('PENDING')) || [];

        return (
          <>
            {/* Wallet Metrics Grid */}
            <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
              {[
                { label: '💵 Cash', value: `Rp ${summary.cash?.toLocaleString('id-ID')}`, sub: 'Sisa saldo untuk membeli' },
                { label: '💼 Invested', value: `Rp ${summary.total_invested?.toLocaleString('id-ID')}`, sub: 'Dana terinvestasi di saham' },
                { label: '📊 Total Equity', value: `Rp ${summary.total_equity?.toLocaleString('id-ID')}`, sub: `${summary.total_return_pct >= 0 ? '+' : ''}${summary.total_return_pct?.toFixed(2)}%`, subColor: summary.total_return_pct >= 0 ? 'text-emerald-400' : 'text-red-400' },
                { label: '📈 Realized P&L', value: `Rp ${summary.realized_pnl?.toLocaleString('id-ID')}`, sub: 'Profit/Loss posisi tertutup', valueColor: summary.realized_pnl >= 0 ? 'text-emerald-400' : 'text-red-400' },
                { label: '📊 Unrealized P&L', value: `Rp ${summary.unrealized_pnl?.toLocaleString('id-ID')}`, sub: 'Profit/Loss posisi terbuka', valueColor: summary.unrealized_pnl >= 0 ? 'text-emerald-400' : 'text-red-400' },
              ].map((card, idx) => (
                <div key={idx} className="bg-white/[0.03] border border-white/5 rounded-2xl p-5 hover:bg-white/[0.05] transition duration-300">
                  <p className="text-[11px] text-slate-400 font-bold uppercase tracking-wider mb-2">{card.label}</p>
                  <p className={`text-lg font-black font-mono ${card.valueColor || 'text-white'}`}>{card.value}</p>
                  <p className={`text-xs mt-1 ${card.subColor || 'text-slate-500'}`}>{card.sub}</p>
                </div>
              ))}
            </div>

            {/* Topup + Equity Chart */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              <div className="bg-white/[0.03] border border-white/5 rounded-3xl p-6 flex flex-col justify-between">
                <div>
                  <h4 className="text-sm font-bold text-white uppercase tracking-wider mb-2">💸 Topup Modal Virtual</h4>
                  <p className="text-xs text-slate-400 mb-4">Tambahkan modal virtual untuk melakukan simulasi transaksi pembelian saham.</p>
                  <div className="space-y-4">
                    <div>
                      <label className="text-[10px] text-slate-400 block mb-1.5 font-bold uppercase">Jumlah Topup (Rp)</label>
                      <input type="number" value={topupAmount} onChange={(e) => setTopupAmount(Number(e.target.value))} min={10000000} className="w-full bg-[#030712] border border-white/10 rounded-xl px-4 py-2 font-mono font-bold text-white focus:outline-none focus:border-indigo-500" />
                    </div>
                    <div className="flex flex-wrap gap-1.5">
                      {[10000000, 50000000, 100000000, 250000000].map((amt) => (
                        <button key={amt} onClick={() => setTopupAmount(amt)} className={`px-2.5 py-1.5 rounded-lg text-xs font-mono font-bold border transition ${topupAmount === amt ? 'bg-indigo-600 border-indigo-500 text-white' : 'bg-white/5 border-white/5 text-slate-400 hover:text-white'}`}>
                          {amt >= 1e6 ? `${amt / 1e6}jt` : amt.toLocaleString('id-ID')}
                        </button>
                      ))}
                    </div>
                  </div>
                </div>
                <button onClick={() => handleTopup(topupAmount)} className="mt-6 w-full py-3 bg-white hover:bg-slate-200 text-black font-bold rounded-xl transition text-sm shadow-[0_0_15px_rgba(255,255,255,0.1)]">
                  💸 Eksekusi Topup
                </button>
              </div>
              <div className="lg:col-span-2">
                <CustomEquityChart points={equityData?.points || []} />
              </div>
            </div>

            {/* Manual Order Form + Quick Buy */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
              <div className="bg-white/[0.03] border border-white/5 rounded-3xl p-6 lg:col-span-1">
                <h3 className="text-lg font-bold text-white mb-4 flex items-center gap-2"><span>🛒</span> Place Order (Buy)</h3>
                <div className="space-y-4">
                  <div>
                    <label className="text-[10px] text-slate-400 block mb-1 font-bold uppercase">Ticker Saham</label>
                    <input type="text" value={buyTicker} onChange={(e) => { setBuyTicker(e.target.value); setBuySignalId(null); }} placeholder="e.g. BBCA, MEDC" className="w-full bg-[#030712] border border-white/10 rounded-xl px-4 py-2 text-sm font-mono font-bold text-white uppercase focus:outline-none focus:border-indigo-500" />
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="text-[10px] text-slate-400 block mb-1 font-bold uppercase">Jumlah Lot</label>
                      <input type="number" value={buyLot} onChange={(e) => setBuyLot(Number(e.target.value))} min={1} className="w-full bg-[#030712] border border-white/10 rounded-xl px-4 py-2 text-sm font-mono font-bold text-white focus:outline-none focus:border-indigo-500" />
                    </div>
                    <div>
                      <label className="text-[10px] text-slate-400 block mb-1 font-bold uppercase">Harga Bid (Rp)</label>
                      <input type="number" value={buyPrice} onChange={(e) => setBuyPrice(Number(e.target.value))} min={1} className="w-full bg-[#030712] border border-white/10 rounded-xl px-4 py-2 text-sm font-mono font-bold text-white focus:outline-none focus:border-indigo-500" />
                    </div>
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="text-[10px] text-slate-400 block mb-1 font-bold uppercase">Target TP1 (Optional)</label>
                      <input type="number" value={buyTp} onChange={(e) => setBuyTp(Number(e.target.value))} min={0} placeholder="0" className="w-full bg-[#030712] border border-white/10 rounded-xl px-4 py-2 text-sm font-mono font-bold text-white focus:outline-none focus:border-indigo-500" />
                    </div>
                    <div>
                      <label className="text-[10px] text-slate-400 block mb-1 font-bold uppercase">Target SL (Optional)</label>
                      <input type="number" value={buySl} onChange={(e) => setBuySl(Number(e.target.value))} min={0} placeholder="0" className="w-full bg-[#030712] border border-white/10 rounded-xl px-4 py-2 text-sm font-mono font-bold text-white focus:outline-none focus:border-indigo-500" />
                    </div>
                  </div>
                  <button onClick={() => handleBuy(buyTicker, buyLot, buyPrice, buySignalId, buyTp, buySl)} className="w-full py-3 mt-2 bg-emerald-500 hover:bg-emerald-400 text-white font-bold rounded-xl transition text-sm shadow-lg shadow-emerald-500/20">
                    🛒 Kirim Order Buy
                  </button>
                </div>
              </div>

              {/* Quick Buy from Top Picks */}
              <div className="lg:col-span-2 space-y-4">
                <div className="flex justify-between items-center">
                  <h3 className="text-lg font-bold text-white flex items-center gap-2"><span>🎯</span> Quick Buy dari Top Picks</h3>
                  <button onClick={handleAutoInvestAll} className="px-3.5 py-1.5 bg-indigo-600/10 hover:bg-indigo-600/20 border border-indigo-500/20 text-indigo-400 font-bold rounded-xl text-xs transition">
                    ⚡ Invest Semua (15% each)
                  </button>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 max-h-[360px] overflow-y-auto pr-1">
                  {picks.slice(0, 4).map((pick: any) => {
                    const defaultPrice = pick.entry_high || pick.entry_low || pick.current_price || 1000;
                    return (
                      <div key={pick.ticker} className="bg-white/[0.03] border border-white/5 rounded-2xl p-4 hover:bg-white/[0.05] transition duration-300 flex flex-col justify-between gap-3">
                        <div className="flex justify-between items-start">
                          <div>
                            <h4 className="font-extrabold text-white">{pick.ticker}</h4>
                            <p className="text-[10px] text-slate-500">Rank #{pick.rank || '-'}</p>
                          </div>
                          <div className="text-right">
                            <p className="text-xs text-slate-400 font-mono">Entry: Rp {pick.entry_low?.toLocaleString('id-ID')}–{pick.entry_high?.toLocaleString('id-ID')}</p>
                            <p className="text-[10px] text-slate-500">TP1: Rp {pick.target_1?.toLocaleString('id-ID')} | SL: Rp {pick.stop_loss?.toLocaleString('id-ID')}</p>
                          </div>
                        </div>
                        <div className="flex gap-2">
                          <button
                            onClick={() => { setBuyTicker(pick.ticker); setBuyPrice(defaultPrice); setBuyTp(pick.target_1 || 0); setBuySl(pick.stop_loss || 0); setBuySignalId(pick.id || null); }}
                            className="flex-1 py-1.5 bg-white/5 hover:bg-white/10 text-white rounded-lg text-xs font-bold transition border border-white/5"
                          >Prefill Form</button>
                          <button onClick={() => handleAutoInvestSingle(pick.id, defaultPrice)} className="flex-1 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-xs font-bold transition">
                            ⚡ Auto 20%
                          </button>
                        </div>
                      </div>
                    );
                  })}
                  {picks.length === 0 && <div className="col-span-2 py-10 text-center text-slate-500 text-sm">Tidak ada rekomendasi Top Picks aktif.</div>}
                </div>
              </div>
            </div>

            {/* Pending Orders */}
            <div>
              <h3 className="text-lg font-bold text-white mb-4 flex items-center gap-2"><span>⏳</span> Pending Orders</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {pendingOrders.map((pos: any) => {
                  const diffVal = Math.abs(pos.current_price - pos.buy_price);
                  const diffPct = pos.current_price ? (diffVal / pos.current_price * 100) : 0;
                  return (
                    <div key={pos.id} className="bg-white/[0.03] border border-white/5 rounded-2xl p-5 flex justify-between items-center gap-4">
                      <div>
                        <div className="flex items-center gap-2 mb-1">
                          <h4 className="font-bold text-white">{pos.ticker}</h4>
                          <span className="text-[10px] px-2 py-0.5 rounded bg-white/5 border border-white/10 text-slate-400 font-mono">
                            {pos.status === 'PENDING_STOP' ? '📈 Buy Stop' : '📉 Buy Limit'}
                          </span>
                        </div>
                        <p className="text-xs text-slate-400 font-mono">{pos.lot} lot ({pos.shares?.toLocaleString('id-ID')} lembar)</p>
                        <div className="grid grid-cols-2 gap-x-4 mt-2 text-xs font-mono text-slate-400">
                          <span>Target: Rp {pos.buy_price?.toLocaleString('id-ID')}</span>
                          <span>Live: Rp {pos.current_price?.toLocaleString('id-ID')}</span>
                          <span className="col-span-2 text-slate-500 mt-1">
                            {pos.status === 'PENDING_STOP' ? `Harus Naik: ${diffPct.toFixed(2)}% lagi` : `Harus Turun: ${diffPct.toFixed(2)}% lagi`}
                          </span>
                        </div>
                      </div>
                      <button onClick={() => handleCancelPending(pos.id)} className="px-3.5 py-2 bg-red-500/10 hover:bg-red-500/20 border border-red-500/20 text-red-400 text-xs font-bold rounded-lg transition">Batal</button>
                    </div>
                  );
                })}
                {pendingOrders.length === 0 && <div className="col-span-2 py-8 text-center bg-white/[0.01] border border-dashed border-white/5 rounded-2xl text-slate-500 text-sm">Tidak ada pending orders.</div>}
              </div>
            </div>

            {/* Open Positions */}
            <div>
              <h3 className="text-lg font-bold text-white mb-4 flex items-center gap-2"><span>📈</span> Open Positions</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {activePositions.map((pos: any) => {
                  const isProfit = pos.unrealized_pnl >= 0;
                  const pctToTp = (pos.tp1 && pos.current_price && pos.tp1 > pos.current_price) ? ((pos.tp1 - pos.current_price) / pos.current_price * 100).toFixed(2) : null;
                  const pctToSl = (pos.stop_loss && pos.current_price && pos.stop_loss < pos.current_price) ? ((pos.current_price - pos.stop_loss) / pos.current_price * 100).toFixed(2) : null;
                  return (
                    <div key={pos.id} className="bg-white/[0.03] border border-white/5 rounded-2xl p-5 flex justify-between items-center gap-4">
                      <div className="flex-1">
                        <div className="flex items-center justify-between mb-2">
                          <h4 className="font-extrabold text-white text-lg">{pos.ticker}</h4>
                          <span className={`font-mono font-bold text-sm ${isProfit ? 'text-emerald-400' : 'text-red-400'}`}>{isProfit ? '▲' : '▼'} {pos.unrealized_pnl_pct?.toFixed(2)}%</span>
                        </div>
                        <p className="text-xs text-slate-400 font-mono mb-2">{pos.lot} lot ({pos.shares?.toLocaleString('id-ID')} lembar)</p>
                        <div className="grid grid-cols-2 sm:grid-cols-3 gap-y-3 gap-x-2 font-mono text-[11px] text-slate-400 mt-1">
                          <div><span className="text-[10px] text-slate-500 block">Buy Price</span>Rp {pos.buy_price?.toLocaleString('id-ID')}</div>
                          <div><span className="text-[10px] text-slate-500 block">Cur. Price</span>Rp {pos.current_price?.toLocaleString('id-ID')}</div>
                          <div><span className="text-[10px] text-slate-500 block">Unrealized P&L</span><span className={isProfit ? 'text-emerald-400 font-bold' : 'text-red-400 font-bold'}>Rp {pos.unrealized_pnl?.toLocaleString('id-ID')}</span></div>
                          <div><span className="text-[10px] text-slate-500 block">Invested</span>Rp {((pos.buy_price || 0) * (pos.shares || 0)).toLocaleString('id-ID')}</div>
                          <div><span className="text-[10px] text-slate-500 block">Cur. Value</span><span className={isProfit ? 'text-emerald-400' : 'text-red-400'}>Rp {((pos.current_price || 0) * (pos.shares || 0)).toLocaleString('id-ID')}</span></div>
                          <div>
                            <span className="text-[10px] text-slate-500 block mb-0.5">Target TP / SL</span>
                            <div className="flex flex-col gap-0.5">
                              <div className="flex items-center gap-1"><span className="text-emerald-400">{pos.tp1 ? `Rp ${pos.tp1.toLocaleString('id-ID')}` : '-'}</span>{pctToTp && <span className="text-[9px] text-emerald-500/70">(+{pctToTp}%)</span>}</div>
                              <div className="flex items-center gap-1"><span className="text-red-400">{pos.stop_loss ? `Rp ${pos.stop_loss.toLocaleString('id-ID')}` : '-'}</span>{pctToSl && <span className="text-[9px] text-red-500/70">(-{pctToSl}%)</span>}</div>
                            </div>
                          </div>
                        </div>
                      </div>
                      <button onClick={() => handleSell(pos.id, pos.current_price)} className="px-4 py-3 bg-red-600 hover:bg-red-500 text-white text-xs font-bold rounded-lg transition">SELL</button>
                    </div>
                  );
                })}
                {activePositions.length === 0 && <div className="col-span-2 py-10 text-center bg-white/[0.01] border border-dashed border-white/5 rounded-2xl text-slate-500 text-sm">Tidak ada posisi aktif yang terbuka.</div>}
              </div>
            </div>

            {/* Closed Trades */}
            <div>
              <h3 className="text-lg font-bold text-white mb-4 flex items-center gap-2"><span>📜</span> Trade History (Closed)</h3>
              <div className="overflow-x-auto rounded-2xl border border-white/5 bg-[#030712]/40">
                <table className="w-full text-left border-collapse text-sm">
                  <thead>
                    <tr className="border-b border-white/10 text-xs font-bold uppercase tracking-wider text-slate-400 bg-white/5">
                      <th className="py-3 px-6">Tanggal</th>
                      <th className="py-3 px-6">Ticker</th>
                      <th className="py-3 px-6 text-center">Status</th>
                      <th className="py-3 px-6 text-right">Volume</th>
                      <th className="py-3 px-6 text-right">Buy @</th>
                      <th className="py-3 px-6 text-right">Sell @</th>
                      <th className="py-3 px-6 text-right">Realized P&L</th>
                      <th className="py-3 px-6 text-right">Return</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-white/5 text-slate-300 font-mono">
                    {closedTrades.map((row: any, idx: number) => {
                      const isProfit = row.realized_pnl >= 0;
                      return (
                        <tr key={idx} className="hover:bg-white/5 transition">
                          <td className="py-3 px-6 font-sans text-slate-400">{row.closed_at ? row.closed_at.split('T')[0] : row.opened_at?.split('T')[0]}</td>
                          <td className="py-3 px-6 font-sans font-bold text-white">{row.ticker}</td>
                          <td className="py-3 px-6 text-center">
                            <span className={`px-2 py-1 text-[10px] font-bold rounded-full uppercase tracking-wider ${row.status === 'TP_HIT' ? 'bg-emerald-500/10 text-emerald-400' : row.status === 'SL_HIT' ? 'bg-red-500/10 text-red-400' : 'bg-slate-500/10 text-slate-400'}`}>
                              {row.status?.replace('_', ' ') || 'CLOSED'}
                            </span>
                          </td>
                          <td className="py-3 px-6 text-right">{row.lot} lot</td>
                          <td className="py-3 px-6 text-right">Rp {row.price?.toLocaleString('id-ID')}</td>
                          <td className="py-3 px-6 text-right">Rp {row.exit_price?.toLocaleString('id-ID') || '-'}</td>
                          <td className={`py-3 px-6 text-right font-bold ${isProfit ? 'text-emerald-400' : 'text-red-400'}`}>{isProfit ? '+' : ''}{row.realized_pnl?.toLocaleString('id-ID')}</td>
                          <td className={`py-3 px-6 text-right font-bold ${isProfit ? 'text-emerald-400' : 'text-red-400'}`}>{isProfit ? '+' : ''}{row.realized_pnl_pct?.toFixed(2)}%</td>
                        </tr>
                      );
                    })}
                    {closedTrades.length === 0 && <tr><td colSpan={8} className="py-10 text-center text-slate-500 font-sans">Belum ada riwayat transaksi ditutup.</td></tr>}
                  </tbody>
                </table>
              </div>
            </div>
          </>
        );
      })()}
    </div>
  );
}
