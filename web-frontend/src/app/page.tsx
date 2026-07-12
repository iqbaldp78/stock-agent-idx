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
  const [toasts, setToasts] = useState<any[]>([]);
  const [batchId, setBatchId] = useState("");
  const [runDate, setRunDate] = useState("");

  const showToast = (message: string, type: 'success' | 'error' | 'info' = 'success') => {
    const id = Date.now();
    setToasts(prev => [...prev, { id, message, type }]);
    setTimeout(() => {
      setToasts(prev => prev.filter(t => t.id !== id));
    }, 4500);
  };
  const [stats, setStats] = useState({ market_outlook: "Loading", win_rate: 0, profit_factor: 0 });
  const [wallet, setWallet] = useState({ cash: 0, invested: 0, pnl: 0 });
  const [holdings, setHoldings] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [tradeStatus, setTradeStatus] = useState("");
  const [isPro, setIsPro] = useState(true); // Hardcode VIP Pro

  const [activeTab, setActiveTab] = useState("dashboard"); // 'dashboard' | 'top-picks' | 'bandarmologi' | 'ihsg' | 'history' | 'settings'
  const [historyData, setHistoryData] = useState<any[]>([]);
  const [selectedStock, setSelectedStock] = useState<any | null>(null);

  // --- Portfolio Management State ---
  const [portfolioTab, setPortfolioTab] = useState<"holdings" | "dca" | "history" | "performance" | "ai">("holdings");
  const [portfolioHoldings, setPortfolioHoldings] = useState<any[]>([]);
  const [portfolioSummary, setPortfolioSummary] = useState<any>({
    total_invested: 0,
    total_current_value: 0,
    total_pnl: 0,
    total_pnl_pct: 0,
    best_performer: null,
    best_pnl_pct: 0
  });
  const [portfolioLoading, setPortfolioLoading] = useState(false);
  const [dcaStrategies, setDcaStrategies] = useState<any[]>([]);
  const [portfolioTxns, setPortfolioTxns] = useState<any[]>([]);
  
  // Forms & Inputs: Holdings Tab
  const [newHoldingTicker, setNewHoldingTicker] = useState("");
  const [newHoldingLots, setNewHoldingLots] = useState(10);
  const [newHoldingAvg, setNewHoldingAvg] = useState(1000);
  const [newHoldingNotes, setNewHoldingNotes] = useState("");
  
  const [recordTxnType, setRecordTxnType] = useState<"BUY" | "SELL">("BUY");
  const [recordTxnTicker, setRecordTxnTicker] = useState("");
  const [recordTxnLots, setRecordTxnLots] = useState(1);
  const [recordTxnPrice, setRecordTxnPrice] = useState(1000);
  const [recordTxnNotes, setRecordTxnNotes] = useState("");
  const [buyPreview, setBuyPreview] = useState<any>(null);
  
  // Forms & Inputs: DCA Tab
  const [dcaMode, setDcaMode] = useState<"signal" | "manual">("signal");
  const [dcaBudget, setDcaBudget] = useState(2000000);
  const [dcaCount, setDcaCount] = useState(3);
  const [selectedSignalId, setSelectedSignalId] = useState<number | null>(null);
  
  const [manualDcaTicker, setManualDcaTicker] = useState("");
  const [manualEntryLow, setManualEntryLow] = useState(3000);
  const [manualEntryHigh, setManualEntryHigh] = useState(3200);
  const [manualMaxEntry, setManualMaxEntry] = useState(3400);
  
  const [previewDcaLevels, setPreviewDcaLevels] = useState<any[]>([]);
  const [dcaLevelsLoading, setDcaLevelsLoading] = useState(false);
  
  const [timingTicker, setTimingTicker] = useState("");
  const [timingResult, setTimingResult] = useState<any>(null);
  const [timingLoading, setTimingLoading] = useState(false);
  
  // History Tab Filters
  const [txnFilterTicker, setTxnFilterTicker] = useState("ALL");
  const [txnFilterType, setTxnFilterType] = useState("ALL");
  
  // AI Tab State
  const [aiMonthlyBudget, setAiMonthlyBudget] = useState(2000000);
  const [aiAnalysisResult, setAiAnalysisResult] = useState<any>(null);
  const [aiAnalysisLoading, setAiAnalysisLoading] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [showFairValueDetails, setShowFairValueDetails] = useState(false);
  const [showTrueCostDetails, setShowTrueCostDetails] = useState(true);
  const [showDistDetails, setShowDistDetails] = useState(true);

  const [bandarmologiTicker, setBandarmologiTicker] = useState("MEDC");
  const [bandarmologiData, setBandarmologiData] = useState<any | null>(null);
  const [bandarLoading, setBandarLoading] = useState(false);
  const [bandarTimeframe, setBandarTimeframe] = useState("1m"); // '7d' | '1m'

  const [ihsgData, setIhsgData] = useState<any>(null);
  const [ihsgLoading, setIhsgLoading] = useState(false);
  const [ihsgError, setIhsgError] = useState("");

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

  const fetchIhsgData = async () => {
    setIhsgLoading(true);
    setIhsgError("");
    try {
      const res = await fetch("/api/ihsg");
      if (!res.ok) throw new Error("Gagal mengambil data IHSG");
      const data = await res.json();
      setIhsgData(data);
    } catch (err: any) {
      setIhsgError(err.message || "Kesalahan jaringan");
    } finally {
      setIhsgLoading(false);
    }
  };

  const [tradingData, setTradingData] = useState<any>(null);
  const [equityData, setEquityData] = useState<any>(null);
  const [tradingLoading, setTradingLoading] = useState(false);
  const [tradingError, setTradingError] = useState("");

  const [buyTicker, setBuyTicker] = useState("MEDC");
  const [buyLot, setBuyLot] = useState(10);
  const [buyPrice, setBuyPrice] = useState(1150);
  const [buyTp, setBuyTp] = useState(0);
  const [buySl, setBuySl] = useState(0);
  const [buySignalId, setBuySignalId] = useState<number | null>(null);

  const [topupAmount, setTopupAmount] = useState(100000000);
  const [showTopupModal, setShowTopupModal] = useState(false);

  const fetchTradingData = async () => {
    setTradingLoading(true);
    setTradingError("");
    try {
      const res = await fetch("/api/trading/summary");
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
      const res = await fetch("/api/trading/equity-history");
      if (res.ok) {
        const data = await res.json();
        setEquityData(data);
      }
    } catch (err) {
      console.error("Gagal mengambil riwayat ekuitas:", err);
    }
  };

  const handleTopup = async (amount: number) => {
    try {
      const res = await fetch("/api/trading/topup", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ amount })
      });
      const data = await res.json();
      if (data.status === "success") {
        showToast(data.message, 'success');
        fetchTradingData();
        fetchEquityData();
      } else {
        showToast(data.message || "Gagal melakukan topup", 'error');
      }
    } catch (err) {
      showToast("Kesalahan jaringan saat melakukan topup", 'error');
    }
  };

  const handleResetPortfolio = async () => {
    if (!confirm("Apakah Anda yakin ingin mereset seluruh posisi dan transaksi virtual?")) return;
    try {
      const res = await fetch("/api/trading/reset", { method: "POST" });
      const data = await res.json();
      showToast(data.message || "Portfolio berhasil direset", 'success');
      fetchTradingData();
      fetchEquityData();
    } catch (err) {
      showToast("Kesalahan jaringan saat mereset portfolio", 'error');
    }
  };

  const handleBuy = async (ticker: string, lot: number, price: number, signalId: number | null, tp1: number, stopLoss: number) => {
    try {
      const res = await fetch("/api/trading/buy", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ticker: ticker.toUpperCase(),
          lot,
          price,
          signal_id: signalId,
          tp1: tp1 > 0 ? tp1 : null,
          stop_loss: stopLoss > 0 ? stopLoss : null
        })
      });
      const data = await res.json();
      if (data.status === "error") {
        showToast(data.message, 'error');
      } else {
        showToast(data.message || "Order berhasil ditempatkan", 'success');
        fetchTradingData();
        fetchEquityData();
      }
    } catch (err) {
      showToast("Kesalahan jaringan saat melakukan pembelian", 'error');
    }
  };

  const handleSell = async (tradeId: number, price: number) => {
    try {
      const res = await fetch("/api/trading/sell", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ trade_id: tradeId, price, reason: "MANUAL" })
      });
      const data = await res.json();
      if (data.status === "success") {
        showToast(`Berhasil menjual: ${data.message || ''}`, 'success');
        fetchTradingData();
        fetchEquityData();
      } else {
        showToast(data.message || "Gagal melakukan penjualan", 'error');
      }
    } catch (err) {
      showToast("Kesalahan jaringan saat melakukan penjualan", 'error');
    }
  };

  const handleCancelPending = async (tradeId: number) => {
    try {
      const res = await fetch("/api/trading/cancel-pending", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ trade_id: tradeId })
      });
      const data = await res.json();
      if (data.status === "success") {
        showToast(data.message || "Order berhasil dibatalkan", 'success');
        fetchTradingData();
        fetchEquityData();
      } else {
        showToast(data.message || "Gagal membatalkan order", 'error');
      }
    } catch (err) {
      showToast("Kesalahan jaringan saat membatalkan order", 'error');
    }
  };

  const handleAutoInvestAll = async () => {
    try {
      const res = await fetch("/api/trading/auto-invest-all", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ budget_pct: 0.15 })
      });
      const data = await res.json();
      showToast(data.message || "Auto-invest berhasil dijalankan", 'success');
      fetchTradingData();
      fetchEquityData();
    } catch (err) {
      showToast("Kesalahan jaringan saat auto-invest", 'error');
    }
  };

  const handleAutoInvestSingle = async (signalId: number, price: number) => {
    try {
      const res = await fetch("/api/trading/auto-invest-single", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ signal_id: signalId, budget_pct: 0.20, price })
      });
      const data = await res.json();
      showToast(data.message || "Auto-invest tunggal berhasil", 'success');
      fetchTradingData();
      fetchEquityData();
    } catch (err) {
      showToast("Kesalahan jaringan saat auto-invest tunggal", 'error');
    }
  };

  const handleCheckTpsl = async () => {
    try {
      const res = await fetch("/api/trading/check-tpsl", { method: "POST" });
      const data = await res.json();
      showToast(data.message || "Pengecekan TP/SL selesai", 'success');
      fetchTradingData();
      fetchEquityData();
    } catch (err) {
      showToast("Kesalahan jaringan saat mengecek TP/SL", 'error');
    }
  };

  const loadPortfolioData = async () => {
    setPortfolioLoading(true);
    try {
      // 1. Load holdings & summary
      const holdingsRes = await fetch("/api/portfolio/holdings");
      if (holdingsRes.ok) {
        const data = await holdingsRes.json();
        setPortfolioHoldings(data.holdings || []);
        setPortfolioSummary(data.summary || {});
        // Auto set default ticker
        if (data.holdings && data.holdings.length > 0 && !recordTxnTicker) {
          setRecordTxnTicker(data.holdings[0].ticker);
          setTimingTicker(data.holdings[0].ticker);
        }
      }
      
      // 2. Load DCA strategies
      const dcaRes = await fetch("/api/portfolio/dca/strategies");
      if (dcaRes.ok) {
        const data = await dcaRes.json();
        setDcaStrategies(data.strategies || []);
      }
      
      // 3. Load Transactions
      const txnsRes = await fetch("/api/portfolio/transactions");
      if (txnsRes.ok) {
        const data = await txnsRes.json();
        setPortfolioTxns(data.transactions || []);
      }
    } catch (err) {
      console.error("Error loading portfolio data:", err);
      showToast("Gagal memuat data portofolio", "error");
    } finally {
      setPortfolioLoading(false);
    }
  };

  const handleAddHolding = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newHoldingTicker) {
      showToast("Ticker harus diisi", "error");
      return;
    }
    try {
      const res = await fetch("/api/portfolio/holdings/add", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ticker: newHoldingTicker.toUpperCase(),
          lot: newHoldingLots,
          avg_cost: newHoldingAvg,
          notes: newHoldingNotes
        })
      });
      if (res.ok) {
        showToast(`Sukses menambahkan holding ${newHoldingTicker.toUpperCase()}`, "success");
        setNewHoldingTicker("");
        setNewHoldingLots(10);
        setNewHoldingAvg(1000);
        setNewHoldingNotes("");
        loadPortfolioData();
      } else {
        const data = await res.json();
        showToast(`Gagal: ${data.detail || "Error"}`, "error");
      }
    } catch (err) {
      showToast("Kesalahan jaringan", "error");
    }
  };

  const handleRecordTransaction = async (e: React.FormEvent) => {
    e.preventDefault();
    const tickerToUse = recordTxnTicker || (portfolioHoldings[0]?.ticker);
    if (!tickerToUse) {
      showToast("Ticker harus dipilih", "error");
      return;
    }
    try {
      const res = await fetch("/api/portfolio/holdings/record-buy-sell", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ticker: tickerToUse.toUpperCase(),
          transaction_type: recordTxnType,
          lot: recordTxnLots,
          price: recordTxnPrice,
          notes: recordTxnNotes
        })
      });
      if (res.ok) {
        showToast(`Sukses mencatat transaksi ${recordTxnType} ${tickerToUse.toUpperCase()}`, "success");
        setRecordTxnLots(1);
        setRecordTxnNotes("");
        setBuyPreview(null);
        loadPortfolioData();
      } else {
        const data = await res.json();
        showToast(`Gagal: ${data.detail || "Error"}`, "error");
      }
    } catch (err) {
      showToast("Kesalahan jaringan", "error");
    }
  };

  const handlePreviewBuy = async () => {
    const tickerToUse = recordTxnTicker || (portfolioHoldings[0]?.ticker);
    if (!tickerToUse) return;
    try {
      const res = await fetch(`/api/portfolio/holdings/preview-buy?ticker=${tickerToUse.toUpperCase()}&price=${recordTxnPrice}&lot=${recordTxnLots}`);
      if (res.ok) {
        const data = await res.json();
        setBuyPreview(data);
      }
    } catch (err) {
      console.error(err);
    }
  };

  const handleResetHoldings = async () => {
    if (!confirm("Apakah Anda yakin ingin menghapus seluruh data holdings dan transaksi? Tindakan ini tidak dapat dibatalkan!")) {
      return;
    }
    try {
      const res = await fetch("/api/portfolio/holdings/reset", { method: "POST" });
      if (res.ok) {
        showToast("Seluruh data portofolio telah direset", "success");
        loadPortfolioData();
      } else {
        showToast("Gagal mereset portofolio", "error");
      }
    } catch (err) {
      showToast("Kesalahan jaringan", "error");
    }
  };

  const getMonthlyFlow = () => {
    const monthlyData: { [key: string]: number } = {};
    portfolioTxns.forEach(t => {
      const dateStr = t.transaction_date || t.created_at || "";
      if (!dateStr) return;
      const month = dateStr.substring(0, 7); // "YYYY-MM"
      const amt = Number(t.amount) || 0;
      const flow = t.transaction_type === "SELL" ? amt : -amt;
      monthlyData[month] = (monthlyData[month] || 0) + flow;
    });
    return Object.entries(monthlyData).map(([month, net_flow]) => ({ month, net_flow })).sort((a, b) => a.month.localeCompare(b.month));
  };

  const getTickerStats = () => {
    const stats: { [ticker: string]: { amount: number, lots: number, count: number } } = {};
    portfolioTxns.forEach(t => {
      const ticker = t.ticker;
      if (!stats[ticker]) {
        stats[ticker] = { amount: 0, lots: 0, count: 0 };
      }
      stats[ticker].amount += Number(t.amount) || 0;
      stats[ticker].lots += Number(t.lots) || 0;
      stats[ticker].count += 1;
    });
    return Object.entries(stats).map(([ticker, data]) => ({ ticker, ...data }));
  };

  const handleCreateDca = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      let res;
      if (dcaMode === "signal") {
        if (!selectedSignalId) {
          showToast("Sinyal harus dipilih", "error");
          return;
        }
        const sig = picks.find(p => p.id === selectedSignalId);
        if (!sig || !sig.entry_low || !sig.entry_high || !sig.max_entry) {
          showToast("Sinyal yang dipilih tidak memiliki Entry Zone (BUY) yang valid.", "error");
          return;
        }
        res = await fetch("/api/portfolio/dca/create-signal", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            signal_id: selectedSignalId,
            total_budget: dcaBudget,
            dca_count: dcaCount
          })
        });
      } else {
        if (!manualDcaTicker) {
          showToast("Ticker harus diisi", "error");
          return;
        }
        res = await fetch("/api/portfolio/dca/create-manual", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            ticker: manualDcaTicker.toUpperCase(),
            total_budget: dcaBudget,
            entry_low: manualEntryLow,
            entry_high: manualEntryHigh,
            max_entry: manualMaxEntry,
            dca_count: dcaCount
          })
        });
      }
      
      if (res.ok) {
        showToast("Sukses mengaktifkan DCA strategy", "success");
        setManualDcaTicker("");
        setPreviewDcaLevels([]);
        loadPortfolioData();
      } else {
        const data = await res.json();
        showToast(`Gagal: ${data.detail || "Error"}`, "error");
      }
    } catch (err) {
      showToast("Kesalahan jaringan", "error");
    }
  };

  const handlePreviewDcaLevels = async () => {
    setDcaLevelsLoading(true);
    try {
      let entryLow = 0, entryHigh = 0, maxEntry = 0;
      if (dcaMode === "signal") {
        const sig = picks.find(p => p.id === selectedSignalId);
        if (!sig) {
          showToast("Pilih sinyal terlebih dahulu", "error");
          setDcaLevelsLoading(false);
          return;
        }
        if (!sig.entry_low || !sig.entry_high || !sig.max_entry) {
          showToast("Sinyal yang dipilih tidak memiliki Entry Zone (BUY) yang valid untuk DCA.", "error");
          setDcaLevelsLoading(false);
          return;
        }
        entryLow = sig.entry_low;
        entryHigh = sig.entry_high || sig.entry_low;
        maxEntry = sig.max_entry;
      } else {
        if (!manualDcaTicker) {
          showToast("Ketik Ticker terlebih dahulu", "error");
          setDcaLevelsLoading(false);
          return;
        }
        if (!manualEntryLow || !manualEntryHigh || !manualMaxEntry) {
          showToast("Masukkan Entry Low, Entry High, dan Max Entry terlebih dahulu", "error");
          setDcaLevelsLoading(false);
          return;
        }
        entryLow = manualEntryLow;
        entryHigh = manualEntryHigh;
        maxEntry = manualMaxEntry;
      }
      
      const res = await fetch("/api/portfolio/dca/calculate-levels", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          entry_low: entryLow,
          entry_high: entryHigh,
          max_entry: maxEntry,
          total_budget: dcaBudget,
          dca_count: dcaCount
        })
      });
      if (res.ok) {
        const data = await res.json();
        setPreviewDcaLevels(data.levels || []);
      } else {
        showToast("Gagal menghitung level DCA", "error");
      }
    } catch (err) {
      showToast("Kesalahan jaringan", "error");
    } finally {
      setDcaLevelsLoading(false);
    }
  };

  const handleAiDcaRecommend = async () => {
    if (!manualDcaTicker) {
      showToast("Ketik Ticker terlebih dahulu", "error");
      return;
    }
    try {
      const res = await fetch(`/api/portfolio/dca/ai-recommend-entry?ticker=${manualDcaTicker.toUpperCase()}`);
      if (res.ok) {
        const data = await res.json();
        if (data.recommendation) {
          setManualEntryLow(data.recommendation.entry_low);
          setManualEntryHigh(data.recommendation.entry_high);
          setManualMaxEntry(data.recommendation.max_entry);
          showToast(`Berhasil menerapkan rekomendasi AI untuk ${manualDcaTicker.toUpperCase()}`, "success");
        } else {
          showToast("Tidak ada rekomendasi dari AI untuk saham ini.", "error");
        }
      }
    } catch (err) {
      showToast("Kesalahan jaringan saat menghubungi AI", "error");
    }
  };

  const handleDeactivateDca = async (id: number) => {
    if (!confirm("Nonaktifkan strategi DCA ini?")) return;
    try {
      const res = await fetch("/api/portfolio/dca/deactivate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ strategy_id: id })
      });
      if (res.ok) {
        showToast("Strategi DCA dinonaktifkan", "success");
        loadPortfolioData();
      } else {
        showToast("Gagal menonaktifkan", "error");
      }
    } catch (err) {
      showToast("Kesalahan jaringan", "error");
    }
  };

  const handleCheckTiming = async () => {
    const tickerToUse = timingTicker || (portfolioHoldings[0]?.ticker);
    if (!tickerToUse) {
      showToast("Pilih ticker terlebih dahulu", "error");
      return;
    }
    setTimingLoading(true);
    try {
      const res = await fetch(`/api/portfolio/dca/recommend-timing?ticker=${tickerToUse.toUpperCase()}`);
      if (res.ok) {
        const data = await res.json();
        setTimingResult(data.timing);
      } else {
        showToast("Gagal mengambil rekomendasi timing", "error");
      }
    } catch (err) {
      showToast("Kesalahan jaringan", "error");
    } finally {
      setTimingLoading(false);
    }
  };

  const handleRunAiAnalysis = async () => {
    setAiAnalysisLoading(true);
    try {
      const res = await fetch("/api/portfolio/ai-analysis", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ monthly_budget: aiMonthlyBudget })
      });
      if (res.ok) {
        const data = await res.json();
        setAiAnalysisResult(data);
        showToast("Analisis AI selesai!", "success");
      } else {
        showToast("Gagal menjalankan Analisis AI", "error");
      }
    } catch (err) {
      showToast("Kesalahan jaringan", "error");
    } finally {
      setAiAnalysisLoading(false);
    }
  };

  useEffect(() => {
    if (picks.length > 0 && selectedSignalId === null) {
      setSelectedSignalId(picks[0].id);
    }
  }, [picks, selectedSignalId]);

  useEffect(() => {
    if (recordTxnType === "BUY" && activeTab === "portfolio" && portfolioTab === "holdings") {
      const timer = setTimeout(() => {
        handlePreviewBuy();
      }, 500);
      return () => clearTimeout(timer);
    } else {
      setBuyPreview(null);
    }
  }, [recordTxnTicker, recordTxnPrice, recordTxnLots, recordTxnType, portfolioTab, activeTab]);

  useEffect(() => {
    if (activeTab === 'bandarmologi') {
      fetchBandarmologiData(bandarmologiTicker);
    } else if (activeTab === 'ihsg') {
      fetchIhsgData();
    } else if (activeTab === 'trading') {
      fetchTradingData();
      fetchEquityData();
    } else if (activeTab === 'portfolio') {
      loadPortfolioData();
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
      showToast("Harga belum tersedia untuk saham ini.", "error");
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
            <button onClick={() => { setActiveTab("trading"); setSidebarOpen(false); }} className={`w-full flex items-center gap-4 px-4 py-3 rounded-xl font-medium transition ${activeTab === 'trading' ? 'bg-white/10 text-white border border-white/5 shadow-[0_0_15px_rgba(255,255,255,0.05)]' : 'text-slate-400 hover:text-white hover:bg-white/5'}`}>
              <span className="text-lg">💹</span> Trading Engine
            </button>
            <button onClick={() => { setActiveTab("bandarmologi"); setSidebarOpen(false); }} className={`w-full flex items-center gap-4 px-4 py-3 rounded-xl font-medium transition ${activeTab === 'bandarmologi' ? 'bg-white/10 text-white border border-white/5 shadow-[0_0_15px_rgba(255,255,255,0.05)]' : 'text-slate-400 hover:text-white hover:bg-white/5'}`}>
              <span className="text-lg">🏛️</span> Bandarmologi
            </button>
            <button onClick={() => { setActiveTab("ihsg"); setSidebarOpen(false); }} className={`w-full flex items-center gap-4 px-4 py-3 rounded-xl font-medium transition ${activeTab === 'ihsg' ? 'bg-white/10 text-white border border-white/5 shadow-[0_0_15px_rgba(255,255,255,0.05)]' : 'text-slate-400 hover:text-white hover:bg-white/5'}`}>
              <span className="text-lg">📈</span> IHSG Predictor
            </button>
            <button onClick={() => { setActiveTab("history"); setSidebarOpen(false); }} className={`w-full flex items-center gap-4 px-4 py-3 rounded-xl font-medium transition ${activeTab === 'history' ? 'bg-white/10 text-white border border-white/5 shadow-[0_0_15px_rgba(255,255,255,0.05)]' : 'text-slate-400 hover:text-white hover:bg-white/5'}`}>
              <span className="text-lg">📊</span> AI Track Record
            </button>
            <button onClick={() => { setActiveTab("portfolio"); setSidebarOpen(false); }} className={`w-full flex items-center gap-4 px-4 py-3 rounded-xl font-medium transition ${activeTab === 'portfolio' ? 'bg-white/10 text-white border border-white/5 shadow-[0_0_15px_rgba(255,255,255,0.05)]' : 'text-slate-400 hover:text-white hover:bg-white/5'}`}>
              <span className="text-lg">💼</span> Portfolio Management
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
                        onClick={() => {
                          setBuyTicker(selectedStock.ticker);
                          setBuyPrice(selectedStock.current_price || selectedStock.entry_price || 1000);
                          setBuyLot(10);
                          setBuyTp(selectedStock.target_1 || 0);
                          setBuySl(selectedStock.stop_loss || 0);
                          setBuySignalId(selectedStock.id || null);
                          setActiveTab("trading");
                          setSelectedStock(null);
                          showToast(`Form order untuk ${selectedStock.ticker} telah diisi. Silakan periksa di Trading Engine!`, 'info');
                        }}
                        className="w-full py-3 rounded-lg font-bold text-white bg-indigo-500 hover:bg-indigo-600 transition text-sm shadow-lg shadow-indigo-500/20">
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
                    <span className={`font-bold ${bandarmologiData.price_analysis.distance_from_7d?.includes('-') ? 'text-red-400' : 'text-emerald-400'}`}>
                      {bandarmologiData.price_analysis.distance_from_7d || 'N/A'}
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span>🏷️</span>
                    <span>Jarak dari avg 1M:</span>
                    <span className={`font-bold ${bandarmologiData.price_analysis.distance_from_1m?.includes('-') ? 'text-red-400' : 'text-emerald-400'}`}>
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

        {activeTab === 'ihsg' && (
          <div className="space-y-6 animate-fade-in">
            <div>
              <h2 className="text-3xl font-bold text-white mb-2">IHSG <span className="text-indigo-400">Predictor</span></h2>
              <p className="text-slate-400">Analisis komparatif arah indeks pasar, skor komponen makro & sektoral, dan prediksi tingkat volatilitas.</p>
            </div>

            {ihsgLoading && (
              <div className="flex flex-col items-center justify-center py-20 gap-4">
                <span className="w-10 h-10 border-4 border-indigo-500 border-t-transparent rounded-full animate-spin"></span>
                <span className="text-slate-400 font-medium">Menganalisis pergerakan IHSG...</span>
              </div>
            )}

            {ihsgError && (
              <div className="p-4 bg-red-500/10 border border-red-500/20 text-red-300 rounded-2xl text-center">
                ⚠️ {ihsgError}
              </div>
            )}

            {!ihsgLoading && !ihsgError && ihsgData && ihsgData.latest && (() => {
              const latest = ihsgData.latest;
              const history = ihsgData.history || [];
              const scores = latest.component_scores || {};
              const drivers = latest.key_drivers || [];
              const risks = latest.risks || [];

              return (
                <>
                  {/* Header Metrics */}
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-6 bg-white/[0.03] backdrop-blur-md border border-white/5 rounded-3xl p-6 hover:bg-white/[0.05] transition duration-300">
                    <div>
                      <p className="text-xs text-slate-400 font-bold uppercase tracking-wider mb-2">Current Level</p>
                      <p className="text-2xl md:text-3xl font-black text-white font-mono">
                        {latest.current_price?.toLocaleString('id-ID')}
                      </p>
                    </div>
                    <div>
                      <p className="text-xs text-slate-400 font-bold uppercase tracking-wider mb-2">Confidence</p>
                      <div className="flex items-center gap-2">
                        <span className={`inline-block w-4 h-4 rounded-full ${
                          latest.confidence === 'HIGH' ? 'bg-emerald-400 shadow-[0_0_10px_rgba(52,211,153,0.5)]' :
                          latest.confidence === 'MEDIUM' ? 'bg-amber-400 shadow-[0_0_10px_rgba(251,191,36,0.5)]' :
                          'bg-red-400 shadow-[0_0_10px_rgba(248,113,113,0.5)]'
                        }`}></span>
                        <span className="text-lg md:text-xl font-extrabold text-white uppercase tracking-wide">
                          {latest.confidence}
                        </span>
                      </div>
                    </div>
                    <div>
                      <p className="text-xs text-slate-400 font-bold uppercase tracking-wider mb-2">Direction</p>
                      <p className={`text-xl md:text-2xl font-black uppercase tracking-wide ${
                        latest.direction === 'BULLISH' ? 'text-emerald-400' :
                        latest.direction === 'BEARISH' ? 'text-red-400' :
                        'text-slate-300'
                      }`}>
                        {latest.direction}
                      </p>
                    </div>
                    <div>
                      <p className="text-xs text-slate-400 font-bold uppercase tracking-wider mb-2">Volatility</p>
                      <p className="text-xl md:text-2xl font-black text-white uppercase tracking-wide">
                        {latest.volatility_level}
                      </p>
                    </div>
                  </div>

                  {/* Predictions Grid */}
                  <div>
                    <h3 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
                      <span>📊</span> Price Predictions
                    </h3>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                      {/* D1 */}
                      <div className="bg-white/[0.03] border border-white/5 rounded-2xl p-5 hover:bg-white/[0.05] transition duration-300 font-mono">
                        <p className="text-xs text-slate-400 font-bold font-sans uppercase mb-2">D+1 Prediction</p>
                        <p className="text-xl font-bold text-white">{latest.day_1_price?.toLocaleString('id-ID')}</p>
                        <p className={`text-xs mt-1 font-bold ${latest.day_1_pct >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                          {latest.day_1_pct >= 0 ? '+' : ''}{latest.day_1_pct?.toFixed(2)}%
                        </p>
                      </div>
                      {/* D3 */}
                      <div className="bg-white/[0.03] border border-white/5 rounded-2xl p-5 hover:bg-white/[0.05] transition duration-300 font-mono">
                        <p className="text-xs text-slate-400 font-bold font-sans uppercase mb-2">D+3 Prediction</p>
                        <p className="text-xl font-bold text-white">{latest.day_3_price?.toLocaleString('id-ID')}</p>
                        <p className={`text-xs mt-1 font-bold ${latest.day_3_pct >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                          {latest.day_3_pct >= 0 ? '+' : ''}{latest.day_3_pct?.toFixed(2)}%
                        </p>
                      </div>
                      {/* D5 */}
                      <div className="bg-white/[0.03] border border-white/5 rounded-2xl p-5 hover:bg-white/[0.05] transition duration-300 font-mono">
                        <p className="text-xs text-slate-400 font-bold font-sans uppercase mb-2">D+5 Prediction</p>
                        <p className="text-xl font-bold text-white">{latest.day_5_price?.toLocaleString('id-ID')}</p>
                        <p className={`text-xs mt-1 font-bold ${latest.day_5_pct >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                          {latest.day_5_pct >= 0 ? '+' : ''}{latest.day_5_pct?.toFixed(2)}%
                        </p>
                      </div>
                      {/* D7 */}
                      <div className="bg-white/[0.03] border border-white/5 rounded-2xl p-5 hover:bg-white/[0.05] transition duration-300 font-mono">
                        <p className="text-xs text-slate-400 font-bold font-sans uppercase mb-2">D+7 Prediction</p>
                        <p className="text-xl font-bold text-white">{latest.day_7_price?.toLocaleString('id-ID')}</p>
                        <p className={`text-xs mt-1 font-bold ${latest.day_7_pct >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                          {latest.day_7_pct >= 0 ? '+' : ''}{latest.day_7_pct?.toFixed(2)}%
                        </p>
                      </div>
                    </div>
                  </div>

                  {/* Component Scores */}
                  <div>
                    <h3 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
                      <span>⚙️</span> Component Scores
                    </h3>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-6 bg-white/[0.03] border border-white/5 rounded-3xl p-6">
                      <div>
                        <p className="text-xs text-slate-400 font-bold uppercase tracking-wider mb-2">Momentum</p>
                        <p className="text-2xl font-black text-white font-mono">
                          {scores.momentum !== undefined ? scores.momentum.toFixed(2) : '-'}
                        </p>
                      </div>
                      <div>
                        <p className="text-xs text-slate-400 font-bold uppercase tracking-wider mb-2">Breadth</p>
                        <p className="text-2xl font-black text-white font-mono">
                          {scores.breadth !== undefined ? scores.breadth.toFixed(2) : '-'}
                        </p>
                      </div>
                      <div>
                        <p className="text-xs text-slate-400 font-bold uppercase tracking-wider mb-2">Macro</p>
                        <p className="text-2xl font-black text-white font-mono">
                          {scores.macro !== undefined ? scores.macro.toFixed(2) : '-'}
                        </p>
                      </div>
                      <div>
                        <p className="text-xs text-slate-400 font-bold uppercase tracking-wider mb-2">Sectors</p>
                        <p className="text-2xl font-black text-white font-mono">
                          {scores.sectors !== undefined ? scores.sectors.toFixed(2) : '-'}
                        </p>
                      </div>
                    </div>
                  </div>

                  {/* Analysis Expanders */}
                  <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                    {/* Left: Reasoning & Analysis */}
                    <div className="space-y-6">
                      <div className="bg-white/[0.03] border border-white/5 rounded-3xl p-6 hover:bg-white/[0.05] transition duration-300">
                        <h3 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
                          <span>📝</span> Reasoning & Analysis
                        </h3>
                        <div className="text-slate-300 text-sm leading-relaxed whitespace-pre-wrap font-sans">
                          {latest.reasoning || 'No analysis reasoning details available.'}
                        </div>
                      </div>
                    </div>

                    {/* Right: Key Drivers & Risks */}
                    <div className="space-y-6">
                      {/* Key Drivers */}
                      <div className="bg-white/[0.03] border border-white/5 rounded-3xl p-6 hover:bg-white/[0.05] transition duration-300">
                        <h3 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
                          <span className="text-emerald-400">✓</span> Key Drivers
                        </h3>
                        {drivers.length > 0 ? (
                          <ul className="space-y-2.5">
                            {drivers.map((driver: string, i: number) => (
                              <li key={i} className="flex items-start gap-3 text-slate-300 text-sm">
                                <span className="text-emerald-400 mt-0.5">•</span>
                                <span>{driver}</span>
                              </li>
                            ))}
                          </ul>
                        ) : (
                          <p className="text-slate-500 text-sm">No drivers identified.</p>
                        )}
                      </div>

                      {/* Risk Factors */}
                      <div className="bg-white/[0.03] border border-white/5 rounded-3xl p-6 hover:bg-white/[0.05] transition duration-300">
                        <h3 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
                          <span className="text-red-400">⚠️</span> Risk Factors
                        </h3>
                        {risks.length > 0 ? (
                          <ul className="space-y-2.5">
                            {risks.map((risk: string, i: number) => (
                              <li key={i} className="flex items-start gap-3 text-slate-300 text-sm">
                                <span className="text-red-400 mt-0.5">•</span>
                                <span>{risk}</span>
                              </li>
                            ))}
                          </ul>
                        ) : (
                          <p className="text-slate-500 text-sm">No major risks identified.</p>
                        )}
                      </div>
                    </div>
                  </div>

                  {/* Historical Table */}
                  <div>
                    <h3 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
                      <span>📈</span> Historical Predictions
                    </h3>
                    <div className="overflow-x-auto rounded-2xl border border-white/5 bg-[#030712]/40">
                      <table className="w-full text-left border-collapse text-sm">
                        <thead>
                          <tr className="border-b border-white/10 text-xs font-bold uppercase tracking-wider text-slate-400 bg-white/5">
                            <th className="py-3.5 px-6">Tanggal</th>
                            <th className="py-3.5 px-6 text-right">Current Index</th>
                            <th className="py-3.5 px-6 text-right">D+1 Predicted</th>
                            <th className="py-3.5 px-6 text-right">D+1 Change</th>
                            <th className="py-3.5 px-6 text-center">Direction</th>
                            <th className="py-3.5 px-6 text-center">Confidence</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-white/5 text-slate-300 font-mono">
                          {history.map((row: any, idx: number) => (
                            <tr key={idx} className="hover:bg-white/5 transition">
                              <td className="py-3.5 px-6 font-sans text-white font-medium">{row.run_date}</td>
                              <td className="py-3.5 px-6 text-right">{row.current_price?.toLocaleString('id-ID')}</td>
                              <td className="py-3.5 px-6 text-right">{row.day_1_price?.toLocaleString('id-ID')}</td>
                              <td className={`py-3.5 px-6 text-right font-bold ${row.day_1_pct >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                                {row.day_1_pct >= 0 ? '+' : ''}{row.day_1_pct?.toFixed(2)}%
                              </td>
                              <td className="py-3.5 px-6 text-center">
                                <span className={`px-2.5 py-0.5 rounded text-[11px] font-sans font-bold uppercase tracking-wider ${
                                  row.direction === 'BULLISH' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' :
                                  row.direction === 'BEARISH' ? 'bg-red-500/10 text-red-400 border border-red-500/20' :
                                  'bg-slate-500/10 text-slate-400 border border-slate-500/20'
                                }`}>
                                  {row.direction}
                                </span>
                              </td>
                              <td className="py-3.5 px-6 text-center">
                                <span className={`px-2.5 py-0.5 rounded text-[11px] font-sans font-bold uppercase tracking-wider ${
                                  row.confidence === 'HIGH' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' :
                                  row.confidence === 'MEDIUM' ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20' :
                                  'bg-red-500/10 text-red-400 border border-red-500/20'
                                }`}>
                                  {row.confidence}
                                </span>
                              </td>
                            </tr>
                          ))}
                          {history.length === 0 && (
                            <tr>
                              <td colSpan={6} className="py-10 text-center text-slate-500 font-sans">Belum ada riwayat prediksi.</td>
                            </tr>
                          )}
                        </tbody>
                      </table>
                    </div>
                  </div>
                </>
              );
            })()}
          </div>
        )}

        {/* Custom Equity Curve Chart Component */}
        {activeTab === 'trading' && (() => {
          const CustomEquityChart = ({ points }: { points: any[] }) => {
            if (!points || points.length === 0) {
              return (
                <div className="relative w-full h-[220px] bg-white/[0.02] border border-white/5 rounded-3xl p-6 hover:bg-white/[0.04] transition duration-300 flex items-center justify-center text-slate-500 text-sm">
                  Equity curve akan muncul setelah ada trades.
                </div>
              );
            }
            
            // Calculate min and max for scaling
            const values = points.map(p => p.equity);
            const minVal = Math.min(...values) * 0.99; // 1% padding
            const maxVal = Math.max(...values) * 1.01; // 1% padding
            const range = maxVal - minVal || 1;

            // Chart dimensions
            const width = 500;
            const height = 150;
            const paddingX = 25;
            const paddingY = 15;

            const pointsCount = points.length;
            
            // Map points to SVG coordinates
            const svgPoints = points.map((p, idx) => {
              const x = paddingX + (idx / (pointsCount - 1 || 1)) * (width - 2 * paddingX);
              const y = height - paddingY - ((p.equity - minVal) / range) * (height - 2 * paddingY);
              return { x, y, data: p };
            });

            // Create path description string
            const pathD = svgPoints.reduce((acc, p, idx) => {
              return acc + `${idx === 0 ? 'M' : 'L'} ${p.x} ${p.y}`;
            }, "");

            // Create fill area path description string (under the line)
            const fillD = svgPoints.length > 0 
              ? `${pathD} L ${svgPoints[svgPoints.length - 1].x} ${height - paddingY} L ${svgPoints[0].x} ${height - paddingY} Z`
              : "";

            return (
              <div className="relative w-full h-[220px] bg-white/[0.02] border border-white/5 rounded-3xl p-6 hover:bg-white/[0.04] transition duration-300">
                <div className="flex justify-between items-center mb-4">
                  <div>
                    <h4 className="text-sm font-bold text-slate-400 uppercase tracking-wider">Equity Growth</h4>
                    <p className="text-[10px] text-slate-505 font-medium">Virtual portfolio value progression</p>
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
                      {/* Area Gradient */}
                      <linearGradient id="chartGradient" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor="#00d4aa" stopOpacity="0.2" />
                        <stop offset="100%" stopColor="#00d4aa" stopOpacity="0.00" />
                      </linearGradient>
                      {/* Glow Filter */}
                      <filter id="glow" x="-20%" y="-20%" width="140%" height="140%">
                        <feDropShadow dx="0" dy="4" stdDeviation="4" floodColor="#00d4aa" floodOpacity="0.3" />
                      </filter>
                    </defs>
                    
                    {/* Horizontal lines grid */}
                    <line x1={paddingX} y1={paddingY} x2={width - paddingX} y2={paddingY} stroke="rgba(255,255,255,0.03)" strokeDasharray="3" />
                    <line x1={paddingX} y1={height/2} x2={width - paddingX} y2={height/2} stroke="rgba(255,255,255,0.03)" strokeDasharray="3" />
                    <line x1={paddingX} y1={height - paddingY} x2={width - paddingX} y2={height - paddingY} stroke="rgba(255,255,255,0.03)" strokeDasharray="3" />

                    {/* Area Fill */}
                    {fillD && <path d={fillD} fill="url(#chartGradient)" />}

                    {/* Stroke Line */}
                    {pathD && <path d={pathD} fill="none" stroke="#00d4aa" strokeWidth="2.5" filter="url(#glow)" />}

                    {/* Data Points Dots */}
                    {svgPoints.map((p, idx) => (
                      <g key={idx} className="group/dot cursor-pointer">
                        <circle cx={p.x} cy={p.y} r="3" fill="#030712" stroke="#00d4aa" strokeWidth="1.5" />
                        <title>{`${p.data.date}: Rp ${p.data.equity.toLocaleString('id-ID')} (${p.data.event || 'Trade'})`}</title>
                      </g>
                    ))}
                  </svg>
                </div>
              </div>
            );
          };

          return (
            <div className="space-y-6 animate-fade-in">
              {/* Title & Check Actions */}
              <div className="flex flex-wrap items-center justify-between gap-4">
                <div>
                  <h2 className="text-3xl font-bold text-white mb-2">Trading <span className="text-indigo-400">Engine</span></h2>
                  <p className="text-slate-400">Virtual Portfolio Validator — Uji strategi trading Anda dengan modal virtual secara real-time.</p>
                </div>
                <div className="flex gap-3">
                  <button 
                    onClick={handleCheckTpsl}
                    className="px-4 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white font-bold rounded-xl text-sm transition flex items-center gap-2 shadow-lg shadow-indigo-600/20"
                  >
                    🔍 Cek TP/SL Sekarang
                  </button>
                  <button 
                    onClick={handleResetPortfolio}
                    className="px-4 py-2.5 bg-red-500/10 hover:bg-red-500/20 border border-red-500/20 text-red-400 font-semibold rounded-xl text-sm transition"
                  >
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

              {tradingError && (
                <div className="p-4 bg-red-500/10 border border-red-500/20 text-red-300 rounded-2xl text-center">
                  ⚠️ {tradingError}
                </div>
              )}

              {!tradingLoading && tradingData && (() => {
                const summary = tradingData.summary || {};
                const history = tradingData.history || [];
                const positions = summary.positions || [];
                const activePositions = positions.filter((p: any) => p.status === 'OPEN');
                const pendingOrders = positions.filter((p: any) => p.status?.startsWith('PENDING'));
                const closedTrades = history.filter((t: any) => t.status !== 'OPEN' && !t.status?.startsWith('PENDING'));

                return (
                  <>
                    {/* Wallet Metrics Grid */}
                    <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
                      <div className="bg-white/[0.03] border border-white/5 rounded-2xl p-5 hover:bg-white/[0.05] transition duration-300">
                        <p className="text-[11px] text-slate-400 font-bold uppercase tracking-wider mb-2">💵 Cash</p>
                        <p className="text-lg font-black text-white font-mono">Rp {summary.cash?.toLocaleString('id-ID')}</p>
                        <p className="text-[10px] text-slate-500 mt-1">Sisa saldo untuk membeli</p>
                      </div>
                      <div className="bg-white/[0.03] border border-white/5 rounded-2xl p-5 hover:bg-white/[0.05] transition duration-300">
                        <p className="text-[11px] text-slate-400 font-bold uppercase tracking-wider mb-2">💼 Invested</p>
                        <p className="text-lg font-black text-white font-mono">Rp {summary.total_invested?.toLocaleString('id-ID')}</p>
                        <p className="text-[10px] text-slate-500 mt-1">Dana terinvestasi di saham</p>
                      </div>
                      <div className="bg-white/[0.03] border border-white/5 rounded-2xl p-5 hover:bg-white/[0.05] transition duration-300">
                        <p className="text-[11px] text-slate-400 font-bold uppercase tracking-wider mb-2">📊 Total Equity</p>
                        <p className="text-lg font-black text-white font-mono">Rp {summary.total_equity?.toLocaleString('id-ID')}</p>
                        <p className={`text-xs font-bold mt-1 font-mono ${summary.total_return_pct >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                          {summary.total_return_pct >= 0 ? '+' : ''}{summary.total_return_pct?.toFixed(2)}%
                        </p>
                      </div>
                      <div className="bg-white/[0.03] border border-white/5 rounded-2xl p-5 hover:bg-white/[0.05] transition duration-300">
                        <p className="text-[11px] text-slate-400 font-bold uppercase tracking-wider mb-2">📈 Realized P&L</p>
                        <p className={`text-lg font-black font-mono ${summary.realized_pnl >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                          Rp {summary.realized_pnl?.toLocaleString('id-ID')}
                        </p>
                        <p className="text-[10px] text-slate-505 mt-1">Profit/Loss posisi tertutup</p>
                      </div>
                      <div className="bg-white/[0.03] border border-white/5 rounded-2xl p-5 hover:bg-white/[0.05] transition duration-300">
                        <p className="text-[11px] text-slate-400 font-bold uppercase tracking-wider mb-2">📊 Unrealized P&L</p>
                        <p className={`text-lg font-black font-mono ${summary.unrealized_pnl >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                          Rp {summary.unrealized_pnl?.toLocaleString('id-ID')}
                        </p>
                        <p className="text-[10px] text-slate-505 mt-1">Profit/Loss posisi terbuka</p>
                      </div>
                    </div>

                    {/* Topup popover area & Equity Curve chart row */}
                    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                      {/* Left: Topup Control Card */}
                      <div className="bg-white/[0.03] border border-white/5 rounded-3xl p-6 hover:bg-white/[0.05] transition duration-300 flex flex-col justify-between">
                        <div>
                          <h4 className="text-sm font-bold text-white uppercase tracking-wider mb-2">💸 Topup Modal Virtual</h4>
                          <p className="text-xs text-slate-400 mb-4">Tambahkan modal virtual untuk melakukan simulasi transaksi pembelian saham.</p>
                          
                          <div className="space-y-4">
                            <div>
                              <label className="text-[10px] text-slate-400 block mb-1.5 font-bold uppercase">Jumlah Topup (Rp)</label>
                              <input 
                                type="number"
                                value={topupAmount}
                                onChange={(e) => setTopupAmount(Number(e.target.value))}
                                min={10000000}
                                className="w-full bg-[#030712] border border-white/10 rounded-xl px-4 py-2 font-mono font-bold text-white focus:outline-none focus:border-indigo-500"
                              />
                            </div>
                            <div className="flex flex-wrap gap-1.5">
                              {[10000000, 50000000, 100000000, 250000000].map((amt) => (
                                <button 
                                  key={amt}
                                  onClick={() => setTopupAmount(amt)}
                                  className={`px-2.5 py-1.5 rounded-lg text-xs font-mono font-bold border transition ${topupAmount === amt ? 'bg-indigo-600 border-indigo-500 text-white' : 'bg-white/5 border-white/5 text-slate-400 hover:text-white'}`}
                                >
                                  {amt >= 1e6 ? `${amt / 1e6}jt` : amt.toLocaleString('id-ID')}
                                </button>
                              ))}
                            </div>
                          </div>
                        </div>
                        
                        <button 
                          onClick={() => handleTopup(topupAmount)}
                          className="mt-6 w-full py-3 bg-white hover:bg-slate-200 text-black font-bold rounded-xl transition text-sm shadow-[0_0_15px_rgba(255,255,255,0.1)]"
                        >
                          💸 Eksekusi Topup
                        </button>
                      </div>

                      {/* Right 2 columns: Chart */}
                      <div className="lg:col-span-2">
                        <CustomEquityChart points={equityData?.points || []} />
                      </div>
                    </div>

                    {/* Manual Trading Form & Quick Buy Top Picks */}
                    <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                      {/* Left: Custom Ticker Buy Form */}
                      <div className="bg-white/[0.03] border border-white/5 rounded-3xl p-6 hover:bg-white/[0.05] transition duration-300 lg:col-span-1">
                        <h3 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
                          <span>🛒</span> Place Order (Buy)
                        </h3>
                        
                        <div className="space-y-4">
                          <div>
                            <label className="text-[10px] text-slate-400 block mb-1 font-bold uppercase">Ticker Saham</label>
                            <input 
                              type="text"
                              value={buyTicker}
                              onChange={(e) => {
                                setBuyTicker(e.target.value);
                                setBuySignalId(null);
                              }}
                              placeholder="e.g. BBCA, MEDC"
                              className="w-full bg-[#030712] border border-white/10 rounded-xl px-4 py-2 text-sm font-mono font-bold text-white uppercase focus:outline-none focus:border-indigo-500"
                            />
                          </div>

                          <div className="grid grid-cols-2 gap-4">
                            <div>
                              <label className="text-[10px] text-slate-400 block mb-1 font-bold uppercase">Jumlah Lot</label>
                              <input 
                                type="number"
                                value={buyLot}
                                onChange={(e) => setBuyLot(Number(e.target.value))}
                                min={1}
                                className="w-full bg-[#030712] border border-white/10 rounded-xl px-4 py-2 text-sm font-mono font-bold text-white focus:outline-none focus:border-indigo-500"
                              />
                            </div>
                            <div>
                              <label className="text-[10px] text-slate-400 block mb-1 font-bold uppercase">Harga Bid (Rp)</label>
                              <input 
                                type="number"
                                value={buyPrice}
                                onChange={(e) => setBuyPrice(Number(e.target.value))}
                                min={1}
                                className="w-full bg-[#030712] border border-white/10 rounded-xl px-4 py-2 text-sm font-mono font-bold text-white focus:outline-none focus:border-indigo-500"
                              />
                            </div>
                          </div>

                          <div className="grid grid-cols-2 gap-4">
                            <div>
                              <label className="text-[10px] text-slate-400 block mb-1 font-bold uppercase">Target TP1 (Optional)</label>
                              <input 
                                type="number"
                                value={buyTp}
                                onChange={(e) => setBuyTp(Number(e.target.value))}
                                min={0}
                                placeholder="0"
                                className="w-full bg-[#030712] border border-white/10 rounded-xl px-4 py-2 text-sm font-mono font-bold text-white focus:outline-none focus:border-indigo-500"
                              />
                            </div>
                            <div>
                              <label className="text-[10px] text-slate-400 block mb-1 font-bold uppercase">Target SL (Optional)</label>
                              <input 
                                type="number"
                                value={buySl}
                                onChange={(e) => setBuySl(Number(e.target.value))}
                                min={0}
                                placeholder="0"
                                className="w-full bg-[#030712] border border-white/10 rounded-xl px-4 py-2 text-sm font-mono font-bold text-white focus:outline-none focus:border-indigo-500"
                              />
                            </div>
                          </div>

                          <button 
                            onClick={() => handleBuy(buyTicker, buyLot, buyPrice, buySignalId, buyTp, buySl)}
                            className="w-full py-3 mt-2 bg-emerald-500 hover:bg-emerald-400 text-white font-bold rounded-xl transition text-sm shadow-lg shadow-emerald-500/20"
                          >
                            🛒 Kirim Order Buy
                          </button>
                        </div>
                      </div>

                      {/* Right 2 columns: Quick Buy from Top Picks */}
                      <div className="lg:col-span-2 space-y-4">
                        <div className="flex justify-between items-center">
                          <h3 className="text-lg font-bold text-white flex items-center gap-2">
                            <span>🎯</span> Quick Buy dari Top Picks
                          </h3>
                          <button 
                            onClick={handleAutoInvestAll}
                            className="px-3.5 py-1.5 bg-indigo-600/10 hover:bg-indigo-600/20 border border-indigo-500/20 text-indigo-400 font-bold rounded-xl text-xs transition"
                          >
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
                                    <p className="text-[10px] text-slate-505">Rank #{pick.rank || '-'}</p>
                                  </div>
                                  <div className="text-right">
                                    <p className="text-xs text-slate-400 font-mono">Entry: Rp {pick.entry_low?.toLocaleString('id-ID')}–{pick.entry_high?.toLocaleString('id-ID')}</p>
                                    <p className="text-[10px] text-slate-505">TP1: Rp {pick.target_1?.toLocaleString('id-ID')} | SL: Rp {pick.stop_loss?.toLocaleString('id-ID')}</p>
                                  </div>
                                </div>
                                <div className="flex gap-2">
                                  <button 
                                    onClick={() => {
                                      setBuyTicker(pick.ticker);
                                      setBuyPrice(defaultPrice);
                                      setBuyTp(pick.target_1 || 0);
                                      setBuySl(pick.stop_loss || 0);
                                      setBuySignalId(pick.id || null);
                                    }}
                                    className="flex-1 py-1.5 bg-white/5 hover:bg-white/10 text-white rounded-lg text-xs font-bold transition border border-white/5"
                                  >
                                    Prefill Form
                                  </button>
                                  <button 
                                    onClick={() => handleAutoInvestSingle(pick.id, defaultPrice)}
                                    className="flex-1 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-xs font-bold transition"
                                  >
                                    ⚡ Auto 20%
                                  </button>
                                </div>
                              </div>
                            );
                          })}
                          {picks.length === 0 && (
                            <div className="col-span-2 py-10 text-center text-slate-500 text-sm">Tidak ada rekomendasi Top Picks aktif.</div>
                          )}
                        </div>
                      </div>
                    </div>

                    {/* Pending Orders */}
                    <div>
                      <h3 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
                        <span>⏳</span> Pending Orders
                      </h3>
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        {pendingOrders.map((pos: any) => {
                          const diffVal = Math.abs(pos.current_price - pos.buy_price);
                          const diffPct = pos.current_price ? (diffVal / pos.current_price * 100) : 0;
                          return (
                            <div key={pos.id} className="bg-white/[0.03] border border-white/5 rounded-2xl p-5 flex justify-between items-center gap-4 hover:bg-white/[0.05] transition duration-300">
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
                              <button 
                                onClick={() => handleCancelPending(pos.id)}
                                className="px-3.5 py-2 bg-red-500/10 hover:bg-red-500/20 border border-red-500/20 text-red-400 text-xs font-bold rounded-lg transition"
                              >
                                Batal
                              </button>
                            </div>
                          );
                        })}
                        {pendingOrders.length === 0 && (
                          <div className="col-span-2 py-8 text-center bg-white/[0.01] border border-dashed border-white/5 rounded-2xl text-slate-500 text-sm">Tidak ada pending orders.</div>
                        )}
                      </div>
                    </div>

                    {/* Open Positions */}
                    <div>
                      <h3 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
                        <span>📈</span> Open Positions
                      </h3>
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        {activePositions.map((pos: any) => {
                          const isProfit = pos.unrealized_pnl >= 0;
                          const pctToTp = (pos.tp1 && pos.current_price && pos.tp1 > pos.current_price) 
                            ? ((pos.tp1 - pos.current_price) / pos.current_price * 100).toFixed(2) 
                            : null;
                          const pctToSl = (pos.stop_loss && pos.current_price && pos.stop_loss < pos.current_price) 
                            ? ((pos.current_price - pos.stop_loss) / pos.current_price * 100).toFixed(2) 
                            : null;
                          
                          return (
                            <div key={pos.id} className="bg-white/[0.03] border border-white/5 rounded-2xl p-5 flex justify-between items-center gap-4 hover:bg-white/[0.05] transition duration-300">
                              <div className="flex-1">
                                <div className="flex items-center justify-between mb-2">
                                  <h4 className="font-extrabold text-white text-lg">{pos.ticker}</h4>
                                  <span className={`font-mono font-bold text-sm ${isProfit ? 'text-emerald-400' : 'text-red-400'}`}>
                                    {isProfit ? '▲' : '▼'} {pos.unrealized_pnl_pct?.toFixed(2)}%
                                  </span>
                                </div>
                                <p className="text-xs text-slate-400 font-mono mb-2">{pos.lot} lot ({pos.shares?.toLocaleString('id-ID')} lembar)</p>
                                
                                <div className="grid grid-cols-2 sm:grid-cols-3 gap-y-3 gap-x-2 font-mono text-[11px] text-slate-400 mt-1">
                                  <div>
                                    <span className="text-[10px] text-slate-500 block">Buy Price</span>
                                    Rp {pos.buy_price?.toLocaleString('id-ID')}
                                  </div>
                                  <div>
                                    <span className="text-[10px] text-slate-500 block">Cur. Price</span>
                                    Rp {pos.current_price?.toLocaleString('id-ID')}
                                  </div>
                                  <div>
                                    <span className="text-[10px] text-slate-500 block">Unrealized P&L</span>
                                    <span className={isProfit ? 'text-emerald-400 font-bold' : 'text-red-400 font-bold'}>
                                      Rp {pos.unrealized_pnl?.toLocaleString('id-ID')}
                                    </span>
                                  </div>
                                  <div>
                                    <span className="text-[10px] text-slate-500 block">Invested</span>
                                    Rp {((pos.buy_price || 0) * (pos.shares || 0)).toLocaleString('id-ID')}
                                  </div>
                                  <div>
                                    <span className="text-[10px] text-slate-500 block">Cur. Value</span>
                                    <span className={isProfit ? 'text-emerald-400' : 'text-red-400'}>
                                      Rp {((pos.current_price || 0) * (pos.shares || 0)).toLocaleString('id-ID')}
                                    </span>
                                  </div>
                                  <div>
                                    <span className="text-[10px] text-slate-500 block mb-0.5">Target TP / SL</span>
                                    <div className="flex flex-col gap-0.5">
                                      <div className="flex items-center gap-1">
                                        <span className="text-emerald-400">{pos.tp1 ? `Rp ${pos.tp1.toLocaleString('id-ID')}` : '-'}</span>
                                        {pctToTp && <span className="text-[9px] text-emerald-500/70" title="Harus naik">(+{pctToTp}%)</span>}
                                      </div>
                                      <div className="flex items-center gap-1">
                                        <span className="text-red-400">{pos.stop_loss ? `Rp ${pos.stop_loss.toLocaleString('id-ID')}` : '-'}</span>
                                        {pctToSl && <span className="text-[9px] text-red-500/70" title="Harus turun">(-{pctToSl}%)</span>}
                                      </div>
                                    </div>
                                  </div>
                                </div>
                              </div>
                              <button 
                                onClick={() => handleSell(pos.id, pos.current_price)}
                                className="px-4 py-3 bg-red-600 hover:bg-red-500 text-white text-xs font-bold rounded-lg transition"
                              >
                                SELL
                              </button>
                            </div>
                          );
                        })}
                        {activePositions.length === 0 && (
                          <div className="col-span-2 py-10 text-center bg-white/[0.01] border border-dashed border-white/5 rounded-2xl text-slate-500 text-sm">Tidak ada posisi aktif yang terbuka.</div>
                        )}
                      </div>
                    </div>

                    {/* Closed Trades / History Table */}
                    <div>
                      <h3 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
                        <span>📜</span> Trade History (Closed)
                      </h3>
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
                                  <td className={`py-3 px-6 text-right font-bold ${isProfit ? 'text-emerald-400' : 'text-red-400'}`}>
                                    {isProfit ? '+' : ''}{row.realized_pnl?.toLocaleString('id-ID')}
                                  </td>
                                  <td className={`py-3 px-6 text-right font-bold ${isProfit ? 'text-emerald-400' : 'text-red-400'}`}>
                                    {isProfit ? '+' : ''}{row.realized_pnl_pct?.toFixed(2)}%
                                  </td>
                                </tr>
                              );
                            })}
                            {closedTrades.length === 0 && (
                              <tr>
                                <td colSpan={8} className="py-10 text-center text-slate-500 font-sans">Belum ada riwayat transaksi ditutup.</td>
                              </tr>
                            )}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  </>
                );
              })()}
            </div>
          );
        })()}

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

        {activeTab === 'portfolio' && (
          <div className="space-y-8 animate-fade-in">
            {/* Header */}
            <div>
              <h2 className="text-3xl font-bold text-white mb-2">💼 Portfolio <span className="text-indigo-400">Management</span></h2>
              <p className="text-slate-400">Manajemen holdings aktif, strategi Dollar Cost Averaging (DCA), riwayat transaksi, dan analisis portofolio bertenaga AI.</p>
            </div>

            {/* Sub-Tabs Nav */}
            <div className="flex bg-white/[0.03] backdrop-blur-md p-1.5 rounded-2xl border border-white/5 overflow-x-auto max-w-max">
              {([
                { id: "holdings", label: "📊 Holdings Overview" },
                { id: "dca", label: "💰 DCA Manager" },
                { id: "history", label: "📜 Transaction History" },
                { id: "performance", label: "📈 Performance Report" },
                { id: "ai", label: "🤖 AI Analysis" }
              ] as const).map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setPortfolioTab(tab.id)}
                  className={`px-4 py-2.5 rounded-xl text-sm font-semibold transition whitespace-nowrap ${
                    portfolioTab === tab.id
                      ? "bg-gradient-to-r from-indigo-500 to-purple-500 text-white shadow-lg shadow-indigo-500/20"
                      : "text-slate-400 hover:text-white hover:bg-white/5"
                  }`}
                >
                  {tab.label}
                </button>
              ))}
            </div>

            {/* SUB-TAB 1: HOLDINGS OVERVIEW */}
            {portfolioTab === "holdings" && (
              <div className="space-y-6">
                {/* Summary Cards */}
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                  <div className="bg-white/[0.03] border border-white/5 rounded-2xl p-5">
                    <p className="text-xs text-slate-400 font-bold uppercase tracking-wider mb-1">Total Invested</p>
                    <p className="text-2xl font-black text-white font-mono">
                      Rp {(portfolioSummary.total_invested || 0).toLocaleString("id-ID")}
                    </p>
                  </div>
                  <div className="bg-white/[0.03] border border-white/5 rounded-2xl p-5">
                    <p className="text-xs text-slate-400 font-bold uppercase tracking-wider mb-1">Current Value</p>
                    <p className="text-2xl font-black text-white font-mono">
                      Rp {(portfolioSummary.total_current_value || 0).toLocaleString("id-ID")}
                    </p>
                    {portfolioSummary.total_pnl !== 0 && (
                      <p className={`text-xs font-mono font-bold mt-1 ${portfolioSummary.total_pnl > 0 ? "text-emerald-400" : "text-red-400"}`}>
                        {portfolioSummary.total_pnl > 0 ? "▲ +" : "▼ "}
                        Rp {Math.abs(portfolioSummary.total_pnl).toLocaleString("id-ID")}
                      </p>
                    )}
                  </div>
                  <div className="bg-white/[0.03] border border-white/5 rounded-2xl p-5">
                    <p className="text-xs text-slate-400 font-bold uppercase tracking-wider mb-1">Total P&L</p>
                    <p className={`text-2xl font-black font-mono ${portfolioSummary.total_pnl_pct > 0 ? "text-emerald-400" : portfolioSummary.total_pnl_pct < 0 ? "text-red-400" : "text-white"}`}>
                      {portfolioSummary.total_pnl_pct > 0 ? "+" : ""}{(portfolioSummary.total_pnl_pct || 0).toFixed(2)}%
                    </p>
                    {portfolioSummary.total_pnl !== 0 && (
                      <p className="text-xs text-slate-500 font-mono mt-1">
                        Rp {portfolioSummary.total_pnl.toLocaleString("id-ID")}
                      </p>
                    )}
                  </div>
                  <div className="bg-white/[0.03] border border-white/5 rounded-2xl p-5">
                    <p className="text-xs text-slate-400 font-bold uppercase tracking-wider mb-1">Best Performer</p>
                    <p className="text-2xl font-black text-white truncate">
                      {portfolioSummary.best_performer || "N/A"}
                    </p>
                    {portfolioSummary.best_performer && (
                      <p className="text-xs font-mono font-bold mt-1 text-emerald-400">
                        +{(portfolioSummary.best_pnl_pct || 0).toFixed(2)}%
                      </p>
                    )}
                  </div>
                </div>

                {/* Holdings Table */}
                <div className="bg-white/[0.03] backdrop-blur-md border border-white/5 rounded-3xl p-6">
                  <h3 className="text-lg font-bold text-white mb-4">📋 Holdings</h3>
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm text-left text-slate-300">
                      <thead className="text-xs text-slate-400 uppercase bg-white/5 border-b border-white/5">
                        <tr>
                          <th className="px-4 py-4 rounded-tl-lg">Ticker</th>
                          <th className="px-4 py-4 text-right">Lot</th>
                          <th className="px-4 py-4 text-right">Avg Cost</th>
                          <th className="px-4 py-4 text-right">Current</th>
                          <th className="px-4 py-4 text-right">Value</th>
                          <th className="px-4 py-4 text-right">P&L (Rp)</th>
                          <th className="px-4 py-4 text-right">P&L (%)</th>
                          <th className="px-4 py-4 text-center rounded-tr-lg">Status</th>
                        </tr>
                      </thead>
                      <tbody>
                        {portfolioHoldings.map((h, i) => {
                          const totalInvested = h.avg_cost * h.shares;
                          const pnlValue = h.value - totalInvested;
                          return (
                            <tr key={i} className="border-b border-white/5 hover:bg-white/5 transition duration-150">
                              <td className="px-4 py-4 font-bold text-white text-base">{h.ticker}</td>
                              <td className="px-4 py-4 text-right font-mono">{(h.shares / 100).toFixed(0)}</td>
                              <td className="px-4 py-4 text-right font-mono">Rp {h.avg_cost.toLocaleString("id-ID")}</td>
                              <td className="px-4 py-4 text-right font-mono">Rp {h.current_price.toLocaleString("id-ID")}</td>
                              <td className="px-4 py-4 text-right font-mono">Rp {h.value.toLocaleString("id-ID")}</td>
                              <td className={`px-4 py-4 text-right font-mono font-bold ${pnlValue > 0 ? "text-emerald-400" : pnlValue < 0 ? "text-red-400" : "text-slate-400"}`}>
                                {pnlValue > 0 ? "+" : ""}
                                {pnlValue.toLocaleString("id-ID")}
                              </td>
                              <td className={`px-4 py-4 text-right font-mono font-bold ${h.pnl_pct > 0 ? "text-emerald-400" : h.pnl_pct < 0 ? "text-red-400" : "text-slate-400"}`}>
                                {h.pnl_pct > 0 ? "+" : ""}
                                {h.pnl_pct.toFixed(2)}%
                              </td>
                              <td className="px-4 py-4 text-center">
                                <span className="px-2.5 py-1 rounded bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 text-xs font-semibold uppercase">
                                  Active
                                </span>
                              </td>
                            </tr>
                          );
                        })}
                        {portfolioHoldings.length === 0 && (
                          <tr>
                            <td colSpan={8} className="px-4 py-12 text-center text-slate-500">
                              Belum ada holdings aktif. Tambahkan holdings pertama di bawah.
                            </td>
                          </tr>
                        )}
                      </tbody>
                    </table>
                  </div>
                </div>

                {/* Operations Section */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  {/* Add New Holding */}
                  <div className="bg-white/[0.03] backdrop-blur-md border border-white/5 rounded-3xl p-6">
                    <h3 className="text-lg font-bold text-white mb-4">➕ Add New Holding</h3>
                    <form onSubmit={handleAddHolding} className="space-y-4">
                      <div>
                        <label className="block text-xs font-bold uppercase tracking-wider text-slate-400 mb-2">Ticker (e.g. TLKM)</label>
                        <input
                          type="text"
                          className="w-full bg-[#030712] border border-white/10 rounded-xl px-4 py-3 text-slate-100 font-medium focus:outline-none focus:border-indigo-500"
                          placeholder="TLKM"
                          value={newHoldingTicker}
                          onChange={(e) => setNewHoldingTicker(e.target.value)}
                        />
                      </div>
                      <div className="grid grid-cols-2 gap-4">
                        <div>
                          <label className="block text-xs font-bold uppercase tracking-wider text-slate-400 mb-2">Lot</label>
                          <input
                            type="number"
                            className="w-full bg-[#030712] border border-white/10 rounded-xl px-4 py-3 text-slate-100 font-medium focus:outline-none focus:border-indigo-500"
                            value={newHoldingLots}
                            onChange={(e) => setNewHoldingLots(Number(e.target.value))}
                          />
                        </div>
                        <div>
                          <label className="block text-xs font-bold uppercase tracking-wider text-slate-400 mb-2">Avg Cost (Rp/share)</label>
                          <input
                            type="number"
                            className="w-full bg-[#030712] border border-white/10 rounded-xl px-4 py-3 text-slate-100 font-medium focus:outline-none focus:border-indigo-500"
                            value={newHoldingAvg}
                            onChange={(e) => setNewHoldingAvg(Number(e.target.value))}
                          />
                        </div>
                      </div>
                      <div>
                        <label className="block text-xs font-bold uppercase tracking-wider text-slate-400 mb-2">Notes</label>
                        <input
                          type="text"
                          className="w-full bg-[#030712] border border-white/10 rounded-xl px-4 py-3 text-slate-100 font-medium focus:outline-none focus:border-indigo-500"
                          placeholder="Catatan tambahan..."
                          value={newHoldingNotes}
                          onChange={(e) => setNewHoldingNotes(e.target.value)}
                        />
                      </div>
                      <button
                        type="submit"
                        className="w-full bg-gradient-to-r from-indigo-500 to-purple-500 text-white font-bold py-3 px-4 rounded-xl transition hover:opacity-90 shadow-lg shadow-indigo-500/20"
                      >
                        Add Holding
                      </button>
                    </form>
                  </div>

                  {/* Record Buy/Sell */}
                  <div className="bg-white/[0.03] backdrop-blur-md border border-white/5 rounded-3xl p-6">
                    <h3 className="text-lg font-bold text-white mb-4">💵 Record Buy / Sell</h3>
                    <form onSubmit={handleRecordTransaction} className="space-y-4">
                      <div>
                        <label className="block text-xs font-bold uppercase tracking-wider text-slate-400 mb-2">Type</label>
                        <div className="flex bg-[#030712] p-1 rounded-xl border border-white/10 max-w-max">
                          <button
                            type="button"
                            onClick={() => setRecordTxnType("BUY")}
                            className={`px-4 py-2 rounded-lg text-xs font-bold transition ${
                              recordTxnType === "BUY" ? "bg-emerald-500 text-white shadow-lg" : "text-slate-400 hover:text-white"
                            }`}
                          >
                            BUY
                          </button>
                          <button
                            type="button"
                            onClick={() => setRecordTxnType("SELL")}
                            className={`px-4 py-2 rounded-lg text-xs font-bold transition ${
                              recordTxnType === "SELL" ? "bg-red-500 text-white shadow-lg" : "text-slate-400 hover:text-white"
                            }`}
                          >
                            SELL
                          </button>
                        </div>
                      </div>
                      <div>
                        <label className="block text-xs font-bold uppercase tracking-wider text-slate-400 mb-2">Ticker</label>
                        <select
                          className="w-full bg-[#030712] border border-white/10 rounded-xl px-4 py-3 text-slate-100 font-medium focus:outline-none focus:border-indigo-500"
                          value={recordTxnTicker}
                          onChange={(e) => setRecordTxnTicker(e.target.value)}
                        >
                          <option value="">-- Pilih Saham --</option>
                          {portfolioHoldings.map((h) => (
                            <option key={h.ticker} value={h.ticker}>
                              {h.ticker}
                            </option>
                          ))}
                        </select>
                      </div>
                      <div className="grid grid-cols-2 gap-4">
                        <div>
                          <label className="block text-xs font-bold uppercase tracking-wider text-slate-400 mb-2">Lot</label>
                          <input
                            type="number"
                            className="w-full bg-[#030712] border border-white/10 rounded-xl px-4 py-3 text-slate-100 font-medium focus:outline-none focus:border-indigo-500"
                            value={recordTxnLots}
                            onChange={(e) => setRecordTxnLots(Number(e.target.value))}
                          />
                        </div>
                        <div>
                          <label className="block text-xs font-bold uppercase tracking-wider text-slate-400 mb-2">Price (Rp/share)</label>
                          <input
                            type="number"
                            className="w-full bg-[#030712] border border-white/10 rounded-xl px-4 py-3 text-slate-100 font-medium focus:outline-none focus:border-indigo-500"
                            value={recordTxnPrice}
                            onChange={(e) => setRecordTxnPrice(Number(e.target.value))}
                          />
                        </div>
                      </div>
                      <div>
                        <label className="block text-xs font-bold uppercase tracking-wider text-slate-400 mb-2">Notes</label>
                        <input
                          type="text"
                          className="w-full bg-[#030712] border border-white/10 rounded-xl px-4 py-3 text-slate-100 font-medium focus:outline-none focus:border-indigo-500"
                          placeholder="Catatan..."
                          value={recordTxnNotes}
                          onChange={(e) => setRecordTxnNotes(e.target.value)}
                        />
                      </div>

                      {recordTxnType === "BUY" && buyPreview && (
                        <div className="bg-emerald-500/10 border border-emerald-500/20 text-emerald-300 p-4 rounded-xl text-xs font-mono space-y-1">
                          <p className="font-bold text-white uppercase text-[10px] tracking-wider mb-1">Preview New Avg Cost</p>
                          <p>Avg Cost Saat Ini: <span className="text-white font-bold">Rp {buyPreview.current_avg?.toLocaleString("id-ID")}</span></p>
                          <p>Avg Cost Baru: <span className="text-white font-bold">Rp {buyPreview.new_avg_cost?.toLocaleString("id-ID")}</span></p>
                          <p>Total Lot Setelah Trx: <span className="text-white font-bold">{buyPreview.total_lots_after} Lot</span></p>
                        </div>
                      )}

                      <button
                        type="submit"
                        className={`w-full text-white font-bold py-3 px-4 rounded-xl transition hover:opacity-90 shadow-lg ${
                          recordTxnType === "BUY" ? "bg-emerald-600 shadow-emerald-600/20" : "bg-red-600 shadow-red-600/20"
                        }`}
                      >
                        Record {recordTxnType}
                      </button>
                    </form>
                  </div>
                </div>

                {/* Danger Zone */}
                <div className="bg-red-500/5 border border-red-500/10 rounded-3xl p-6 mt-8">
                  <h4 className="text-lg font-bold text-red-400 mb-2">⚠️ Danger Zone: Reset Portfolio</h4>
                  <p className="text-sm text-slate-400 mb-4">
                    Tindakan ini akan menghapus semua riwayat transaksi, DCA, dan data kepemilikan saham di portofolio secara permanen!
                  </p>
                  <button
                    onClick={handleResetHoldings}
                    className="bg-red-600 hover:bg-red-700 text-white font-bold py-2.5 px-6 rounded-xl text-sm transition"
                  >
                    🚨 Reset All Data Holding
                  </button>
                </div>
              </div>
            )}

            {/* SUB-TAB 2: DCA MANAGER */}
            {portfolioTab === "dca" && (
              <div className="space-y-8">
                {/* Active DCA Strategies */}
                <div className="bg-white/[0.03] backdrop-blur-md border border-white/5 rounded-3xl p-6">
                  <h3 className="text-lg font-bold text-white mb-4">📋 Active DCA Strategies</h3>
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm text-left text-slate-300">
                      <thead className="text-xs text-slate-400 uppercase bg-white/5 border-b border-white/5">
                        <tr>
                          <th className="px-4 py-4 rounded-tl-lg">Ticker</th>
                          <th className="px-4 py-4 text-right">Budget</th>
                          <th className="px-4 py-4 text-right">Used</th>
                          <th className="px-4 py-4 text-right">Remaining</th>
                          <th className="px-4 py-4">Progress</th>
                          <th className="px-4 py-4 text-center">Levels</th>
                          <th className="px-4 py-4 text-right">Next Buy</th>
                          <th className="px-4 py-4 text-center">Status</th>
                          <th className="px-4 py-4 text-center rounded-tr-lg">Action</th>
                        </tr>
                      </thead>
                      <tbody>
                        {dcaStrategies.map((strat, i) => {
                          const usedPct = (strat.used_budget / strat.total_budget) * 100;
                          return (
                            <tr key={i} className="border-b border-white/5 hover:bg-white/5 transition duration-150">
                              <td className="px-4 py-4 font-bold text-white text-base">{strat.ticker}</td>
                              <td className="px-4 py-4 text-right font-mono">Rp {strat.total_budget.toLocaleString("id-ID")}</td>
                              <td className="px-4 py-4 text-right font-mono">Rp {strat.used_budget.toLocaleString("id-ID")}</td>
                              <td className="px-4 py-4 text-right font-mono">Rp {strat.remaining_budget.toLocaleString("id-ID")}</td>
                              <td className="px-4 py-4 min-w-[120px]">
                                <div className="flex items-center gap-2">
                                  <div className="h-2 w-20 bg-slate-800 rounded-full overflow-hidden">
                                    <div
                                      className="h-full bg-gradient-to-r from-indigo-500 to-purple-500 rounded-full"
                                      style={{ width: `${Math.min(usedPct, 100)}%` }}
                                    ></div>
                                  </div>
                                  <span className="text-xs font-mono">{usedPct.toFixed(0)}%</span>
                                </div>
                              </td>
                              <td className="px-4 py-4 text-center font-mono">{strat.dca_count}</td>
                              <td className="px-4 py-4 text-right font-mono text-indigo-300">
                                {strat.next_buy_price ? `Rp ${strat.next_buy_price.toLocaleString("id-ID")}` : "-"}
                              </td>
                              <td className="px-4 py-4 text-center">
                                <span className="px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 text-xs font-semibold">
                                  {strat.status}
                                </span>
                              </td>
                              <td className="px-4 py-4 text-center">
                                <button
                                  onClick={() => handleDeactivateDca(strat.id)}
                                  className="text-red-400 hover:text-red-300 text-xs font-bold uppercase transition"
                                >
                                  Deactivate
                                </button>
                              </td>
                            </tr>
                          );
                        })}
                        {dcaStrategies.length === 0 && (
                          <tr>
                            <td colSpan={9} className="px-4 py-10 text-center text-slate-500">
                              Belum ada DCA strategy aktif.
                            </td>
                          </tr>
                        )}
                      </tbody>
                    </table>
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  {/* Create New DCA */}
                  <div className="bg-white/[0.03] backdrop-blur-md border border-white/5 rounded-3xl p-6">
                    <h3 className="text-lg font-bold text-white mb-4">➕ Create New DCA Strategy</h3>
                    
                    <div className="flex bg-[#030712] p-1 rounded-xl border border-white/10 max-w-max mb-6">
                      <button
                        type="button"
                        onClick={() => {
                          setDcaMode("signal");
                          setPreviewDcaLevels([]);
                        }}
                        className={`px-4 py-2 rounded-lg text-xs font-bold transition ${
                          dcaMode === "signal" ? "bg-indigo-500 text-white shadow-lg" : "text-slate-400 hover:text-white"
                        }`}
                      >
                        From TOP PICKS Signal
                      </button>
                      <button
                        type="button"
                        onClick={() => {
                          setDcaMode("manual");
                          setPreviewDcaLevels([]);
                        }}
                        className={`px-4 py-2 rounded-lg text-xs font-bold transition ${
                          dcaMode === "manual" ? "bg-indigo-500 text-white shadow-lg" : "text-slate-400 hover:text-white"
                        }`}
                      >
                        Manual Input
                      </button>
                    </div>

                    <form onSubmit={handleCreateDca} className="space-y-4">
                      {dcaMode === "signal" ? (
                        <div>
                          <label className="block text-xs font-bold uppercase tracking-wider text-slate-400 mb-2">Pilih Sinyal Top Picks</label>
                          {picks.length > 0 ? (
                            <select
                              className="w-full bg-[#030712] border border-white/10 rounded-xl px-4 py-3 text-slate-100 font-medium focus:outline-none focus:border-indigo-500"
                              value={selectedSignalId || ""}
                              onChange={(e) => {
                                setSelectedSignalId(Number(e.target.value));
                                setPreviewDcaLevels([]);
                              }}
                            >
                              <option value="">-- Pilih Rekomendasi Sinyal --</option>
                              {picks.map((p) => (
                                <option key={p.id} value={p.id}>
                                  {p.ticker} (Entry: {p.entry_low} - {p.max_entry} | Conviction: {p.conviction})
                                </option>
                              ))}
                            </select>
                          ) : (
                            <div className="text-xs text-yellow-400 bg-yellow-500/10 border border-yellow-500/20 p-3 rounded-xl">
                              ⚠️ Belum ada TOP PICKS signal. Run analysis dulu di tab dashboard / top picks.
                            </div>
                          )}
                        </div>
                      ) : (
                        <div className="space-y-4">
                          <div>
                            <label className="block text-xs font-bold uppercase tracking-wider text-slate-400 mb-2">Ticker</label>
                            <div className="flex gap-2">
                              <input
                                type="text"
                                className="flex-1 bg-[#030712] border border-white/10 rounded-xl px-4 py-3 text-slate-100 font-medium focus:outline-none focus:border-indigo-500"
                                placeholder="TLKM"
                                value={manualDcaTicker}
                                onChange={(e) => setManualDcaTicker(e.target.value)}
                              />
                              <button
                                type="button"
                                onClick={handleAiDcaRecommend}
                                className="bg-slate-800 border border-white/10 hover:bg-slate-700 text-white font-bold px-3 rounded-xl text-xs transition"
                              >
                                🤖 AI Entry
                              </button>
                            </div>
                          </div>
                          <div className="grid grid-cols-3 gap-2">
                            <div>
                              <label className="block text-[10px] font-bold uppercase tracking-wider text-slate-400 mb-1">Entry Low</label>
                              <input
                                type="number"
                                className="w-full bg-[#030712] border border-white/10 rounded-xl px-3 py-2.5 text-xs text-slate-100 font-mono focus:outline-none focus:border-indigo-500"
                                value={manualEntryLow}
                                onChange={(e) => setManualEntryLow(Number(e.target.value))}
                              />
                            </div>
                            <div>
                              <label className="block text-[10px] font-bold uppercase tracking-wider text-slate-400 mb-1">Entry High</label>
                              <input
                                type="number"
                                className="w-full bg-[#030712] border border-white/10 rounded-xl px-3 py-2.5 text-xs text-slate-100 font-mono focus:outline-none focus:border-indigo-500"
                                value={manualEntryHigh}
                                onChange={(e) => setManualEntryHigh(Number(e.target.value))}
                              />
                            </div>
                            <div>
                              <label className="block text-[10px] font-bold uppercase tracking-wider text-slate-400 mb-1">Max Entry</label>
                              <input
                                type="number"
                                className="w-full bg-[#030712] border border-white/10 rounded-xl px-3 py-2.5 text-xs text-slate-100 font-mono focus:outline-none focus:border-indigo-500"
                                value={manualMaxEntry}
                                onChange={(e) => setManualMaxEntry(Number(e.target.value))}
                              />
                            </div>
                          </div>
                        </div>
                      )}

                      <div className="grid grid-cols-2 gap-4">
                        <div>
                          <label className="block text-xs font-bold uppercase tracking-wider text-slate-400 mb-2">Total Budget (Rp)</label>
                          <input
                            type="number"
                            className="w-full bg-[#030712] border border-white/10 rounded-xl px-4 py-3 text-slate-100 font-medium focus:outline-none focus:border-indigo-500"
                            value={dcaBudget}
                            onChange={(e) => setDcaBudget(Number(e.target.value))}
                          />
                        </div>
                        <div>
                          <label className="block text-xs font-bold uppercase tracking-wider text-slate-400 mb-2">DCA Levels (2 - 5)</label>
                          <input
                            type="number"
                            min={2}
                            max={5}
                            className="w-full bg-[#030712] border border-white/10 rounded-xl px-4 py-3 text-slate-100 font-medium focus:outline-none focus:border-indigo-500"
                            value={dcaCount}
                            onChange={(e) => setDcaCount(Number(e.target.value))}
                          />
                        </div>
                      </div>

                      <div className="flex gap-3">
                        <button
                          type="button"
                          onClick={handlePreviewDcaLevels}
                          className="flex-1 bg-slate-800 hover:bg-slate-700 text-white font-bold py-3 rounded-xl text-sm transition"
                        >
                          {dcaLevelsLoading ? "Calculating..." : "Preview DCA Levels"}
                        </button>
                        <button
                          type="submit"
                          className="flex-1 bg-gradient-to-r from-indigo-500 to-purple-500 text-white font-bold py-3 rounded-xl text-sm transition hover:opacity-90 shadow-lg shadow-indigo-500/20"
                        >
                          ✅ Activate DCA
                        </button>
                      </div>
                    </form>

                    {/* Preview Dca Levels table */}
                    {previewDcaLevels.length > 0 && (
                      <div className="mt-6 bg-white/[0.02] border border-white/5 rounded-2xl p-4 space-y-3">
                        <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400">Preview Levels:</h4>
                        <div className="overflow-x-auto">
                          <table className="w-full text-xs text-left text-slate-300">
                            <thead>
                              <tr className="border-b border-white/10 text-slate-400">
                                <th className="pb-2">Level</th>
                                <th className="pb-2 text-right">Price</th>
                                <th className="pb-2 text-right">Budget</th>
                                <th className="pb-2 text-right">Actual</th>
                                <th className="pb-2 text-right">Lot</th>
                              </tr>
                            </thead>
                            <tbody>
                              {previewDcaLevels.map((lvl, idx) => (
                                <tr key={idx} className="border-b border-white/[0.02]">
                                  <td className="py-2 font-bold">{lvl.level}</td>
                                  <td className="py-2 text-right font-mono">Rp {lvl.price.toLocaleString("id-ID")}</td>
                                  <td className="py-2 text-right font-mono">Rp {lvl.amount_budget.toLocaleString("id-ID")}</td>
                                  <td className="py-2 text-right font-mono">Rp {lvl.actual_amount.toLocaleString("id-ID")}</td>
                                  <td className="py-2 text-right font-mono">{lvl.lots} Lot</td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      </div>
                    )}
                  </div>

                  {/* DCA Timing Recommendation */}
                  <div className="bg-white/[0.03] backdrop-blur-md border border-white/5 rounded-3xl p-6">
                    <h3 className="text-lg font-bold text-white mb-4">🕐 DCA Timing Recommendation</h3>
                    <div className="space-y-4">
                      <div>
                        <label className="block text-xs font-bold uppercase tracking-wider text-slate-400 mb-2">Select Ticker</label>
                        <select
                          className="w-full bg-[#030712] border border-white/10 rounded-xl px-4 py-3 text-slate-100 font-medium focus:outline-none focus:border-indigo-500"
                          value={timingTicker}
                          onChange={(e) => setTimingTicker(e.target.value)}
                        >
                          <option value="">-- Pilih Saham Anda --</option>
                          {portfolioHoldings.map((h) => (
                            <option key={h.ticker} value={h.ticker}>
                              {h.ticker}
                            </option>
                          ))}
                        </select>
                      </div>

                      <button
                        onClick={handleCheckTiming}
                        disabled={timingLoading}
                        className="w-full bg-slate-800 hover:bg-slate-700 text-white font-bold py-3 rounded-xl text-sm transition"
                      >
                        {timingLoading ? "Checking..." : "Check Timing"}
                      </button>

                      {timingResult && (
                        <div className="bg-[#030712] border border-white/10 rounded-2xl p-5 space-y-4">
                          <div className="flex items-center justify-between">
                            <span className="text-xs text-slate-400 font-bold uppercase">Status</span>
                            <span className={`px-3 py-1 rounded-full text-xs font-bold ${
                              timingResult.status === "IDEAL"
                                ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                                : timingResult.status === "ACCEPTABLE"
                                ? "bg-yellow-500/10 text-yellow-400 border border-yellow-500/20"
                                : timingResult.status === "CAUTION"
                                ? "bg-orange-500/10 text-orange-400 border border-orange-500/20"
                                : "bg-red-500/10 text-red-400 border border-red-500/20"
                            }`}>
                              {timingResult.status === "IDEAL"
                                ? "🟢 IDEAL"
                                : timingResult.status === "ACCEPTABLE"
                                ? "🟡 ACCEPTABLE"
                                : timingResult.status === "CAUTION"
                                ? "🟠 CAUTION"
                                : "🔴 AVOID"}
                            </span>
                          </div>

                          <div className="grid grid-cols-3 gap-2 text-center border-t border-b border-white/5 py-4">
                            <div>
                              <p className="text-[10px] text-slate-400 font-bold uppercase">Current Price</p>
                              <p className="font-mono font-bold text-white mt-1">Rp {timingResult.current_price?.toLocaleString("id-ID")}</p>
                            </div>
                            <div>
                              <p className="text-[10px] text-slate-400 font-bold uppercase">True Cost 1M</p>
                              <p className="font-mono font-bold text-white mt-1">Rp {timingResult.true_cost_1m?.toLocaleString("id-ID")}</p>
                            </div>
                            <div>
                              <p className="text-[10px] text-slate-400 font-bold uppercase">Distance</p>
                              <p className={`font-mono font-bold mt-1 ${timingResult.distance_pct > 0 ? "text-red-400" : "text-emerald-400"}`}>
                                {timingResult.distance_pct > 0 ? "+" : ""}{timingResult.distance_pct?.toFixed(2)}%
                              </p>
                            </div>
                          </div>

                          <div className="text-xs text-slate-300 leading-relaxed bg-white/[0.02] border border-white/5 p-3 rounded-xl">
                            {timingResult.reason}
                          </div>

                          {timingResult.recommended_buy && (
                            <div className="text-xs font-bold text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 p-3.5 rounded-xl flex items-center justify-between">
                              <span>💡 Recommended Buy Price:</span>
                              <span className="font-mono text-white text-sm">Rp {timingResult.recommended_buy.toLocaleString("id-ID")}</span>
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* SUB-TAB 3: TRANSACTION HISTORY */}
            {portfolioTab === "history" && (
              <div className="bg-white/[0.03] backdrop-blur-md border border-white/5 rounded-3xl p-6 space-y-6">
                <div className="flex justify-between items-center flex-wrap gap-4 border-b border-white/5 pb-4">
                  <h3 className="text-lg font-bold text-white">📜 Transaction History</h3>
                  
                  {/* Download CSV button */}
                  {portfolioTxns.length > 0 && (
                    <button
                      onClick={() => {
                        const csvContent =
                          "data:text/csv;charset=utf-8,Date,Ticker,Type,Lots,Price,Amount,Notes\n" +
                          portfolioTxns
                            .map((t) => `${t.transaction_date},${t.ticker},${t.transaction_type},${t.lots},${t.price},${t.amount},"${t.notes || ""}"`)
                            .join("\n");
                        const encodedUri = encodeURI(csvContent);
                        const link = document.createElement("a");
                        link.setAttribute("href", encodedUri);
                        link.setAttribute("download", `transactions_${new Date().toISOString()}.csv`);
                        document.body.appendChild(link);
                        link.click();
                        document.body.removeChild(link);
                      }}
                      className="bg-indigo-500 hover:bg-indigo-600 text-white font-bold py-2 px-4 rounded-xl text-xs transition"
                    >
                      📥 Export to CSV
                    </button>
                  )}
                </div>

                {/* Filters */}
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                  <div>
                    <label className="block text-xs font-bold uppercase tracking-wider text-slate-400 mb-2">Filter Ticker</label>
                    <select
                      className="w-full bg-[#030712] border border-white/10 rounded-xl px-4 py-3 text-slate-100 font-medium focus:outline-none"
                      value={txnFilterTicker}
                      onChange={(e) => setTxnFilterTicker(e.target.value)}
                    >
                      <option value="ALL">ALL</option>
                      {Array.from(new Set(portfolioTxns.map((t) => t.ticker))).map((t) => (
                        <option key={t} value={t}>
                          {t}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="block text-xs font-bold uppercase tracking-wider text-slate-400 mb-2">Filter Type</label>
                    <select
                      className="w-full bg-[#030712] border border-white/10 rounded-xl px-4 py-3 text-slate-100 font-medium focus:outline-none"
                      value={txnFilterType}
                      onChange={(e) => setTxnFilterType(e.target.value)}
                    >
                      <option value="ALL">ALL</option>
                      <option value="BUY">BUY</option>
                      <option value="SELL">SELL</option>
                    </select>
                  </div>
                </div>

                {/* Table */}
                <div className="overflow-x-auto">
                  <table className="w-full text-sm text-left text-slate-300">
                    <thead className="text-xs text-slate-400 uppercase bg-white/5 border-b border-white/5">
                      <tr>
                        <th className="px-4 py-4 rounded-tl-lg">Date</th>
                        <th className="px-4 py-4">Ticker</th>
                        <th className="px-4 py-4">Type</th>
                        <th className="px-4 py-4 text-right">Lot</th>
                        <th className="px-4 py-4 text-right">Price</th>
                        <th className="px-4 py-4 text-right">Amount</th>
                        <th className="px-4 py-4 rounded-tr-lg">Notes</th>
                      </tr>
                    </thead>
                    <tbody>
                      {portfolioTxns
                        .filter((t) => txnFilterTicker === "ALL" || t.ticker === txnFilterTicker)
                        .filter((t) => txnFilterType === "ALL" || t.transaction_type === txnFilterType)
                        .map((t, idx) => (
                          <tr key={idx} className="border-b border-white/5 hover:bg-white/5 transition duration-150">
                            <td className="px-4 py-4">{t.transaction_date}</td>
                            <td className="px-4 py-4 font-bold text-white text-base">{t.ticker}</td>
                            <td className="px-4 py-4">
                              <span className={`px-2.5 py-1 rounded text-xs font-bold border ${
                                t.transaction_type === "BUY"
                                  ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
                                  : "bg-red-500/10 text-red-400 border-red-500/20"
                              }`}>
                                {t.transaction_type}
                              </span>
                            </td>
                            <td className="px-4 py-4 text-right font-mono">{t.lots}</td>
                            <td className="px-4 py-4 text-right font-mono">Rp {t.price.toLocaleString("id-ID")}</td>
                            <td className="px-4 py-4 text-right font-mono">Rp {t.amount.toLocaleString("id-ID")}</td>
                            <td className="px-4 py-4 text-slate-400 italic text-xs max-w-xs truncate">{t.notes}</td>
                          </tr>
                        ))}
                      {portfolioTxns.length === 0 && (
                        <tr>
                          <td colSpan={7} className="px-4 py-10 text-center text-slate-500">
                            Belum ada riwayat transaksi.
                          </td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* SUB-TAB 4: PERFORMANCE REPORT */}
            {portfolioTab === "performance" && (
              <div className="space-y-6">
                {/* Monthly Transaction Flow */}
                <div className="bg-white/[0.03] backdrop-blur-md border border-white/5 rounded-3xl p-6">
                  <h3 className="text-lg font-bold text-white mb-2">📊 Monthly Transaction Flow</h3>
                  <p className="text-xs text-slate-400 mb-6">Distribusi pergerakan dana bersih (Total SELL - Total BUY) per bulan.</p>
                  
                  {/* Visual Bar Chart in pure CSS/Tailwind */}
                  {(() => {
                    const monthlyFlows = getMonthlyFlow();
                    if (monthlyFlows.length === 0) {
                      return <div className="text-center py-10 text-slate-500 text-sm">Belum ada transaksi untuk memetakan bulanan.</div>;
                    }
                    const maxAbsVal = Math.max(...monthlyFlows.map(f => Math.abs(f.net_flow))) || 1;
                    return (
                      <div className="space-y-4">
                        {monthlyFlows.map((flow, idx) => {
                          const val = flow.net_flow;
                          const ratio = Math.min(Math.abs(val) / maxAbsVal, 1);
                          const isPositive = val >= 0;
                          return (
                            <div key={idx} className="flex items-center gap-4 text-xs font-mono">
                              <span className="w-16 font-bold text-slate-400">{flow.month}</span>
                              <div className="flex-1 h-6 bg-slate-900 rounded-lg relative overflow-hidden flex items-center px-2">
                                <div
                                  className={`h-full absolute top-0 left-1/2 transform -translate-x-1/2 flex items-center transition-all ${
                                    isPositive ? "bg-emerald-500/20 text-emerald-400 border-l border-emerald-500" : "bg-red-500/20 text-red-400 border-r border-red-500"
                                  }`}
                                  style={{
                                    width: `${ratio * 50}%`,
                                    left: isPositive ? "50%" : "auto",
                                    right: isPositive ? "auto" : "50%"
                                  }}
                                ></div>
                                <span className={`relative z-10 font-bold ml-auto font-mono ${isPositive ? "text-emerald-400" : "text-red-400"}`}>
                                  {isPositive ? "+" : "-"}Rp {Math.abs(val).toLocaleString("id-ID")}
                                </span>
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    );
                  })()}
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  {/* Per-Ticker Summary */}
                  <div className="bg-white/[0.03] border border-white/5 rounded-3xl p-6">
                    <h3 className="text-lg font-bold text-white mb-4">📋 Per-Ticker Transaction Summary</h3>
                    <div className="overflow-x-auto">
                      <table className="w-full text-sm text-left text-slate-300">
                        <thead>
                          <tr className="border-b border-white/10 text-xs text-slate-400 uppercase">
                            <th className="pb-3">Ticker</th>
                            <th className="pb-3 text-right">Total Amount</th>
                            <th className="pb-3 text-right">Total Lot</th>
                            <th className="pb-3 text-center">Txns</th>
                          </tr>
                        </thead>
                        <tbody>
                          {getTickerStats().map((stat, idx) => (
                            <tr key={idx} className="border-b border-white/5">
                              <td className="py-3 font-bold text-white">{stat.ticker}</td>
                              <td className="py-3 text-right font-mono">Rp {stat.amount.toLocaleString("id-ID")}</td>
                              <td className="py-3 text-right font-mono">{stat.lots} Lot</td>
                              <td className="py-3 text-center font-mono">{stat.count}</td>
                            </tr>
                          ))}
                          {getTickerStats().length === 0 && (
                            <tr>
                              <td colSpan={4} className="py-10 text-center text-slate-500 text-xs">Belum ada transaksi.</td>
                            </tr>
                          )}
                        </tbody>
                      </table>
                    </div>
                  </div>

                  {/* Current Holdings P&L */}
                  <div className="bg-white/[0.03] border border-white/5 rounded-3xl p-6">
                    <h3 className="text-lg font-bold text-white mb-4">💼 Current Holdings P&L</h3>
                    <div className="overflow-x-auto">
                      <table className="w-full text-sm text-left text-slate-300">
                        <thead>
                          <tr className="border-b border-white/10 text-xs text-slate-400 uppercase">
                            <th className="pb-3">Ticker</th>
                            <th className="pb-3 text-right">P&L (Rp)</th>
                            <th className="pb-3 text-right">P&L (%)</th>
                          </tr>
                        </thead>
                        <tbody>
                          {portfolioHoldings.map((h, idx) => {
                            const totalInvested = h.avg_cost * h.shares;
                            const pnlValue = h.value - totalInvested;
                            return (
                              <tr key={idx} className="border-b border-white/5">
                                <td className="py-3 font-bold text-white">{h.ticker}</td>
                                <td className={`py-3 text-right font-mono font-bold ${pnlValue > 0 ? "text-emerald-400" : pnlValue < 0 ? "text-red-400" : "text-slate-400"}`}>
                                  {pnlValue > 0 ? "+" : ""}
                                  {pnlValue.toLocaleString("id-ID")}
                                </td>
                                <td className={`py-3 text-right font-mono font-bold ${h.pnl_pct > 0 ? "text-emerald-400" : h.pnl_pct < 0 ? "text-red-400" : "text-slate-400"}`}>
                                  {h.pnl_pct > 0 ? "+" : ""}
                                  {h.pnl_pct.toFixed(2)}%
                                </td>
                              </tr>
                            );
                          })}
                          {portfolioHoldings.length === 0 && (
                            <tr>
                              <td colSpan={3} className="py-10 text-center text-slate-500 text-xs">Belum ada holdings aktif.</td>
                            </tr>
                          )}
                        </tbody>
                      </table>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* SUB-TAB 5: AI ANALYSIS */}
            {portfolioTab === "ai" && (
              <div className="space-y-6">
                {/* AI Portfolio advisor control panel */}
                <div className="bg-white/[0.03] backdrop-blur-md border border-white/5 rounded-3xl p-6">
                  <h3 className="text-lg font-bold text-white mb-2">🤖 AI Portfolio Analysis</h3>
                  <p className="text-xs text-slate-400 mb-6">
                    Analisis portofolio komprehensif: rebalancing target, prioritas DCA bulan ini, analisis risiko diversifikasi, serta atribusi performa.
                  </p>

                  <div className="flex flex-col sm:flex-row items-end gap-4">
                    <div className="flex-1">
                      <label className="block text-xs font-bold uppercase tracking-wider text-slate-400 mb-2">Monthly DCA Budget (Rp)</label>
                      <input
                        type="number"
                        className="w-full bg-[#030712] border border-white/10 rounded-xl px-4 py-3 text-slate-100 font-medium focus:outline-none"
                        value={aiMonthlyBudget}
                        onChange={(e) => setAiMonthlyBudget(Number(e.target.value))}
                      />
                    </div>
                    <button
                      onClick={handleRunAiAnalysis}
                      disabled={aiAnalysisLoading}
                      className="bg-gradient-to-r from-indigo-500 to-purple-500 text-white font-bold py-3 px-6 rounded-xl transition hover:opacity-90 shadow-lg shadow-indigo-500/20 disabled:opacity-50"
                    >
                      {aiAnalysisLoading ? "🤖 AI sedang menganalisis..." : "🤖 Get AI Portfolio Analysis"}
                    </button>
                  </div>
                </div>

                {/* AI Analysis Loading spinner */}
                {aiAnalysisLoading && (
                  <div className="bg-white/[0.02] border border-white/5 rounded-3xl p-12 text-center space-y-4">
                    <div className="w-10 h-10 border-4 border-indigo-500 border-t-transparent rounded-full animate-spin mx-auto"></div>
                    <p className="text-slate-400 font-medium text-sm">AI sedang menganalisis portfolio... (proses LLM & perdebatan bisa memakan waktu 30-60 detik)</p>
                  </div>
                )}

                {/* AI Analysis Result */}
                {!aiAnalysisLoading && aiAnalysisResult && (
                  <div className="space-y-6 animate-fade-in">
                    {/* Timestamp */}
                    {aiAnalysisResult.generated_at && (
                      <p className="text-xs text-slate-500 font-mono">
                        Generated: {aiAnalysisResult.generated_at.substring(0, 19).replace("T", " ")} WIB
                      </p>
                    )}

                    {/* Summary Card */}
                    {aiAnalysisResult.summary && (
                      <div className="bg-indigo-500/10 border border-indigo-500/20 p-5 rounded-2xl text-indigo-300 text-sm leading-relaxed">
                        <span className="font-bold text-white block mb-1">📋 AI Summary:</span>
                        {aiAnalysisResult.summary}
                      </div>
                    )}

                    {/* Section 1: Rebalancing */}
                    <div className="bg-white/[0.03] border border-white/5 rounded-3xl p-6 space-y-4">
                      <h4 className="text-base font-bold text-white flex items-center gap-2">⚖️ Rebalancing Recommendations</h4>
                      {aiAnalysisResult.rebalancing?.needed ? (
                        <div className="text-yellow-400 bg-yellow-500/10 border border-yellow-500/20 p-3.5 rounded-xl text-xs font-semibold">
                          ⚠️ Rebalancing diperlukan agar sesuai target diversifikasi profil Anda.
                        </div>
                      ) : (
                        <div className="text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 p-3.5 rounded-xl text-xs font-semibold">
                          ✅ Portfolio saat ini sudah terdistribusi dengan seimbang.
                        </div>
                      )}

                      <div className="grid grid-cols-2 gap-4 text-sm mt-2">
                        <div className="bg-[#030712] p-4 rounded-xl border border-white/5">
                          <p className="text-xs font-bold text-red-400 uppercase tracking-wider mb-2">🔴 Overweight (Porsi Terlalu Besar):</p>
                          {aiAnalysisResult.rebalancing?.overweight?.length > 0 ? (
                            <ul className="list-disc pl-5 text-slate-300 space-y-1">
                              {aiAnalysisResult.rebalancing.overweight.map((t: string) => (
                                <li key={t}>{t}</li>
                              ))}
                            </ul>
                          ) : (
                            <p className="text-slate-500 text-xs italic">Tidak ada</p>
                          )}
                        </div>
                        <div className="bg-[#030712] p-4 rounded-xl border border-white/5">
                          <p className="text-xs font-bold text-yellow-400 uppercase tracking-wider mb-2">🟡 Underweight (Porsi Terlalu Kecil):</p>
                          {aiAnalysisResult.rebalancing?.underweight?.length > 0 ? (
                            <ul className="list-disc pl-5 text-slate-300 space-y-1">
                              {aiAnalysisResult.rebalancing.underweight.map((t: string) => (
                                <li key={t}>{t}</li>
                              ))}
                            </ul>
                          ) : (
                            <p className="text-slate-500 text-xs italic">Tidak ada</p>
                          )}
                        </div>
                      </div>

                      {/* Action Plan */}
                      {aiAnalysisResult.rebalancing?.actions?.length > 0 && (
                        <div className="mt-4">
                          <p className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-3">Suggested Action Plan:</p>
                          <div className="overflow-x-auto bg-[#030712] rounded-xl border border-white/5">
                            <table className="w-full text-xs text-left text-slate-300">
                              <thead>
                                <tr className="border-b border-white/10 text-slate-400 uppercase">
                                  <th className="px-4 py-3">Ticker</th>
                                  <th className="px-4 py-3">Action</th>
                                  <th className="px-4 py-3 text-right">Amount (Rp)</th>
                                  <th className="px-4 py-3">Reason</th>
                                </tr>
                              </thead>
                              <tbody>
                                {aiAnalysisResult.rebalancing.actions.map((act: any, idx: number) => (
                                  <tr key={idx} className="border-b border-white/[0.02]">
                                    <td className="px-4 py-3 font-bold text-white">{act.ticker}</td>
                                    <td className="px-4 py-3">
                                      <span className={`px-2 py-0.5 rounded font-bold ${
                                        act.action === "REDUCE"
                                          ? "bg-red-500/10 text-red-400"
                                          : act.action === "INCREASE"
                                          ? "bg-emerald-500/10 text-emerald-400"
                                          : "bg-slate-500/10 text-slate-400"
                                      }`}>
                                        {act.action === "REDUCE" ? "🔻 REDUCE" : act.action === "INCREASE" ? "🔺 INCREASE" : "⏸️ HOLD"}
                                      </span>
                                    </td>
                                    <td className="px-4 py-3 text-right font-mono">Rp {act.amount?.toLocaleString("id-ID")}</td>
                                    <td className="px-4 py-3 text-slate-400 italic">{act.reason}</td>
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          </div>
                        </div>
                      )}
                    </div>

                    {/* Section 2: DCA Priority */}
                    <div className="bg-white/[0.03] border border-white/5 rounded-3xl p-6 space-y-4">
                      <h4 className="text-base font-bold text-white">💰 DCA Priority This Month (Budget: Rp {aiMonthlyBudget.toLocaleString("id-ID")})</h4>
                      <div className="space-y-3">
                        {aiAnalysisResult.dca_priority?.map((p: any, idx: number) => (
                          <div key={idx} className="bg-[#030712] border border-white/5 p-4 rounded-xl flex flex-col md:flex-row gap-4 justify-between items-start md:items-center">
                            <div className="flex items-center gap-3">
                              <span className="text-lg font-black text-indigo-400 font-mono">#{p.rank}</span>
                              <div>
                                <h5 className="font-bold text-white text-base">{p.ticker}</h5>
                                <p className="text-[10px] text-slate-505 font-medium">
                                  Timing: <span className="text-slate-300 font-mono font-bold">{p.timing_status}</span> | Conviction: <span className="text-slate-300 font-mono font-bold">{p.conviction}</span>
                                </p>
                              </div>
                            </div>
                            <div className="text-right">
                              <p className="text-xs text-slate-400 font-bold uppercase">Alokasi Budget</p>
                              <p className="text-lg font-mono font-black text-emerald-400">Rp {p.allocation?.toLocaleString("id-ID")}</p>
                            </div>
                            <div className="text-xs text-slate-400 italic max-w-sm border-t md:border-t-0 md:border-l border-white/5 pt-2 md:pt-0 md:pl-4">
                              {p.reasoning}
                            </div>
                          </div>
                        ))}
                        {(!aiAnalysisResult.dca_priority || aiAnalysisResult.dca_priority.length === 0) && (
                          <p className="text-slate-505 text-xs italic text-center py-4">Tidak ada rekomendasi alokasi DCA priority dari AI saat ini.</p>
                        )}
                      </div>
                    </div>

                    {/* Section 3: Risk Analysis */}
                    <div className="bg-white/[0.03] border border-white/5 rounded-3xl p-6 space-y-4">
                      <h4 className="text-base font-bold text-white">⚠️ Risk Analysis</h4>
                      <div className="grid grid-cols-2 gap-4 text-center">
                        <div className="bg-[#030712] p-4 rounded-xl border border-white/5">
                          <p className="text-xs text-slate-400 font-bold uppercase tracking-wider mb-1">Risk Level</p>
                          <p className={`text-xl font-bold font-mono ${
                            aiAnalysisResult.risk_analysis?.risk_level === "LOW" ? "text-emerald-400" : aiAnalysisResult.risk_analysis?.risk_level === "HIGH" ? "text-red-400" : "text-yellow-400"
                          }`}>
                            {aiAnalysisResult.risk_analysis?.risk_level === "LOW" ? "🟢 LOW" : aiAnalysisResult.risk_analysis?.risk_level === "HIGH" ? "🔴 HIGH" : "🟡 MEDIUM"}
                          </p>
                        </div>
                        <div className="bg-[#030712] p-4 rounded-xl border border-white/5">
                          <p className="text-xs text-slate-400 font-bold uppercase tracking-wider mb-1">Diversification Score</p>
                          <p className="text-xl font-black text-indigo-400 font-mono">{aiAnalysisResult.risk_analysis?.diversification_score || 0} / 10</p>
                        </div>
                      </div>

                      {/* Sector Concentration */}
                      {aiAnalysisResult.risk_analysis?.sector_concentration && Object.keys(aiAnalysisResult.risk_analysis.sector_concentration).length > 0 && (
                        <div>
                          <p className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-2">Sector Concentration:</p>
                          <div className="overflow-x-auto bg-[#030712] rounded-xl border border-white/5">
                            <table className="w-full text-xs text-left text-slate-300">
                              <thead>
                                <tr className="border-b border-white/10 text-slate-400 uppercase">
                                  <th className="px-4 py-2.5">Sector</th>
                                  <th className="px-4 py-2.5 text-right">Weight (%)</th>
                                </tr>
                              </thead>
                              <tbody>
                                {Object.entries(aiAnalysisResult.risk_analysis.sector_concentration).map(([sec, weight]: any, idx) => (
                                  <tr key={idx} className="border-b border-white/[0.02]">
                                    <td className="px-4 py-2.5 font-bold text-white">{sec}</td>
                                    <td className="px-4 py-2.5 text-right font-mono">{weight}%</td>
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          </div>
                        </div>
                      )}

                      {/* Recommendations */}
                      {aiAnalysisResult.risk_analysis?.recommendations?.length > 0 && (
                        <div>
                          <p className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-2">AI Risk Mitigation:</p>
                          <ul className="list-disc pl-5 text-slate-300 space-y-1 text-xs">
                            {aiAnalysisResult.risk_analysis.recommendations.map((rec: string, idx: number) => (
                              <li key={idx}>{rec}</li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </div>

                    {/* Section 4: Performance Attribution */}
                    <div className="bg-white/[0.03] border border-white/5 rounded-3xl p-6 space-y-4">
                      <h4 className="text-base font-bold text-white">📊 Performance Attribution</h4>
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div className="bg-[#030712] p-4 rounded-xl border border-white/5 space-y-2">
                          <p className="text-xs font-bold text-emerald-400 uppercase tracking-wider">🏆 Best Performer:</p>
                          {aiAnalysisResult.performance_attribution?.best_performer && typeof aiAnalysisResult.performance_attribution.best_performer === "object" ? (
                            <div>
                              <p className="text-lg font-black text-white">{aiAnalysisResult.performance_attribution.best_performer.ticker}</p>
                              <p className="text-xl font-mono font-black text-emerald-400">+{aiAnalysisResult.performance_attribution.best_performer.return_pct?.toFixed(2)}%</p>
                              <p className="text-xs text-slate-400 italic mt-1">{aiAnalysisResult.performance_attribution.best_performer.reason}</p>
                            </div>
                          ) : (
                            <p className="text-slate-300 text-sm">{aiAnalysisResult.performance_attribution?.best_performer || "N/A"}</p>
                          )}
                        </div>
                        <div className="bg-[#030712] p-4 rounded-xl border border-white/5 space-y-2">
                          <p className="text-xs font-bold text-red-400 uppercase tracking-wider">📉 Worst Performer:</p>
                          {aiAnalysisResult.performance_attribution?.worst_performer && typeof aiAnalysisResult.performance_attribution.worst_performer === "object" ? (
                            <div>
                              <p className="text-lg font-black text-white">{aiAnalysisResult.performance_attribution.worst_performer.ticker}</p>
                              <p className="text-xl font-mono font-black text-red-400">{aiAnalysisResult.performance_attribution.worst_performer.return_pct?.toFixed(2)}%</p>
                              <p className="text-xs text-slate-400 italic mt-1">{aiAnalysisResult.performance_attribution.worst_performer.reason}</p>
                            </div>
                          ) : (
                            <p className="text-slate-300 text-sm">{aiAnalysisResult.performance_attribution?.worst_performer || "N/A"}</p>
                          )}
                        </div>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        )}

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

      {/* Floating Toast Container */}
      <div className="fixed top-6 right-6 z-[9999] space-y-3 pointer-events-none max-w-sm w-full font-sans">
        {toasts.map(toast => (
          <div 
            key={toast.id} 
            className={`p-4 rounded-2xl border shadow-2xl flex items-start gap-3 pointer-events-auto transition-all duration-300 bg-[#0f172a]/95 backdrop-blur-md ${
              toast.type === 'success' ? 'border-emerald-500/20 text-emerald-400' :
              toast.type === 'error' ? 'border-red-500/20 text-red-400' :
              'border-indigo-500/20 text-indigo-400'
            }`}
          >
            <span className="text-lg">
              {toast.type === 'success' ? '🟢' : toast.type === 'error' ? '🔴' : '🔵'}
            </span>
            <div className="flex-1 text-xs font-bold leading-snug">
              {toast.message}
            </div>
            <button 
              onClick={() => setToasts(prev => prev.filter(t => t.id !== toast.id))}
              className="text-slate-500 hover:text-white transition text-xs font-mono px-1 cursor-pointer"
            >
              ✕
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
