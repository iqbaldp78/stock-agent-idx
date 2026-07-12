"use client";
import React, { useState, useEffect } from 'react';

const formatEntry = (stock: any) => {
  if (!stock) return "-";
  if (stock.entry_low && stock.entry_high) {
    return `${stock.entry_low.toLocaleString('id-ID')} - ${stock.entry_high.toLocaleString('id-ID')}`;
  }
  if (stock.entry_low) return `${stock.entry_low.toLocaleString('id-ID')}`;
  if (stock.entry_high) return `${stock.entry_high.toLocaleString('id-ID')}`;
  return "-";
};

const formatTP = (stock: any) => {
  if (!stock) return "-";
  const tps = [stock.target_1, stock.target_2, stock.target_3].filter(tp => tp !== null && tp !== undefined);
  if (tps.length > 0) {
    return tps.map(tp => `${tp.toLocaleString('id-ID')}`).join(" / ");
  }
  return "-";
};

const formatSL = (stock: any) => {
  if (!stock) return "-";
  return stock.stop_loss ? `${stock.stop_loss.toLocaleString('id-ID')}` : "-";
};

const formatLot = (lots: number) => {
  if (!lots) return "0";
  if (lots >= 1000) {
    return `${(lots / 1000).toFixed(1)}K`;
  }
  return lots.toLocaleString('id-ID');
};

const formatValue = (val: number) => {
  if (!val) return "0";
  if (val >= 1e9) {
    return `${(val / 1e9).toFixed(2)}B`;
  }
  if (val >= 1e6) {
    return `${(val / 1e6).toFixed(2)}M`;
  }
  return val.toLocaleString('id-ID');
};

const formatPercentage = (pct: number) => {
  if (pct === undefined || pct === null) return "0.00%";
  const sign = pct >= 0 ? "+" : "";
  return `${sign}${pct.toFixed(2)}%`;
};

export default function Home() {
  const [picks, setPicks] = useState<any[]>([]);
  const [batchId, setBatchId] = useState("");
  const [runDate, setRunDate] = useState("");
  const [stats, setStats] = useState({ market_outlook: "Loading", win_rate: 0, profit_factor: 0 });
  const [wallet, setWallet] = useState({ cash: 0, invested: 0, pnl: 0 });
  const [holdings, setHoldings] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [tradeStatus, setTradeStatus] = useState("");
  const [isPro, setIsPro] = useState(true); // Hardcode VIP Pro

  const [activeTab, setActiveTab] = useState("dashboard"); // 'dashboard' | 'top-picks' | 'history' | 'settings'
  const [historyData, setHistoryData] = useState<any[]>([]);
  const [selectedStock, setSelectedStock] = useState<any | null>(null);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [showFairValueDetails, setShowFairValueDetails] = useState(false);
  const [showTrueCostDetails, setShowTrueCostDetails] = useState(true);
  const [showDistDetails, setShowDistDetails] = useState(true);

  const [bandarmologiTicker, setBandarmologiTicker] = useState("MEDC");
  const [bandarmologiData, setBandarmologiData] = useState<any | null>(null);
  const [bandarLoading, setBandarLoading] = useState(false);
  const [bandarTimeframe, setBandarTimeframe] = useState("1m"); // '7d' | '1m'

  const fetchBandarmologiData = async (ticker: string) => {
    setBandarLoading(true);
    try {
      const res = await fetch(`/api/bandarmologi/${ticker}`);
      const data = await res.json();
      if (data && !data.error) {
        setBandarmologiData(data);
      }
    } catch (err) {
      console.error("Error loading bandarmologi data:", err);
    } finally {
      setBandarLoading(false);
    }
  };

  useEffect(() => {
    if (activeTab === 'bandarmologi') {
      fetchBandarmologiData(bandarmologiTicker);
    }
  }, [activeTab, bandarmologiTicker]);

  const loadData = async () => {
    // Fetch top picks
    fetch('/api/signals/top-picks')
      .then(res => res.json())
      .then(data => {
        if (data.data) {
          setPicks(data.data);
          setBatchId(data.batch_id);
          setRunDate(data.run_date || "");
        }
      })
      .catch(err => console.error("Error loading picks API:", err));

    // Fetch stats
    fetch('/api/dashboard/stats')
      .then(res => res.json())
      .then(data => {
        setStats(data);
        setLoading(false);
      })
      .catch(err => {
        console.error("Error loading stats API:", err);
        setLoading(false);
      });

    // Fetch portfolio
    fetch('/api/portfolio/paper')
      .then(res => res.json())
      .then(data => {
        if(data.wallet) setWallet(data.wallet);
        if(data.holdings) setHoldings(data.holdings);
      })
      .catch(err => console.error("Error loading portfolio:", err));

    // Fetch history
    fetch('/api/performance/history')
      .then(res => res.json())
      .then(data => {
        if(data.history) setHistoryData(data.history);
      })
      .catch(err => console.error("Error loading history:", err));
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleTrade = async (ticker: string, action: string, price: number) => {
    if(!price) {
      alert("Harga belum tersedia untuk saham ini.");
      return;
    }
    
    setTradeStatus(`Memproses ${action} ${ticker}...`);
    try {
      const res = await fetch('/api/portfolio/trade', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: 1,
          ticker: ticker,
          action: action === "HOLD" ? "BUY" : action, // Simulate BUY for HOLD signals
          shares: 100, // 1 Lot standard
          price: price
        })
      });
      const data = await res.json();
      if(res.ok) {
        setTradeStatus(`Sukses beli 1 lot ${ticker}!`);
        loadData(); // Reload wallet & holdings
      } else {
        setTradeStatus(`Gagal: ${data.detail || 'Error'}`);
      }
    } catch(err) {
      setTradeStatus("Terjadi kesalahan jaringan");
    }
    setTimeout(() => setTradeStatus(""), 3000);
  };

  return (
    <div className="min-h-screen bg-[#030712] text-slate-100 font-sans relative overflow-x-hidden overflow-y-auto w-full h-full pb-20">
      {/* Background Orbs */}
      <div className="fixed top-[-10%] left-[-10%] w-[50vw] h-[50vw] rounded-full bg-[radial-gradient(circle,rgba(99,102,241,0.15)_0%,rgba(0,0,0,0)_70%)] z-0 pointer-events-none"></div>
      <div className="fixed bottom-[-10%] right-[-10%] w-[60vw] h-[60vw] rounded-full bg-[radial-gradient(circle,rgba(168,85,247,0.15)_0%,rgba(0,0,0,0)_70%)] z-0 pointer-events-none"></div>

      {/* Sidebar Overlay */}
      {sidebarOpen && (
        <div 
          className="fixed inset-0 bg-black/60 backdrop-blur-sm z-[60] transition-opacity"
          onClick={() => setSidebarOpen(false)}
        ></div>
      )}

      {/* Sidebar */}
      <aside className={`fixed top-0 left-0 h-full w-64 bg-[#030712]/95 backdrop-blur-2xl border-r border-white/10 z-[70] transform transition-transform duration-300 ease-in-out ${sidebarOpen ? 'translate-x-0' : '-translate-x-full'}`}>
        <div className="p-6 flex flex-col h-full">
          <div className="flex items-center justify-between mb-10">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-full bg-gradient-to-tr from-indigo-500 to-purple-500 flex items-center justify-center shadow-lg shadow-indigo-500/20 text-white font-bold text-sm">
                H
              </div>
              <h1 className="font-bold text-xl tracking-wide">
                Hamboo<span className="text-indigo-400">.ai</span>
              </h1>
            </div>
            <button onClick={() => setSidebarOpen(false)} className="text-slate-400 hover:text-white transition">
              ✕
            </button>
          </div>

          <nav className="space-y-2">
            <button onClick={() => { setActiveTab("dashboard"); setSidebarOpen(false); }} className={`w-full flex items-center gap-4 px-4 py-3 rounded-xl font-medium transition ${activeTab === 'dashboard' ? 'bg-white/10 text-white border border-white/5 shadow-[0_0_15px_rgba(255,255,255,0.05)]' : 'text-slate-400 hover:text-white hover:bg-white/5'}`}>
              <span className="text-lg">🏠</span> Home Dashboard
            </button>
            <button onClick={() => { setActiveTab("top-picks"); setSidebarOpen(false); }} className={`w-full flex items-center gap-4 px-4 py-3 rounded-xl font-medium transition ${activeTab === 'top-picks' ? 'bg-white/10 text-white border border-white/5 shadow-[0_0_15px_rgba(255,255,255,0.05)]' : 'text-slate-400 hover:text-white hover:bg-white/5'}`}>
              <span className="text-lg">🎯</span> AI Top Picks
            </button>
            <button onClick={() => { setActiveTab("bandarmologi"); setSidebarOpen(false); }} className={`w-full flex items-center gap-4 px-4 py-3 rounded-xl font-medium transition ${activeTab === 'bandarmologi' ? 'bg-white/10 text-white border border-white/5 shadow-[0_0_15px_rgba(255,255,255,0.05)]' : 'text-slate-400 hover:text-white hover:bg-white/5'}`}>
              <span className="text-lg">🏛️</span> Bandarmologi
            </button>
            <button onClick={() => { setActiveTab("history"); setSidebarOpen(false); }} className={`w-full flex items-center gap-4 px-4 py-3 rounded-xl font-medium transition ${activeTab === 'history' ? 'bg-white/10 text-white border border-white/5 shadow-[0_0_15px_rgba(255,255,255,0.05)]' : 'text-slate-400 hover:text-white hover:bg-white/5'}`}>
              <span className="text-lg">📈</span> AI Track Record
            </button>
            <button onClick={() => { setActiveTab("settings"); setSidebarOpen(false); }} className={`w-full flex items-center gap-4 px-4 py-3 rounded-xl font-medium transition ${activeTab === 'settings' ? 'bg-white/10 text-white border border-white/5 shadow-[0_0_15px_rgba(255,255,255,0.05)]' : 'text-slate-400 hover:text-white hover:bg-white/5'}`}>
              <span className="text-lg">⚙️</span> Preferences
            </button>
            <a href="https://admin.hamboo.me" target="_blank" className="flex items-center gap-4 px-4 py-3 text-slate-400 hover:text-white hover:bg-white/5 rounded-xl transition font-medium">
              <span className="text-lg">👨‍💻</span> Admin Panel
            </a>
          </nav>

          <div className="mt-auto pt-6 border-t border-white/10">
            <div className="bg-indigo-500/10 border border-indigo-500/20 rounded-xl p-4 mb-4">
              <p className="text-xs text-indigo-300 font-bold mb-1">PRO ACCOUNT AKTIF</p>
              <p className="text-[10px] text-slate-400">Akses sinyal unlimited dan AI reasoning detail menyala.</p>
            </div>
            <a href="#" className="flex items-center gap-4 px-4 py-3 text-red-400 hover:text-red-300 hover:bg-red-500/10 rounded-xl transition font-medium">
              <span>🚪</span> Sign Out
            </a>
          </div>
        </div>
      </aside>

      {/* Navbar */}
      <nav className="sticky top-0 z-50 bg-[#030712]/70 backdrop-blur-xl border-b border-white/5">
        <div className="max-w-5xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <button onClick={() => setSidebarOpen(true)} className="mr-2 p-2 rounded-lg text-slate-400 hover:text-white hover:bg-white/10 transition">
              <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="3" y1="12" x2="21" y2="12"></line><line x1="3" y1="6" x2="21" y2="6"></line><line x1="3" y1="18" x2="21" y2="18"></line></svg>
            </button>
            <div className="w-8 h-8 rounded-full bg-gradient-to-tr from-indigo-500 to-purple-500 flex items-center justify-center shadow-lg shadow-indigo-500/20 text-white font-bold text-sm">
              H
            </div>
              <h1 className="font-bold text-xl tracking-wide">
                Hamboo<span className="text-indigo-400">.ai</span>
              </h1>
            </div>
            
            <div className="flex items-center gap-4 text-sm font-medium">
              <div className="bg-[#030712] p-1 rounded-full border border-white/10 flex text-xs">
                <button className={`px-4 py-1.5 rounded-full transition ${isPro ? 'text-slate-400 hover:text-white' : 'bg-indigo-500 text-white shadow-lg shadow-indigo-500/20'}`} onClick={() => setIsPro(false)}>Free</button>
                <button className={`px-4 py-1.5 rounded-full transition flex items-center gap-1 ${isPro ? 'bg-gradient-to-r from-indigo-500 to-purple-500 text-white shadow-lg shadow-purple-500/20' : 'text-slate-400 hover:text-white'}`} onClick={() => setIsPro(true)}>
                  Pro <span className="text-[10px] bg-white/20 px-1.5 rounded-md">✨</span>
                </button>
              </div>
              
              <span className="px-3 py-1 rounded-full bg-white/5 border border-white/10 text-emerald-400 font-mono">
                Cash: Rp {(wallet.cash || 0).toLocaleString('id-ID')}
              </span>
            </div>
          </div>
        </nav>
      {/* End Sidebar & Navbar */}

      <main className="max-w-5xl mx-auto px-6 py-10 space-y-10 relative z-10">
        
        {/* TAB: DASHBOARD */}
        {activeTab === 'dashboard' && (
          <div className="space-y-10 animate-fade-in">
            {/* Hero Section */}
            <div className="text-center space-y-4 py-8">
              <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-indigo-500/10 border border-indigo-500/20 text-indigo-300 text-xs font-semibold uppercase tracking-widest mb-4">
            <span className="w-1.5 h-1.5 rounded-full bg-indigo-400 animate-pulse"></span>
            AI Model is Active
          </div>
          <h2 className="text-4xl md:text-5xl font-bold tracking-tight text-white">
            Selamat Datang di <br />
            <span className="bg-gradient-to-r from-indigo-400 to-purple-400 bg-clip-text text-transparent">Hamboo AI Terminal.</span>
          </h2>
          <p className="text-slate-400 max-w-2xl mx-auto text-lg">Pusat komando investasi cerdasmu. Pantau kondisi pasar, lihat riwayat portofoliomu, dan temukan saham potensial lewat analisa AI.</p>
        </div>

        {/* 3 Stats Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="bg-white/[0.03] backdrop-blur-md border border-white/5 rounded-2xl p-6 hover:bg-white/5 transition duration-300">
            <div className="flex justify-between items-start mb-4">
              <div className={`w-10 h-10 rounded-full flex items-center justify-center font-bold ${stats.market_outlook === 'Bullish' ? 'bg-emerald-500/10 text-emerald-400' : stats.market_outlook === 'Bearish' ? 'bg-red-500/10 text-red-400' : 'bg-slate-500/10 text-slate-400'}`}>
                {stats.market_outlook === 'Bullish' ? '↗' : stats.market_outlook === 'Bearish' ? '↘' : '→'}
              </div>
              <span className="text-xs font-semibold text-slate-500 uppercase">Arah Pasar</span>
            </div>
            <h3 className={`text-3xl font-bold ${stats.market_outlook === 'Bullish' ? 'text-emerald-400' : stats.market_outlook === 'Bearish' ? 'text-red-400' : 'text-slate-400'}`}>
              {stats.market_outlook}
            </h3>
            <p className="text-sm text-slate-400 mt-1">Sinyal saham utama</p>
          </div>

          <div className="bg-white/[0.03] backdrop-blur-md border border-white/5 rounded-2xl p-6 hover:bg-white/5 transition duration-300">
            <div className="flex justify-between items-start mb-4">
              <div className="w-10 h-10 rounded-full bg-purple-500/10 flex items-center justify-center text-purple-400 font-bold">◎</div>
              <span className="text-xs font-semibold text-slate-500 uppercase">AI Win Rate</span>
            </div>
            <h3 className="text-3xl font-bold text-white">{stats.win_rate}%</h3>
            <p className="text-sm text-slate-400 mt-1">Akurasi historis portfolio</p>
          </div>

          <div className="bg-white/[0.03] backdrop-blur-md border border-white/5 rounded-2xl p-6 hover:bg-white/5 transition duration-300">
            <div className="flex justify-between items-start mb-4">
              <div className="w-10 h-10 rounded-full bg-blue-500/10 flex items-center justify-center text-blue-400 font-bold">⚖</div>
              <span className="text-xs font-semibold text-slate-500 uppercase">Profit Factor</span>
            </div>
            <h3 className="text-3xl font-bold text-white">{stats.profit_factor}x</h3>
            <p className="text-sm text-slate-400 mt-1">Gross profit / Gross loss</p>
          </div>
        </div>
      </div>
      )} {/* END DASHBOARD TAB */}

            {/* TAB: TOP PICKS */}
            {activeTab === 'top-picks' && !selectedStock && (
          <div className="space-y-10 animate-fade-in">
            <div className="text-center space-y-4 py-8">
              <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-purple-500/10 border border-purple-500/20 text-purple-300 text-xs font-semibold uppercase tracking-widest mb-4">
                <span className="w-1.5 h-1.5 rounded-full bg-purple-400 animate-pulse"></span>
                Fresh Signals Available
              </div>
              <h2 className="text-4xl md:text-5xl font-bold tracking-tight text-white">
                Sinyal Trading Masa Depan, <br />
                <span className="bg-gradient-to-r from-indigo-400 to-purple-400 bg-clip-text text-transparent">Ditenagai oleh AI.</span>
              </h2>
              <p className="text-slate-400 max-w-2xl mx-auto text-lg">Pilihan saham eksklusif hasil perdebatan beberapa LLM independen dan analisis fundamental teknikal mendalam.</p>
            </div>
            
            {/* Top Picks List */}
            {picks.length === 0 ? (
              <div className="text-center py-20 text-slate-400">
                <div className="w-16 h-16 rounded-full bg-slate-800 flex items-center justify-center mx-auto mb-4 text-2xl">🔍</div>
                <h4 className="text-lg font-bold text-white mb-2">No Data Found</h4>
                <p>Tidak ada sinyal rekomendasi saham yang aktif saat ini dari AI.</p>
              </div>
            ) : (
              <div className="space-y-8">
                <div className="flex justify-between items-end mb-2">
                  <h3 className="text-2xl font-bold text-white">Today's AI Picks</h3>
                  <p className="text-sm text-slate-500">Running Date: <span className="font-mono text-indigo-300">{runDate}</span></p>
                </div>
                
                {/* 1st Top Pick (Featured) */}
                <div className="bg-gradient-to-b from-indigo-500/10 to-transparent border border-indigo-500/20 rounded-3xl p-1 shadow-[0_0_50px_rgba(99,102,241,0.05)] relative overflow-hidden">
                  {/* ... same 1st pick content ... */}
                  <div className="absolute top-0 right-0 w-64 h-64 bg-indigo-500/10 rounded-full blur-3xl -translate-y-1/2 translate-x-1/2"></div>
                  
                  <div className="bg-[#030712]/80 backdrop-blur-xl rounded-[23px] p-8 h-full flex flex-col relative z-10">
                    <div className="flex justify-between items-start mb-6">
                      <div>
                        <div className="flex items-center gap-3 mb-1">
                          <h4 
                            className="text-3xl font-black text-white hover:text-indigo-400 cursor-pointer transition-colors"
                            onClick={() => setSelectedStock(picks[0])}
                          >
                            {picks[0].ticker}
                          </h4>
                        </div>
                        <p className="text-slate-500 font-medium text-sm mb-3">Saham Tbk.</p>
                        <span className={`px-4 py-1.5 rounded-full text-xs font-bold uppercase tracking-wider ${picks[0].action === 'BUY' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' : picks[0].action === 'SELL' ? 'bg-red-500/10 text-red-400 border border-red-500/20' : 'bg-slate-500/10 text-slate-400 border border-slate-500/20'}`}>
                          {picks[0].action}
                        </span>
                      </div>
                      
                      <div className="text-right">
                        <div className="text-3xl font-bold text-white font-mono">{picks[0].current_price || picks[0].entry_price}</div>
                        <p className="text-slate-500 text-xs mt-1 uppercase font-bold tracking-widest">Current Price</p>
                      </div>
                    </div>

                    <div className="grid grid-cols-2 gap-4 mb-4">
                      <div className="bg-white/5 rounded-xl p-4 border border-white/5">
                        <p className="text-xs text-slate-400 font-bold uppercase tracking-wider mb-1">AI Confidence</p>
                        <div className="flex items-end gap-2">
                          <span className="text-2xl font-bold text-indigo-400">{picks[0].confidence_score}</span>
                          <span className="text-slate-500 mb-1">/ 10</span>
                        </div>
                      </div>
                      <div className="bg-white/5 rounded-xl p-4 border border-white/5">
                        <p className="text-xs text-slate-400 font-bold uppercase tracking-wider mb-1">Risk Profile</p>
                        <p className="text-xl font-bold text-white">Moderate</p>
                      </div>
                    </div>

                    <div className="grid grid-cols-3 gap-4 mb-8">
                      <div className="bg-white/5 rounded-xl p-4 border border-white/5">
                        <p className="text-[10px] text-slate-400 font-bold uppercase tracking-wider mb-1">Entry Range</p>
                        <p className="text-sm font-bold text-white font-mono">{formatEntry(picks[0])}</p>
                      </div>
                      <div className="bg-white/5 rounded-xl p-4 border border-white/5">
                        <p className="text-[10px] text-slate-400 font-bold uppercase tracking-wider mb-1">Take Profit</p>
                        <p className="text-sm font-bold text-emerald-400 font-mono">{formatTP(picks[0])}</p>
                      </div>
                      <div className="bg-white/5 rounded-xl p-4 border border-white/5">
                        <p className="text-[10px] text-slate-400 font-bold uppercase tracking-wider mb-1">Stop Loss</p>
                        <p className="text-sm font-bold text-red-400 font-mono">{formatSL(picks[0])}</p>
                      </div>
                    </div>

                    <div className="mt-auto">
                      <p className="text-sm text-slate-400 mb-6 line-clamp-2">
                        {picks[0].reasoning}
                      </p>
                        
                      <div className="pt-2">
                        <button 
                          onClick={() => setSelectedStock(picks[0])}
                          className="w-full py-4 rounded-xl font-bold text-white bg-indigo-500 hover:bg-indigo-600 transition shadow-lg shadow-indigo-500/20 text-lg">
                          Lihat Detail & Analisis
                        </button>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Grid for remaining picks */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6 relative">
                  {picks.slice(1).map((pick, i) => (
                    <div key={i} className={`bg-white/[0.03] backdrop-blur-md border border-white/5 rounded-3xl p-6 flex flex-col hover:bg-white/5 transition duration-300 ${!isPro ? 'filter blur-sm opacity-50 pointer-events-none' : ''}`}>
                      <div className="flex justify-between items-start mb-4">
                        <div>
                          <h4 
                            className="text-2xl font-black text-white mb-1 hover:text-indigo-400 cursor-pointer transition-colors"
                            onClick={() => setSelectedStock(pick)}
                          >
                            {pick.ticker}
                          </h4>
                          <span className={`px-3 py-1 rounded-full text-[10px] font-bold uppercase tracking-wider border ${pick.action === 'BUY' ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' : pick.action === 'SELL' ? 'bg-red-500/10 text-red-400 border-red-500/20' : 'bg-slate-500/10 text-slate-400 border-slate-500/20'}`}>
                            {pick.action}
                          </span>
                        </div>
                        <div className="text-right">
                          <div className="text-xl font-bold text-white font-mono">{pick.current_price || pick.entry_price}</div>
                          <div className="text-[10px] text-slate-500 font-bold mt-1 uppercase tracking-wider">Current Price</div>
                        </div>
                      </div>

                      <div className="grid grid-cols-3 gap-2 mb-4">
                        <div className="bg-white/5 rounded-lg p-2 border border-white/5">
                          <p className="text-[9px] text-slate-400 font-bold uppercase tracking-wider mb-0.5">Entry</p>
                          <p className="text-[11px] font-bold text-white font-mono truncate">{formatEntry(pick)}</p>
                        </div>
                        <div className="bg-white/5 rounded-lg p-2 border border-white/5">
                          <p className="text-[9px] text-slate-400 font-bold uppercase tracking-wider mb-0.5">TP</p>
                          <p className="text-[11px] font-bold text-emerald-400 font-mono truncate">{formatTP(pick)}</p>
                        </div>
                        <div className="bg-white/5 rounded-lg p-2 border border-white/5">
                          <p className="text-[9px] text-slate-400 font-bold uppercase tracking-wider mb-0.5">SL</p>
                          <p className="text-[11px] font-bold text-red-400 font-mono truncate">{formatSL(pick)}</p>
                        </div>
                      </div>

                      <div className="mt-auto">
                        <p className="text-sm text-slate-400 mb-6 line-clamp-2">
                          {pick.reasoning}
                        </p>
                
                        {/* Simple Info Only */}
                        <div className="pt-2">
                          <button 
                            onClick={() => setSelectedStock(pick)}
                            className="w-full py-3 rounded-xl font-bold text-white bg-indigo-500 hover:bg-indigo-600 transition text-sm shadow-lg shadow-indigo-500/20">
                            Lihat Detail & Analisis
                          </button>
                        </div>
                      </div>
                    </div>
                  ))}

                  {/* Locked/Premium area */}
                  {!isPro && picks.length > 1 && (
                    <div className="absolute inset-0 bg-[#030712]/60 backdrop-blur-[2px] rounded-3xl flex flex-col justify-center items-center text-center p-8 z-20 border border-white/10">
                      <div className="w-16 h-16 bg-gradient-to-tr from-indigo-500 to-purple-500 rounded-2xl flex items-center justify-center mb-6 shadow-xl shadow-indigo-500/20">
                        <span className="text-3xl">🔒</span>
                      </div>
                      <h4 className="text-2xl font-bold text-white mb-3">Pro Tier Required</h4>
                      <p className="text-slate-400 mb-8 max-w-sm">Upgrade ke akun Pro untuk membuka seluruh sinyal trading harian, deteksi algoritma bandarmologi, dan prediksi harga AI lanjutan.</p>
                      <button onClick={() => setIsPro(true)} className="px-8 py-4 rounded-xl font-bold text-white bg-gradient-to-r from-indigo-500 to-purple-500 shadow-lg shadow-purple-500/25 hover:scale-105 transition transform">
                        Upgrade ke Pro ✨
                      </button>
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
          )}

          {/* STOCK DETAIL VIEW */}
          {activeTab === 'top-picks' && selectedStock && (
            <div className="space-y-6 animate-fade-in">
              <button 
                onClick={() => setSelectedStock(null)}
                className="flex items-center gap-2 text-slate-400 hover:text-white transition group mb-4"
              >
                <span className="w-8 h-8 rounded-full bg-white/5 group-hover:bg-white/10 flex items-center justify-center transition">←</span>
                <span className="text-sm font-semibold">Kembali ke Daftar</span>
              </button>

              <div className="bg-[#030712] border border-white/5 rounded-3xl p-8 relative overflow-hidden">
                {/* Decorative BG */}
                <div className="absolute top-0 right-0 w-96 h-96 bg-indigo-500/10 rounded-full blur-3xl -translate-y-1/2 translate-x-1/2 pointer-events-none"></div>

                <div className="relative z-10">
                  <div className="flex justify-between items-start mb-8">
                    <div>
                      <div className="flex items-center gap-3 mb-2">
                        <h2 className="text-5xl font-black text-white">{selectedStock.ticker}</h2>
                        <span className={`px-4 py-1.5 rounded-full text-sm font-bold shadow-lg ${selectedStock.action === 'BUY' ? 'bg-emerald-500 text-white shadow-emerald-500/20' : selectedStock.action === 'SELL' ? 'bg-red-500 text-white shadow-red-500/20' : 'bg-slate-700 text-white'}`}>
                          {selectedStock.action}
                        </span>
                      </div>
                      <p className="text-slate-400 font-medium text-lg">{selectedStock.company_name || 'Saham Tbk.'}</p>
                    </div>
                    
                    <div className="text-right">
                      <div className="text-5xl font-bold text-white font-mono">{selectedStock.current_price || selectedStock.entry_price}</div>
                      <p className="text-slate-500 text-sm mt-1">Current Price</p>
                    </div>
                  </div>

                  {/* Summary Stats */}
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
                    <div className="bg-white/5 rounded-xl p-4 border border-white/5">
                      <p className="text-xs text-slate-400 font-bold uppercase tracking-wider mb-1">AI Confidence</p>
                      <div className="flex items-end gap-2">
                        <span className="text-2xl font-bold text-indigo-400">{selectedStock.confidence_score}</span>
                        <span className="text-slate-500 mb-1">/ 10</span>
                      </div>
                    </div>
                    <div className="bg-white/5 rounded-xl p-4 border border-white/5">
                      <p className="text-xs text-slate-400 font-bold uppercase tracking-wider mb-1">Target Fair Value</p>
                      <p className="text-xl font-bold text-emerald-400">{selectedStock.fair_value ? `Rp ${selectedStock.fair_value.toLocaleString('id-ID')}` : "-"}</p>
                    </div>
                    <div className="bg-white/5 rounded-xl p-4 border border-white/5">
                      <p className="text-xs text-slate-400 font-bold uppercase tracking-wider mb-1">Bandar Avg Cost</p>
                      <p className="text-xl font-bold text-indigo-400">{selectedStock.bandar_avg ? `Rp ${selectedStock.bandar_avg.toLocaleString('id-ID')}` : "-"}</p>
                    </div>
                    <div className="bg-white/5 rounded-xl p-4 border border-white/5 flex items-center justify-center">
                      <button 
                        onClick={() => handleTrade(selectedStock.ticker, selectedStock.action, selectedStock.current_price || selectedStock.entry_price)}
                        className="w-full py-3 rounded-lg font-bold text-white bg-indigo-500 hover:bg-indigo-600 transition text-sm">
                        Simulasi Transaksi
                      </button>
                    </div>
                  </div>

                  {/* Entry, TP, SL targets */}
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
                    <div className="bg-white/5 rounded-xl p-4 border border-white/5 flex flex-col justify-center">
                      <p className="text-xs text-slate-400 font-bold uppercase tracking-wider mb-1">Entry Range</p>
                      <p className="text-base font-bold text-white font-mono">{formatEntry(selectedStock)}</p>
                    </div>
                    <div className="bg-white/5 rounded-xl p-4 border border-white/5 flex flex-col justify-center">
                      <p className="text-xs text-slate-400 font-bold uppercase tracking-wider mb-1">Take Profit Targets</p>
                      <p className="text-base font-bold text-emerald-400 font-mono">{formatTP(selectedStock)}</p>
                    </div>
                    <div className="bg-white/5 rounded-xl p-4 border border-white/5 flex flex-col justify-center">
                      <p className="text-xs text-slate-400 font-bold uppercase tracking-wider mb-1">Stop Loss</p>
                      <p className="text-base font-bold text-red-400 font-mono">{formatSL(selectedStock)}</p>
                    </div>
                  </div>

                  {/* Collapsible Fair Value Details */}
                  {selectedStock.fair_value_details && (
                    <div className="bg-white/[0.03] backdrop-blur-md border border-white/5 rounded-3xl p-6 mb-8 hover:bg-white/5 transition duration-300">
                      <div className="flex flex-wrap items-center justify-between gap-4 mb-4 pb-4 border-b border-white/5">
                        <div className="flex items-center gap-2 text-base font-semibold text-white">
                          <span>💰 Fair Value:</span>
                          <span className={`inline-block w-2.5 h-2.5 rounded-full ${
                            selectedStock.fair_value_details.valuation_label?.includes('UNDERVALUED') 
                              ? 'bg-emerald-500 shadow-[0_0_10px_rgba(16,185,129,0.5)]' 
                              : selectedStock.fair_value_details.valuation_label?.includes('OVERVALUED')
                              ? 'bg-red-500 shadow-[0_0_10px_rgba(239,68,68,0.5)]'
                              : 'bg-yellow-500 shadow-[0_0_10px_rgba(245,158,11,0.5)]'
                          }`}></span>
                          <span className="font-bold text-emerald-400">Rp {(selectedStock.fair_value_details.fair_value_base || selectedStock.fair_value_details.fair_value || 0).toLocaleString('id-ID')}</span>
                          <span className="text-slate-500">|</span>
                          <span className="text-slate-300">Upside:</span>
                          <span className={`font-mono font-bold ${selectedStock.fair_value_details.upside_pct >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                            {selectedStock.fair_value_details.upside_pct >= 0 ? '+' : ''}{selectedStock.fair_value_details.upside_pct?.toFixed(2)}%
                          </span>
                          <span className="text-slate-500">|</span>
                          <span className="text-slate-300 font-bold uppercase tracking-wider text-xs bg-white/5 px-2.5 py-1 rounded-md border border-white/10">
                            {selectedStock.fair_value_details.valuation_label?.replace('_', ' ')} ({selectedStock.fair_value_details.confidence})
                          </span>
                        </div>
                      </div>

                      {/* Collapsible Header */}
                      <button 
                        onClick={() => setShowFairValueDetails(!showFairValueDetails)}
                        className="w-full flex items-center justify-between py-2 text-slate-300 hover:text-white transition font-medium text-sm border border-white/5 bg-white/5 px-4 rounded-xl"
                      >
                        <span className="flex items-center gap-2">
                          <span className="text-indigo-400">📐</span> Detail Fair Value {selectedStock.ticker}
                        </span>
                        <span>{showFairValueDetails ? '▲' : '▼'}</span>
                      </button>

                      {/* Collapsible Body */}
                      {showFairValueDetails && (
                        <div className="mt-4 p-4 rounded-xl bg-[#030712]/60 border border-white/5 space-y-4 animate-fade-in">
                          <div className="text-sm font-bold text-slate-300">
                            Range: <span className="font-mono text-white">Rp {(selectedStock.fair_value_details.fair_value_low || 0).toLocaleString('id-ID')}</span> – <span className="font-mono text-white">Rp {(selectedStock.fair_value_details.fair_value_high || 0).toLocaleString('id-ID')}</span>
                          </div>
                          
                          <ul className="space-y-2 text-sm text-slate-300">
                            {selectedStock.fair_value_details.methods && Object.keys(selectedStock.fair_value_details.methods).map((method) => {
                              const mData = selectedStock.fair_value_details.methods[method];
                              if (!mData || !mData.available) return null;
                              return (
                                <li key={method} className="flex items-center gap-2">
                                  <span className="text-indigo-400">•</span>
                                  <span className="font-semibold font-mono">{method}:</span>
                                  <span className="font-bold text-white">Rp {(mData.fair_value || 0).toLocaleString('id-ID')}</span>
                                </li>
                              );
                            })}
                          </ul>

                          {selectedStock.fair_value_details.notes && selectedStock.fair_value_details.notes.length > 0 && (
                            <div className="pt-3 border-t border-white/5 text-[10px] text-slate-500 leading-relaxed font-mono">
                              {selectedStock.fair_value_details.notes.join(' | ')}
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  )}
                  {/* Price Projections (Full Width) */}
                  {selectedStock.predictions && Object.keys(selectedStock.predictions).length > 0 && (
                    <div className="bg-white/[0.03] border border-white/5 rounded-2xl p-6 mb-8 hover:bg-white/[0.05] transition duration-300">
                      <h4 className="text-sm font-bold text-slate-400 uppercase tracking-widest mb-4 border-b border-white/5 pb-2 flex items-center gap-2">
                        <span>🎯</span> Price Projections
                      </h4>
                      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                        {['day_1', 'day_3', 'day_5', 'day_7'].map((day, idx) => (
                          selectedStock.predictions[day] && (
                            <div key={idx} className="bg-white/5 rounded-xl p-4 text-center border border-white/5 hover:bg-white/10 transition duration-300">
                              <p className="text-xs text-slate-400 font-mono mb-1">T+{day.split('_')[1]}</p>
                              <p className="font-extrabold text-white text-lg font-mono">{selectedStock.predictions[day].price}</p>
                              <p className={`text-xs font-bold font-mono mt-1 ${String(selectedStock.predictions[day].pct_change).includes('-') ? 'text-red-400' : 'text-emerald-400'}`}>
                                {selectedStock.predictions[day].pct_change}
                              </p>
                            </div>
                          )
                        ))}
                      </div>
                    </div>
                  )}

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                    {/* Left Column */}
                    <div className="space-y-8">
                      <div className="bg-white/[0.03] border border-white/5 rounded-2xl p-6 hover:bg-white/[0.05] transition duration-300">
                        <h4 className="text-sm font-bold text-slate-400 uppercase tracking-widest mb-4 border-b border-white/5 pb-2 flex items-center gap-2">
                          <span>🧠</span> AI Deep Reasoning
                        </h4>
                        <p className="text-sm text-slate-300 leading-relaxed">
                          {selectedStock.reasoning}
                        </p>
                      </div>

                      {selectedStock.thesis && (
                        <div className="bg-indigo-500/5 border border-indigo-500/10 hover:border-indigo-500/20 rounded-2xl p-6 hover:bg-indigo-500/10 transition duration-300">
                          <h4 className="text-sm font-bold text-indigo-300 uppercase tracking-widest mb-4 border-b border-indigo-500/10 pb-2 flex items-center gap-2">
                            <span>📜</span> Investment Thesis
                          </h4>
                          <p className="text-sm text-slate-300 leading-relaxed">
                            {selectedStock.thesis}
                          </p>
                        </div>
                      )}
                    </div>

                    {/* Right Column */}
                    <div className="space-y-8">
                      {/* Key Drivers */}
                      {selectedStock.key_drivers && selectedStock.key_drivers.length > 0 && (
                        <div className="bg-white/[0.03] border border-white/5 rounded-2xl p-6 hover:bg-white/[0.05] transition duration-300">
                          <h4 className="text-sm font-bold text-slate-400 uppercase tracking-widest mb-4 border-b border-white/5 pb-2 flex items-center gap-2">
                            <span>⚡</span> Key Drivers
                          </h4>
                          <ul className="space-y-3">
                            {selectedStock.key_drivers.map((driver: string, idx: number) => (
                              <li key={idx} className="text-sm text-slate-300 flex items-start gap-3">
                                <span className="text-emerald-400 shrink-0 mt-0.5 text-lg leading-none">✓</span>
                                <span>{driver}</span>
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}

                      {/* Risks */}
                      {selectedStock.risks && selectedStock.risks.length > 0 && (
                        <div className="bg-red-500/5 border border-red-500/10 hover:border-red-500/20 rounded-2xl p-6 hover:bg-red-500/10 transition duration-300">
                          <h4 className="text-sm font-bold text-red-300 uppercase tracking-widest mb-4 border-b border-red-500/10 pb-2 flex items-center gap-2">
                            <span>⚠️</span> Risk Factors
                          </h4>
                          <ul className="space-y-3">
                            {selectedStock.risks.map((risk: string, idx: number) => (
                              <li key={idx} className="text-sm text-slate-300 flex items-start gap-3">
                                <span className="text-red-400 shrink-0 mt-0.5 text-lg leading-none">!</span>
                                <span>{risk}</span>
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Mode and Broker Utama Card */}
                  {(selectedStock.weight_mode || selectedStock.broker_utama) && (
                    <div className="bg-white/[0.03] backdrop-blur-md border-l-4 border-l-amber-500 border-y border-r border-white/5 rounded-2xl p-5 mt-8 mb-6 hover:bg-white/[0.05] transition duration-300">
                      <div className="flex flex-wrap items-center justify-between gap-4">
                        <div className="flex items-center gap-2 text-white font-bold">
                          <span className="text-amber-500">⚡</span>
                          <span className="text-slate-300">Mode:</span>
                          <span className="text-amber-400 font-mono bg-amber-500/10 px-2.5 py-0.5 rounded border border-amber-500/20 text-sm">
                            {selectedStock.weight_mode || 'default'}
                          </span>
                        </div>
                      </div>
                      {selectedStock.broker_utama && (
                        <div className="mt-3 text-slate-300 text-sm leading-relaxed border-t border-white/5 pt-3">
                          <span className="font-bold text-slate-200 mr-2">Broker Utama:</span>
                          <span className="font-mono text-slate-300">{selectedStock.broker_utama}</span>
                        </div>
                      )}
                    </div>
                  )}

                  {/* Collapsible Broker Accumulation Details */}
                  {selectedStock.broker_true_cost && selectedStock.broker_true_cost.w1m && (
                    <div className="bg-white/[0.03] backdrop-blur-md border border-white/5 rounded-3xl p-6 mb-8 hover:bg-white/5 transition duration-300">
                      {/* Collapsible Header */}
                      <button 
                        onClick={() => setShowTrueCostDetails(!showTrueCostDetails)}
                        className="w-full flex items-center justify-between py-2 text-slate-200 hover:text-white transition font-bold text-base"
                      >
                        <span className="flex items-center gap-2">
                          <span className="text-indigo-400">🏛️</span> True Cost Broker Akumulasi
                        </span>
                        <span>{showTrueCostDetails ? '▲' : '▼'}</span>
                      </button>

                      {/* Collapsible Body */}
                      {showTrueCostDetails && (
                        <div className="mt-4 animate-fade-in">
                          <div className="overflow-x-auto rounded-xl border border-white/5 bg-[#030712]/40">
                            <table className="w-full text-left border-collapse">
                              <thead>
                                <tr className="border-b border-white/5 text-[11px] font-bold uppercase tracking-wider text-slate-400 bg-white/5">
                                  <th className="py-3 px-4">Broker</th>
                                  <th className="py-3 px-4">True Cost</th>
                                  <th className="py-3 px-4">Total Buy Lot</th>
                                  <th className="py-3 px-4">Total Buy Value</th>
                                  <th className="py-3 px-4">Harga vs Cost</th>
                                  <th className="py-3 px-4 text-right">Active</th>
                                </tr>
                              </thead>
                              <tbody className="divide-y divide-white/5 text-sm font-mono text-slate-300">
                                {selectedStock.broker_true_cost.w1m.map((row: any, idx: number) => (
                                  <tr key={idx} className="hover:bg-white/5 transition">
                                    <td className="py-3 px-4 font-bold text-white flex items-center gap-2">
                                      {row.broker}
                                    </td>
                                    <td className="py-3 px-4 text-white">Rp {(row.true_cost || 0).toLocaleString('id-ID')}</td>
                                    <td className="py-3 px-4">{formatLot(row.total_buy_lot)}</td>
                                    <td className="py-3 px-4">{formatValue(row.total_buy_value)}</td>
                                    <td className={`py-3 px-4 font-bold ${row.distance_pct >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                                      {formatPercentage(row.distance_pct)}
                                    </td>
                                    <td className="py-3 px-4 text-right">{row.active_days || '-'}</td>
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          </div>
                          <p className="text-[10px] text-slate-500 mt-3 font-sans">
                            Menampilkan 1 bulan; 7 hari tersedia di halaman Bandarmologi.
                          </p>
                        </div>
                      )}
                    </div>
                  )}

                  {/* Collapsible Broker Distribution Details */}
                  {selectedStock.broker_distributors && selectedStock.broker_distributors.w1m && (
                    <div className="bg-white/[0.03] backdrop-blur-md border border-white/5 rounded-3xl p-6 mb-8 hover:bg-white/5 transition duration-300">
                      {/* Collapsible Header */}
                      <button 
                        onClick={() => setShowDistDetails(!showDistDetails)}
                        className="w-full flex items-center justify-between py-2 text-slate-200 hover:text-white transition font-bold text-base"
                      >
                        <span className="flex items-center gap-2">
                          <span className="text-red-400">📉</span> Avg Sell Distribusi
                        </span>
                        <span>{showDistDetails ? '▲' : '▼'}</span>
                      </button>

                      {/* Collapsible Body */}
                      {showDistDetails && (
                        <div className="mt-4 animate-fade-in">
                          <div className="overflow-x-auto rounded-xl border border-white/5 bg-[#030712]/40">
                            <table className="w-full text-left border-collapse">
                              <thead>
                                <tr className="border-b border-white/5 text-[11px] font-bold uppercase tracking-wider text-slate-400 bg-white/5">
                                  <th className="py-3 px-4">Broker</th>
                                  <th className="py-3 px-4">Avg Sell</th>
                                  <th className="py-3 px-4">Total Sell Lot</th>
                                  <th className="py-3 px-4">Total Sell Value</th>
                                  <th className="py-3 px-4">Harga vs Avg</th>
                                  <th className="py-3 px-4 text-right">Active</th>
                                </tr>
                              </thead>
                              <tbody className="divide-y divide-white/5 text-sm font-mono text-slate-300">
                                {selectedStock.broker_distributors.w1m.map((row: any, idx: number) => (
                                  <tr key={idx} className="hover:bg-white/5 transition">
                                    <td className="py-3 px-4 font-bold text-white flex items-center gap-2">
                                      {row.broker}
                                    </td>
                                    <td className="py-3 px-4 text-white">Rp {(row.avg_sell || 0).toLocaleString('id-ID')}</td>
                                    <td className="py-3 px-4">{formatLot(row.total_sell_lot)}</td>
                                    <td className="py-3 px-4">{formatValue(row.total_sell_value)}</td>
                                    <td className={`py-3 px-4 font-bold ${row.distance_pct >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                                      {formatPercentage(row.distance_pct)}
                                    </td>
                                    <td className="py-3 px-4 text-right">{row.active_days || '-'}</td>
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          </div>
                          <p className="text-[10px] text-slate-505 mt-3 font-sans">
                            Menampilkan 1 bulan; 7 hari tersedia di halaman Bandarmologi.
                          </p>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </div>
            </div>
          )} {/* END TOP PICKS TAB */}

        {activeTab === 'bandarmologi' && (
          <div className="space-y-6 animate-fade-in">
            {/* Title */}
            <div>
              <h2 className="text-3xl font-bold text-white mb-2">Analisis <span className="text-indigo-400">Bandarmologi</span></h2>
              <p className="text-slate-400">Peta aliran dana institusi besar, rata-rata harga beli/jual bandar, dan status entry zone.</p>
            </div>

            {/* Ticker Selector */}
            <div className="flex flex-wrap items-center justify-between gap-4 bg-white/5 p-4 rounded-2xl border border-white/5 mb-6">
              <div className="flex items-center gap-3">
                <span className="text-slate-300 font-bold text-sm">Pilih Saham:</span>
                <select 
                  value={bandarmologiTicker}
                  onChange={(e) => setBandarmologiTicker(e.target.value)}
                  className="bg-[#030712] text-white border border-white/10 rounded-xl px-4 py-2 text-sm focus:outline-none focus:border-indigo-500 font-mono font-bold"
                >
                  {bandarmologiData?.all_tickers?.map((t: string) => (
                    <option key={t} value={t}>{t}</option>
                  )) || (
                    ['MEDC', 'ANTM', 'PGAS'].map((t: string) => (
                      <option key={t} value={t}>{t}</option>
                    ))
                  )}
                </select>
                {bandarLoading && <span className="text-xs text-indigo-400 animate-pulse font-bold">Memuat...</span>}
              </div>

              {/* Timeframe Selector tabs */}
              <div className="flex bg-[#030712] p-1 rounded-xl border border-white/10">
                <button 
                  onClick={() => setBandarTimeframe("1m")}
                  className={`px-4 py-1.5 rounded-lg transition text-xs font-bold ${bandarTimeframe === '1m' ? 'bg-indigo-500 text-white shadow-lg' : 'text-slate-400 hover:text-white'}`}
                >
                  1 Bulan (30 Hari)
                </button>
                <button 
                  onClick={() => setBandarTimeframe("7d")}
                  className={`px-4 py-1.5 rounded-lg transition text-xs font-bold ${bandarTimeframe === '7d' ? 'bg-indigo-500 text-white shadow-lg' : 'text-slate-400 hover:text-white'}`}
                >
                  7 Hari
                </button>
              </div>
            </div>

            {/* Top Metrics Cards */}
            {bandarmologiData && bandarmologiData.summary && (
              <div className="grid grid-cols-2 md:grid-cols-4 gap-6 bg-white/[0.03] backdrop-blur-md border border-white/5 rounded-3xl p-6 mb-8 hover:bg-white/[0.05] transition duration-300">
                {/* Signal */}
                <div>
                  <p className="text-xs text-slate-400 font-bold uppercase tracking-wider mb-2">Signal</p>
                  <p className={`text-2xl md:text-3xl font-black uppercase tracking-tight ${
                    bandarmologiData.summary.signal === 'BUY' || bandarmologiData.summary.signal?.includes('ACCUMULATION') ? 'text-emerald-400' :
                    bandarmologiData.summary.signal === 'SELL' || bandarmologiData.summary.signal?.includes('DISTRIBUTION') ? 'text-red-400' :
                    'text-indigo-400'
                  }`}>
                    {bandarmologiData.summary.signal?.replace('_', ' ') || 'HOLD'}
                  </p>
                </div>

                {/* Score */}
                <div>
                  <p className="text-xs text-slate-400 font-bold uppercase tracking-wider mb-2">Score</p>
                  <p className="text-2xl md:text-3xl font-black text-white font-mono">
                    {bandarmologiData.score !== undefined ? `${bandarmologiData.score}/10` : '-'}
                  </p>
                </div>

                {/* Current Price */}
                <div>
                  <p className="text-xs text-slate-400 font-bold uppercase tracking-wider mb-2">Current Price</p>
                  <p className="text-2xl md:text-3xl font-black text-white font-mono">
                    {bandarmologiData.price_analysis?.current_price ? `Rp ${bandarmologiData.price_analysis.current_price.toLocaleString('id-ID')}` : '-'}
                  </p>
                </div>

                {/* Entry Status */}
                <div>
                  <p className="text-xs text-slate-400 font-bold uppercase tracking-wider mb-2">Entry Status</p>
                  <div className="flex items-center gap-2.5">
                    <span className={`inline-block w-4 h-4 rounded-full ${
                      bandarmologiData.price_analysis?.entry_status?.toLowerCase().includes('ideal') ? 'bg-blue-400 shadow-[0_0_10px_rgba(96,165,250,0.5)]' :
                      bandarmologiData.price_analysis?.entry_status?.toLowerCase().includes('acceptable') ? 'bg-emerald-400 shadow-[0_0_10px_rgba(52,211,153,0.5)]' :
                      bandarmologiData.price_analysis?.entry_status?.toLowerCase().includes('caution') ? 'bg-amber-400 shadow-[0_0_10px_rgba(251,191,36,0.5)]' :
                      bandarmologiData.price_analysis?.entry_status?.toLowerCase().includes('avoid') ? 'bg-red-400 shadow-[0_0_10px_rgba(248,113,113,0.5)]' :
                      'bg-slate-400'
                    }`}></span>
                    <span className="text-xl md:text-2xl font-black text-white uppercase tracking-wide">
                      {bandarmologiData.price_analysis?.entry_status?.replace(/[^a-zA-Z]/g, '').trim() || 'N/A'}
                    </span>
                  </div>
                </div>
              </div>
            )}

            {/* Entry Analysis Card */}
            {bandarmologiData && bandarmologiData.price_analysis && (
              <div className="bg-white/[0.03] backdrop-blur-md border border-white/5 rounded-3xl p-6 mb-8 hover:bg-white/[0.05] transition duration-300">
                <h3 className="text-lg font-bold text-white mb-6 flex items-center gap-2">
                  <span className="text-yellow-400">💡</span> Entry Analysis
                </h3>
                
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
                  {/* Avg 7 Hari */}
                  <div>
                    <p className="text-xs text-slate-400 font-bold uppercase tracking-wider mb-2">Avg 7 Hari</p>
                    <p className="text-2xl font-black text-white font-mono">
                      {bandarmologiData.price_analysis.bandar_avg_7d ? `Rp ${bandarmologiData.price_analysis.bandar_avg_7d.toLocaleString('id-ID')}` : '-'}
                    </p>
                  </div>

                  {/* Avg 1 Bulan (True Cost) */}
                  <div>
                    <p className="text-xs text-slate-400 font-bold uppercase tracking-wider mb-2">Avg 1 Bulan (True Cost)</p>
                    <p className="text-2xl font-black text-white font-mono">
                      {bandarmologiData.price_analysis.bandar_avg_1m ? `Rp ${bandarmologiData.price_analysis.bandar_avg_1m.toLocaleString('id-ID')}` : '-'}
                    </p>
                  </div>

                  {/* Harga Sekarang */}
                  <div>
                    <p className="text-xs text-slate-400 font-bold uppercase tracking-wider mb-2">Harga Sekarang</p>
                    <p className="text-2xl font-black text-white font-mono">
                      {bandarmologiData.price_analysis.current_price ? `Rp ${bandarmologiData.price_analysis.current_price.toLocaleString('id-ID')}` : '-'}
                    </p>
                  </div>
                </div>

                {/* Distance metrics */}
                <div className="space-y-2 mb-6 font-mono text-sm text-slate-300">
                  <div className="flex items-center gap-2">
                    <span>🏷️</span>
                    <span>Jarak dari avg 7H:</span>
                    <span className={`font-bold ${bandarmologiData.price_analysis.distance_from_7d?.includes('-') ? 'text-emerald-400' : 'text-red-400'}`}>
                      {bandarmologiData.price_analysis.distance_from_7d || 'N/A'}
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span>🏷️</span>
                    <span>Jarak dari avg 1M:</span>
                    <span className={`font-bold ${bandarmologiData.price_analysis.distance_from_1m?.includes('-') ? 'text-emerald-400' : 'text-red-400'}`}>
                      {bandarmologiData.price_analysis.distance_from_1m || 'N/A'}
                    </span>
                  </div>
                </div>

                {/* Entry status boxes */}
                <div className="space-y-3 font-sans text-sm font-semibold">
                  {bandarmologiData.price_analysis.ideal_entry_zone && (
                    <div className="flex items-center gap-2.5 px-4 py-3 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-300">
                      <span>🎯</span>
                      <span>Entry Ideal: <span className="font-mono font-bold text-white">{bandarmologiData.price_analysis.ideal_entry_zone}</span> | Max Entry: <span className="font-mono font-bold text-white">{bandarmologiData.price_analysis.max_entry}</span></span>
                    </div>
                  )}
                  {bandarmologiData.price_analysis.entry_status && (
                    <div className={`flex items-center gap-2.5 px-4 py-3 rounded-xl border ${
                      bandarmologiData.price_analysis.entry_status?.toLowerCase().includes('ideal') || bandarmologiData.price_analysis.entry_status?.toLowerCase().includes('acceptable')
                        ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-300'
                        : 'bg-red-500/10 border-red-500/20 text-red-300'
                    }`}>
                      <span>{bandarmologiData.price_analysis.entry_status?.split(' ')[0]}</span>
                      <span>
                        <span className="font-bold">{bandarmologiData.price_analysis.entry_status?.replace(/[^a-zA-Z]/g, '').trim()}</span>
                        {' — '}
                        {bandarmologiData.price_analysis.entry_label}
                      </span>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Window Summary Info Bar */}
            {bandarmologiData && (() => {
              const summary = bandarTimeframe === '1m' ? bandarmologiData.window_1m_summary : bandarmologiData.window_7d_summary;
              if (!summary || !summary.period) return null;
              return (
                <div className="bg-white/[0.03] border border-white/5 rounded-2xl p-5 mb-6 flex flex-wrap items-center justify-between gap-6 hover:bg-white/[0.05] transition duration-300 font-mono text-sm">
                  <div className="flex items-center gap-2">
                    <span className="text-slate-400 font-sans">Period:</span>
                    <span className="text-white font-bold">{summary.period}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-slate-400 font-sans">Bandar Signal:</span>
                    <span className={`font-bold ${
                      summary.bandar_signal?.toLowerCase().includes('accumulation') ? 'text-emerald-400' :
                      summary.bandar_signal?.toLowerCase().includes('distribution') ? 'text-red-400' :
                      'text-slate-300'
                    }`}>
                      {summary.bandar_signal} {summary.assessment && summary.assessment !== summary.bandar_signal ? `— ${summary.assessment}` : ''}
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-slate-400 font-sans">Net Lot:</span>
                    <span className={`font-bold ${summary.net_lot >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                      {summary.net_lot !== undefined ? (summary.net_lot >= 0 ? '+' : '') + summary.net_lot.toLocaleString('id-ID') : '0'}
                    </span>
                    <span className="text-slate-505">|</span>
                    <span className="text-slate-400 font-sans">Net Value:</span>
                    <span className={`font-bold ${summary.net_value >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                      {summary.net_value !== undefined ? (summary.net_value >= 0 ? '+' : '') + formatValue(summary.net_value) : '0'}
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-slate-400 font-sans">Buyer/Seller:</span>
                    <span className="text-white font-bold">{summary.total_buyer}/{summary.total_seller}</span>
                  </div>
                </div>
              );
            })()}

            {/* Tables (Side-by-Side) */}
            {bandarmologiData && (
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                {/* Table Accumulation */}
                <div className="bg-emerald-500/[0.02] hover:bg-emerald-500/[0.04] border border-emerald-500/20 rounded-2xl p-6 transition duration-300">
                  <h3 className="text-lg font-bold text-emerald-400 mb-4 flex items-center gap-2">
                    <span>🏛️</span> Top {(bandarTimeframe === '1m' ? bandarmologiData.accumulators_1m : bandarmologiData.accumulators_7d).length} Broker Akumulasi ({bandarTimeframe.toUpperCase()})
                  </h3>
                  <div className="overflow-x-auto rounded-xl border border-emerald-500/10 bg-[#030712]/40">
                    <table className="w-full text-left border-collapse text-sm">
                      <thead>
                        <tr className="border-b border-emerald-500/10 text-[11px] font-bold uppercase tracking-wider text-emerald-300/70 bg-emerald-950/10">
                          <th className="py-3 px-4 whitespace-nowrap">Broker</th>
                          <th className="py-3 px-4 whitespace-nowrap">Avg Price</th>
                          <th className="py-3 px-4 whitespace-nowrap">Volume (Lot)</th>
                          <th className="py-3 px-4 whitespace-nowrap">Value</th>
                          <th className="py-3 px-4 whitespace-nowrap">Keaktifan</th>
                          <th className="py-3 px-4 whitespace-nowrap">Harga vs Cost</th>
                          <th className="py-3 px-4 text-right whitespace-nowrap">Status</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-emerald-500/5 text-slate-300 font-mono">
                        {(bandarTimeframe === '1m' ? bandarmologiData.accumulators_1m : bandarmologiData.accumulators_7d).map((row: any, idx: number) => (
                          <tr key={idx} className="hover:bg-emerald-500/5 transition">
                            <td className="py-3 px-4 font-bold text-white whitespace-nowrap">
                              {row.broker}
                            </td>
                            <td className="py-3 px-4 whitespace-nowrap">Rp {row.avg_price.toLocaleString('id-ID')}</td>
                            <td className="py-3 px-4 whitespace-nowrap">{formatLot(row.total_buy_lot)}</td>
                            <td className="py-3 px-4 whitespace-nowrap">{formatValue(row.total_buy_value)}</td>
                            <td className="py-3 px-4 text-xs text-slate-400 whitespace-nowrap">{row.active_days}</td>
                            <td className={`py-3 px-4 font-bold whitespace-nowrap ${
                              row.distance_pct === null ? 'text-slate-400' :
                              row.distance_pct >= 0 ? 'text-emerald-400' : 'text-red-400'
                            }`}>
                              {row.distance_pct !== null ? `${row.distance_pct >= 0 ? '+' : ''}${row.distance_pct.toFixed(2)}%` : '-'}
                            </td>
                            <td className="py-3 px-4 text-right text-xs text-slate-300 font-sans whitespace-nowrap">
                              {row.status || '-'}
                            </td>
                          </tr>
                        ))}
                        {(bandarTimeframe === '1m' ? bandarmologiData.accumulators_1m : bandarmologiData.accumulators_7d).length === 0 && (
                          <tr>
                            <td colSpan={7} className="py-10 text-center text-slate-505 font-sans">Tidak ada data akumulasi terdeteksi.</td>
                          </tr>
                        )}
                      </tbody>
                    </table>
                  </div>
                </div>

                {/* Table Distribution */}
                <div className="bg-red-500/[0.02] hover:bg-red-500/[0.04] border border-red-500/20 rounded-2xl p-6 transition duration-300">
                  <h3 className="text-lg font-bold text-red-400 mb-4 flex items-center gap-2">
                    <span>📉</span> Top {(bandarTimeframe === '1m' ? bandarmologiData.distributors_1m : bandarmologiData.distributors_7d).length} Broker Distribusi ({bandarTimeframe.toUpperCase()})
                  </h3>
                  <div className="overflow-x-auto rounded-xl border border-red-500/10 bg-[#030712]/40">
                    <table className="w-full text-left border-collapse text-sm">
                      <thead>
                        <tr className="border-b border-red-500/10 text-[11px] font-bold uppercase tracking-wider text-red-300/70 bg-red-950/10">
                          <th className="py-3 px-4 whitespace-nowrap">Broker</th>
                          <th className="py-3 px-4 whitespace-nowrap">Avg Sell</th>
                          <th className="py-3 px-4 whitespace-nowrap">Volume (Lot)</th>
                          <th className="py-3 px-4 whitespace-nowrap">Value</th>
                          <th className="py-3 px-4 whitespace-nowrap">Keaktifan</th>
                          <th className="py-3 px-4 whitespace-nowrap">Harga vs Cost</th>
                          <th className="py-3 px-4 text-right whitespace-nowrap">Status</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-red-500/5 text-slate-300 font-mono">
                        {(bandarTimeframe === '1m' ? bandarmologiData.distributors_1m : bandarmologiData.distributors_7d).map((row: any, idx: number) => (
                          <tr key={idx} className="hover:bg-red-500/5 transition">
                            <td className="py-3 px-4 font-bold text-white whitespace-nowrap">
                              {row.broker}
                            </td>
                            <td className="py-3 px-4 whitespace-nowrap">Rp {row.avg_price.toLocaleString('id-ID')}</td>
                            <td className="py-3 px-4 whitespace-nowrap">{formatLot(row.total_sell_lot)}</td>
                            <td className="py-3 px-4 whitespace-nowrap">{formatValue(row.total_sell_value)}</td>
                            <td className="py-3 px-4 text-xs text-slate-400 whitespace-nowrap">{row.active_days}</td>
                            <td className={`py-3 px-4 font-bold whitespace-nowrap ${
                              row.distance_pct === null ? 'text-slate-400' :
                              row.distance_pct >= 0 ? 'text-emerald-400' : 'text-red-400'
                            }`}>
                              {row.distance_pct !== null ? `${row.distance_pct >= 0 ? '+' : ''}${row.distance_pct.toFixed(2)}%` : '-'}
                            </td>
                            <td className="py-3 px-4 text-right text-xs text-slate-300 font-sans whitespace-nowrap">
                              {row.status || '-'}
                            </td>
                          </tr>
                        ))}
                        {(bandarTimeframe === '1m' ? bandarmologiData.distributors_1m : bandarmologiData.distributors_7d).length === 0 && (
                          <tr>
                            <td colSpan={7} className="py-10 text-center text-slate-505 font-sans">Tidak ada data distribusi terdeteksi.</td>
                          </tr>
                        )}
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {activeTab === 'history' && (
          <div className="space-y-6 animate-fade-in">
            <div>
              <h2 className="text-3xl font-bold text-white mb-2">Track Record <span className="text-indigo-400">AI Sinyal</span></h2>
              <p className="text-slate-400">Laporan transparan performa historis agen AI Hamboo pada seluruh transaksi.</p>
            </div>
            
            <div className="bg-white/[0.03] backdrop-blur-md border border-white/5 rounded-3xl p-6">
              <div className="overflow-x-auto">
                <table className="w-full text-sm text-left text-slate-300">
                  <thead className="text-xs text-slate-400 uppercase bg-white/5 border-b border-white/5">
                    <tr>
                      <th className="px-4 py-4 rounded-tl-lg">Tanggal</th>
                      <th className="px-4 py-4">Saham</th>
                      <th className="px-4 py-4">Sinyal Awal</th>
                      <th className="px-4 py-4 text-center">Status</th>
                      <th className="px-4 py-4 text-right rounded-tr-lg">Profit / Loss (%)</th>
                    </tr>
                  </thead>
                  <tbody>
                    {historyData.map((h, i) => (
                      <tr key={i} className="border-b border-white/5 hover:bg-white/5 transition duration-150">
                        <td className="px-4 py-4">{h.date}</td>
                        <td className="px-4 py-4 font-bold text-white text-lg">{h.ticker}</td>
                        <td className="px-4 py-4">
                          <span className={`px-3 py-1 rounded-full text-xs font-bold border ${h.signal === 'BUY' ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' : h.signal === 'SELL' ? 'bg-red-500/10 text-red-400 border-red-500/20' : 'bg-slate-500/10 text-slate-400 border-slate-500/20'}`}>
                            {h.signal}
                          </span>
                        </td>
                        <td className="px-4 py-4 text-center">
                          <span className={`px-3 py-1 rounded-lg text-xs font-bold ${h.result === 'PROFIT' ? 'bg-emerald-500 text-white shadow-[0_0_10px_rgba(16,185,129,0.3)]' : h.result === 'LOSS' ? 'bg-red-500 text-white shadow-[0_0_10px_rgba(239,68,68,0.3)]' : 'bg-slate-700 text-slate-300'}`}>
                            {h.result}
                          </span>
                        </td>
                        <td className={`px-4 py-4 text-right font-mono font-bold text-lg ${h.return_pct > 0 ? 'text-emerald-400' : h.return_pct < 0 ? 'text-red-400' : 'text-slate-400'}`}>
                          {h.return_pct > 0 ? '+' : ''}{h.return_pct}%
                        </td>
                      </tr>
                    ))}
                    {historyData.length === 0 && (
                      <tr>
                        <td colSpan={5} className="px-4 py-10 text-center text-slate-500">Belum ada riwayat trading yang tercatat.</td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )} {/* END HISTORY TAB */}

        {/* TAB: SETTINGS */}
        {activeTab === 'settings' && (
          <div className="space-y-6 animate-fade-in max-w-2xl mx-auto">
            <div>
              <h2 className="text-3xl font-bold text-white mb-2">Preferences <span className="text-indigo-400">& Settings</span></h2>
              <p className="text-slate-400">Atur preferensi akun Pro dan konfigurasi model AI-mu.</p>
            </div>
            
            <div className="bg-white/[0.03] backdrop-blur-md border border-white/5 rounded-3xl p-8 space-y-8">
              <div className="space-y-4">
                <h4 className="text-lg font-bold text-white border-b border-white/10 pb-2">Akun Saya</h4>
                <div className="flex justify-between items-center bg-white/5 p-4 rounded-xl border border-white/5">
                  <div>
                    <p className="font-bold text-white">Status Tier</p>
                    <p className="text-sm text-slate-400">Mode saat ini yang sedang aktif</p>
                  </div>
                  <div className="flex bg-[#030712] p-1 rounded-xl border border-white/10">
                    <button className={`px-4 py-2 rounded-lg transition text-sm font-bold ${!isPro ? 'bg-indigo-500 text-white shadow-lg' : 'text-slate-400 hover:text-white'}`} onClick={() => setIsPro(false)}>Free Tier</button>
                    <button className={`px-4 py-2 rounded-lg transition text-sm font-bold flex items-center gap-2 ${isPro ? 'bg-gradient-to-r from-indigo-500 to-purple-500 text-white shadow-lg' : 'text-slate-400 hover:text-white'}`} onClick={() => setIsPro(true)}>
                      Pro Tier ✨
                    </button>
                  </div>
                </div>
              </div>

              <div className="space-y-4">
                <h4 className="text-lg font-bold text-white border-b border-white/10 pb-2">Konfigurasi Agen AI</h4>
                <div className="space-y-3">
                  <div className="flex justify-between items-center p-2">
                    <p className="text-slate-300">Model Prediksi Analisa</p>
                    <span className="px-3 py-1 bg-white/10 rounded-lg text-xs font-mono text-indigo-300">OpenRouter (Debate)</span>
                  </div>
                  <div className="flex justify-between items-center p-2">
                    <p className="text-slate-300">Agresivitas Trading</p>
                    <span className="px-3 py-1 bg-white/10 rounded-lg text-xs font-mono text-indigo-300">MODERATE (Defensive)</span>
                  </div>
                  <div className="flex justify-between items-center p-2">
                    <p className="text-slate-300">Notifikasi WhatsApp</p>
                    <button className="w-12 h-6 bg-emerald-500 rounded-full relative transition"><span className="absolute right-1 top-1 w-4 h-4 bg-white rounded-full"></span></button>
                  </div>
                </div>
              </div>

              <div className="pt-4 border-t border-white/10 flex justify-end">
                <button className="bg-white hover:bg-slate-200 text-black font-bold py-2 px-6 rounded-xl transition shadow-[0_0_15px_rgba(255,255,255,0.2)]">
                  Simpan Perubahan
                </button>
              </div>
            </div>
          </div>
        )} {/* END SETTINGS TAB */}

      </main>
    </div>
  );
}
