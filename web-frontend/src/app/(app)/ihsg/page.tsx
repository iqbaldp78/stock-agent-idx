"use client";
import React, { useState, useEffect } from 'react';
import { useApp } from '../../context/AppContext';

export default function IhsgPage() {
  const { showToast } = useApp();
  const [activeTab, setActiveTab] = useState<'live' | 'backtest' | 'outlook'>('live');
  const [ihsgData, setIhsgData] = useState<any>(null);
  const [ihsgLoading, setIhsgLoading] = useState(false);
  const [ihsgError, setIhsgError] = useState("");
  const [currentPage, setCurrentPage] = useState(1);

  // Backtest State
  const [backtestYears, setBacktestYears] = useState<number>(3);
  const [backtestData, setBacktestData] = useState<any>(null);
  const [backtestLoading, setBacktestLoading] = useState(false);
  const [backtestError, setBacktestError] = useState("");
  const [backtestPage, setBacktestPage] = useState(1);

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

  const fetchBacktestData = async (years: number) => {
    setBacktestLoading(true);
    setBacktestError("");
    try {
      const res = await fetch(`/api/ihsg/backtest?years=${years}`);
      if (!res.ok) throw new Error("Gagal mengambil data backtest IHSG");
      const data = await res.json();
      setBacktestData(data);
    } catch (err: any) {
      setBacktestError(err.message || "Gagal memuat backtest");
    } finally {
      setBacktestLoading(false);
    }
  };

  useEffect(() => {
    fetchIhsgData();
  }, []);

  useEffect(() => {
    if (activeTab === 'backtest' && !backtestData && !backtestLoading) {
      fetchBacktestData(backtestYears);
    }
  }, [activeTab]);

  const handlePeriodChange = (years: number) => {
    setBacktestYears(years);
    fetchBacktestData(years);
  };

  return (
    <div className="space-y-6 animate-fade-in">
      <div>
        <h2 className="text-3xl font-bold text-text mb-2">IHSG <span className="text-accent">Predictor</span></h2>
        <p className="text-secondary">Analisis komparatif pergerakan IHSG, pengujian backtest historis, serta deteksi 1-Year Technical Outlook & Reversal Pivot.</p>
      </div>

      {/* TABS NAVIGATION */}
      <div className="flex flex-wrap items-center gap-2 border-b border-border/60 pb-3">
        <button
          onClick={() => setActiveTab('live')}
          className={`px-5 py-2.5 rounded-2xl font-bold text-sm transition-all duration-200 cursor-pointer flex items-center gap-2 ${
            activeTab === 'live'
              ? 'bg-accent text-background shadow-lg shadow-accent/25 scale-[1.02]'
              : 'bg-card/40 text-secondary hover:text-text hover:bg-card border border-border/40'
          }`}
        >
          <span>🔮</span> Live Prediction & Track Record
        </button>
        <button
          onClick={() => setActiveTab('backtest')}
          className={`px-5 py-2.5 rounded-2xl font-bold text-sm transition-all duration-200 cursor-pointer flex items-center gap-2 ${
            activeTab === 'backtest'
              ? 'bg-accent text-background shadow-lg shadow-accent/25 scale-[1.02]'
              : 'bg-card/40 text-secondary hover:text-text hover:bg-card border border-border/40'
          }`}
        >
          <span>🧪</span> Backtest Strategi IHSG
        </button>
        <button
          onClick={() => setActiveTab('outlook')}
          className={`px-5 py-2.5 rounded-2xl font-bold text-sm transition-all duration-200 cursor-pointer flex items-center gap-2 ${
            activeTab === 'outlook'
              ? 'bg-accent text-background shadow-lg shadow-accent/25 scale-[1.02]'
              : 'bg-card/40 text-secondary hover:text-text hover:bg-card border border-border/40'
          }`}
        >
          <span>🌐</span> 1-Year Outlook & Reversal Detector
        </button>
      </div>

      {ihsgLoading && (
        <div className="flex flex-col items-center justify-center py-20 gap-4">
          <span className="w-10 h-10 border-4 border-accent border-t-transparent rounded-full animate-spin"></span>
          <span className="text-secondary font-medium">Menganalisis pergerakan IHSG...</span>
        </div>
      )}

      {ihsgError && (
        <div className="p-4 bg-loss/10 border border-loss/20 text-red-300 rounded-2xl text-center">⚠️ {ihsgError}</div>
      )}

      {!ihsgLoading && !ihsgError && ihsgData && ihsgData.latest && (
        <>
          {/* ================= TAB 1: LIVE PREDICTION ================= */}
          {activeTab === 'live' && (() => {
            const latest = ihsgData.latest;
            const realtime = ihsgData.realtime || {};
            const history = ihsgData.history || [];
            const scores = latest.component_scores || {};
            const drivers = latest.key_drivers || [];
            const risks = latest.risks || [];
            const isRealtime = realtime.source === 'stockbit';

            return (
              <div className="space-y-6">
                {isRealtime && (
                  <div className="bg-gradient-to-r from-accent/20 via-accent/10 to-transparent border border-accent/30 rounded-3xl p-6 flex items-start gap-4">
                    <div className="w-12 h-12 bg-accent/30 rounded-full flex items-center justify-center text-xl flex-shrink-0">📡</div>
                    <div className="flex-1">
                      <h4 className="text-sm font-bold text-accent tracking-wider uppercase mb-2">IHSG Realtime</h4>
                      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                        <div>
                          <p className="text-xs text-secondary font-semibold uppercase mb-1">Current Price</p>
                          <p className="text-2xl font-black text-text font-mono">{realtime.price?.toLocaleString('id-ID')}</p>
                        </div>
                        <div>
                          <p className="text-xs text-secondary font-semibold uppercase mb-1">Prev Close</p>
                          <p className="text-2xl font-black text-secondary font-mono">{realtime.prev_close?.toLocaleString('id-ID')}</p>
                        </div>
                        <div>
                          <p className="text-xs text-secondary font-semibold uppercase mb-1">Change</p>
                          <p className={`text-2xl font-black font-mono ${realtime.change >= 0 ? 'text-profit' : 'text-loss'}`}>
                            {realtime.change >= 0 ? '+' : ''}{realtime.change?.toLocaleString('id-ID')}
                          </p>
                        </div>
                        <div>
                          <p className="text-xs text-secondary font-semibold uppercase mb-1">Change %</p>
                          <p className={`text-2xl font-black font-mono ${realtime.change_pct >= 0 ? 'text-profit' : 'text-loss'}`}>
                            {realtime.change_pct >= 0 ? '+' : ''}{realtime.change_pct?.toFixed(2)}%
                          </p>
                        </div>
                      </div>
                      <p className="text-xs text-secondary/60 mt-3">Updated: {realtime.timestamp}</p>
                    </div>
                  </div>
                )}

                {ihsgData.accuracy && ihsgData.accuracy.total > 0 && (
                  <div className="bg-accent/10 border border-accent/20 rounded-2xl p-4 flex items-center gap-4">
                    <div className="w-12 h-12 bg-accent/20 rounded-full flex items-center justify-center text-xl">🎯</div>
                    <div>
                      <h4 className="text-sm font-bold text-accent tracking-wider uppercase mb-1">Track Record Akurasi</h4>
                      <p className="text-text font-medium">Akurasi Arah (Historical): <span className="text-profit font-bold">{ihsgData.accuracy.percentage}%</span> ({ihsgData.accuracy.correct}/{ihsgData.accuracy.total} hari prediksi tepat)</p>
                    </div>
                  </div>
                )}

                <div className="grid grid-cols-3 gap-6 bg-card backdrop-blur-md border border-border rounded-3xl p-6 text-center">
                  <div>
                    <p className="text-xs text-secondary font-bold uppercase tracking-wider mb-2">Confidence</p>
                    <div className="flex items-center justify-center gap-2">
                      <span className={`inline-block w-3 h-3 rounded-full ${latest.confidence === 'HIGH' ? 'bg-emerald-400 shadow-[0_0_10px_rgba(52,211,153,0.5)]' : latest.confidence === 'MEDIUM' ? 'bg-amber-400 shadow-[0_0_10px_rgba(251,191,36,0.5)]' : 'bg-red-400 shadow-[0_0_10px_rgba(248,113,113,0.5)]'}`}></span>
                      <span className="text-xl md:text-2xl font-black text-text uppercase tracking-wide">{latest.confidence}</span>
                    </div>
                  </div>
                  <div>
                    <p className="text-xs text-secondary font-bold uppercase tracking-wider mb-2">Direction</p>
                    <p className={`text-xl md:text-2xl font-black uppercase tracking-wide ${latest.direction === 'BULLISH' ? 'text-profit' : latest.direction === 'BEARISH' ? 'text-loss' : 'text-secondary'}`}>{latest.direction}</p>
                  </div>
                  <div>
                    <p className="text-xs text-secondary font-bold uppercase tracking-wider mb-2">Volatility</p>
                    <p className="text-xl md:text-2xl font-black text-text uppercase tracking-wide">{latest.volatility_level}</p>
                  </div>
                </div>

                <div>
                  <h3 className="text-lg font-bold text-text mb-4 flex items-center gap-2"><span>📊</span> Price Predictions</h3>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    {[
                      { label: 'D+1', price: latest.day_1_price, pct: latest.day_1_pct },
                      { label: 'D+3', price: latest.day_3_price, pct: latest.day_3_pct },
                      { label: 'D+5', price: latest.day_5_price, pct: latest.day_5_pct },
                      { label: 'D+7', price: latest.day_7_price, pct: latest.day_7_pct },
                    ].map((item, idx) => (
                      <div key={idx} className="bg-card border border-border rounded-2xl p-5 font-mono">
                        <p className="text-xs text-secondary font-bold font-sans uppercase mb-2">{item.label} Prediction</p>
                        <p className="text-xl font-bold text-text">{item.price?.toLocaleString('id-ID')}</p>
                        <p className={`text-xs mt-1 font-bold ${item.pct >= 0 ? 'text-profit' : 'text-loss'}`}>
                          {item.pct >= 0 ? '+' : ''}{item.pct?.toFixed(2)}%
                        </p>
                      </div>
                    ))}
                  </div>
                </div>

                <div>
                  <h3 className="text-lg font-bold text-text mb-4 flex items-center gap-2"><span>⚙️</span> Component Scores</h3>
                  <div className="grid grid-cols-2 md:grid-cols-5 gap-4 bg-card border border-border rounded-3xl p-6">
                    {['momentum', 'breadth', 'macro', 'sectors', 'news'].map((key) => (
                      <div key={key}>
                        <p className="text-xs text-secondary font-bold uppercase tracking-wider mb-2">{key.charAt(0).toUpperCase() + key.slice(1)}</p>
                        <p className="text-2xl font-black text-text font-mono">{scores[key] !== undefined ? scores[key].toFixed(2) : '-'}</p>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                  <div className="space-y-6">
                    <div className="bg-card border border-border rounded-3xl p-6">
                      <h3 className="text-lg font-bold text-text mb-4 flex items-center gap-2"><span>📝</span> Reasoning & Analysis</h3>
                      <div className="text-secondary text-sm leading-relaxed whitespace-pre-wrap font-sans">{latest.reasoning || 'No analysis reasoning details available.'}</div>
                    </div>
                  </div>
                  <div className="space-y-6">
                    <div className="bg-card border border-border rounded-3xl p-6">
                      <h3 className="text-lg font-bold text-text mb-4 flex items-center gap-2"><span className="text-profit">✓</span> Key Drivers</h3>
                      {drivers.length > 0 ? (
                        <ul className="space-y-2.5">{drivers.map((driver: string, i: number) => (<li key={i} className="flex items-start gap-3 text-secondary text-sm"><span className="text-profit mt-0.5">•</span><span>{driver}</span></li>))}</ul>
                      ) : <p className="text-secondary text-sm">No drivers identified.</p>}
                    </div>
                    <div className="bg-card border border-border rounded-3xl p-6">
                      <h3 className="text-lg font-bold text-text mb-4 flex items-center gap-2"><span className="text-loss">⚠️</span> Risk Factors</h3>
                      {risks.length > 0 ? (
                        <ul className="space-y-2.5">{risks.map((risk: string, i: number) => (<li key={i} className="flex items-start gap-3 text-secondary text-sm"><span className="text-loss mt-0.5">•</span><span>{risk}</span></li>))}</ul>
                      ) : <p className="text-secondary text-sm">No major risks identified.</p>}
                    </div>
                  </div>
                </div>

                <div>
                  <h3 className="text-lg font-bold text-text mb-4 flex items-center gap-2"><span>📈</span> Historical Predictions</h3>
                  <div className="overflow-x-auto rounded-2xl border border-border bg-background/40">
                    <table className="w-full text-left border-collapse text-sm">
                      <thead>
                        <tr className="border-b border-border text-xs font-bold uppercase tracking-wider text-secondary bg-white/5">
                          <th className="py-3.5 px-6">Tanggal</th>
                          <th className="py-3.5 px-6 text-right">Current Index</th>
                          <th className="py-3.5 px-6 text-right">D+1 Predicted</th>
                          <th className="py-3.5 px-6 text-right">D+1 Change</th>
                          <th className="py-3.5 px-6 text-center">Direction</th>
                          <th className="py-3.5 px-6 text-center">Confidence</th>
                          <th className="py-3.5 px-6 text-center">Status Validasi</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-white/5 text-secondary font-mono">
                        {(() => {
                          const ITEMS_PER_PAGE = 10;
                          const totalPages = Math.ceil(history.length / ITEMS_PER_PAGE);
                          const safeCurrentPage = Math.max(1, Math.min(currentPage, totalPages || 1));
                          const paginatedHistory = history.slice((safeCurrentPage - 1) * ITEMS_PER_PAGE, safeCurrentPage * ITEMS_PER_PAGE);
                          
                          return paginatedHistory.map((row: any, idx: number) => (
                            <tr key={idx} className="hover:bg-white/5 transition">
                              <td className="py-3.5 px-6 font-sans text-text font-medium">{row.run_date}</td>
                              <td className="py-3.5 px-6 text-right">{row.current_price?.toLocaleString('id-ID')}</td>
                              <td className="py-3.5 px-6 text-right">{row.day_1_price?.toLocaleString('id-ID')}</td>
                              <td className={`py-3.5 px-6 text-right font-bold ${row.day_1_pct >= 0 ? 'text-profit' : 'text-loss'}`}>{row.day_1_pct >= 0 ? '+' : ''}{row.day_1_pct?.toFixed(2)}%</td>
                              <td className="py-3.5 px-6 text-center">
                                <span className={`px-2.5 py-0.5 rounded text-[11px] font-sans font-bold uppercase tracking-wider ${row.direction === 'BULLISH' ? 'bg-profit/10 text-profit border border-profit/20' : row.direction === 'BEARISH' ? 'bg-loss/10 text-loss border border-loss/20' : 'bg-slate-500/10 text-secondary border border-slate-500/20'}`}>{row.direction}</span>
                              </td>
                              <td className="py-3.5 px-6 text-center">
                                <span className={`px-2.5 py-0.5 rounded text-[11px] font-sans font-bold uppercase tracking-wider ${row.confidence === 'HIGH' ? 'bg-profit/10 text-profit border border-profit/20' : row.confidence === 'MEDIUM' ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20' : 'bg-loss/10 text-loss border border-loss/20'}`}>{row.confidence}</span>
                              </td>
                              <td className="py-3.5 px-6 text-center font-sans">
                                {row.is_correct === true && <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-bold bg-profit/20 text-profit border border-profit/30">Benar ✅</span>}
                                {row.is_correct === false && <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-bold bg-loss/20 text-loss border border-loss/30">Salah ❌</span>}
                                {row.is_correct === null && <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-bold bg-gray-500/20 text-gray-400 border border-gray-500/30">Pending ⏳</span>}
                              </td>
                            </tr>
                          ));
                        })()}
                        {history.length === 0 && <tr><td colSpan={7} className="py-10 text-center text-secondary font-sans">Belum ada riwayat prediksi.</td></tr>}
                      </tbody>
                    </table>
                  </div>

                  {history.length > 10 && (
                    <div className="flex flex-col sm:flex-row items-center justify-between mt-4 px-2 gap-4">
                      <p className="text-xs text-secondary font-medium">
                        Menampilkan {Math.min(history.length, (currentPage - 1) * 10 + 1)} - {Math.min(history.length, currentPage * 10)} dari {history.length} prediksi
                      </p>
                      <div className="flex items-center gap-3">
                        <button
                          onClick={() => setCurrentPage(prev => Math.max(1, prev - 1))}
                          disabled={currentPage === 1}
                          className="px-3 py-1.5 rounded-lg border border-border text-xs font-semibold text-text hover:bg-white/5 transition disabled:opacity-40 disabled:hover:bg-transparent cursor-pointer disabled:cursor-not-allowed"
                        >
                          Sebelumnya
                        </button>
                        <span className="text-xs text-text font-mono">
                          {currentPage} / {Math.ceil(history.length / 10)}
                        </span>
                        <button
                          onClick={() => setCurrentPage(prev => Math.min(Math.ceil(history.length / 10), prev + 1))}
                          disabled={currentPage === Math.ceil(history.length / 10)}
                          className="px-3 py-1.5 rounded-lg border border-border text-xs font-semibold text-text hover:bg-white/5 transition disabled:opacity-40 disabled:hover:bg-transparent cursor-pointer disabled:cursor-not-allowed"
                        >
                          Berikutnya
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            );
          })()}

          {/* ================= TAB 2: BACKTEST STRATEGI ================= */}
          {activeTab === 'backtest' && (
            <div className="space-y-6">
              <div className="bg-card border border-border rounded-3xl p-6 flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
                <div>
                  <h3 className="text-lg font-bold text-text mb-1 flex items-center gap-2"><span>🧪</span> Backtest Strategi Kuantitatif IHSG</h3>
                  <p className="text-secondary text-sm">Pengujian rolling harian strategi klasifikasi arah binary & target ATR pada data historis IHSG.</p>
                </div>

                <div className="flex items-center gap-2 bg-background/60 p-1.5 rounded-2xl border border-border">
                  {[1, 3, 5].map((y) => (
                    <button
                      key={y}
                      onClick={() => handlePeriodChange(y)}
                      className={`px-4 py-1.5 rounded-xl font-bold text-xs transition cursor-pointer ${
                        backtestYears === y
                          ? 'bg-accent text-background shadow'
                          : 'text-secondary hover:text-text hover:bg-white/5'
                      }`}
                    >
                      {y} Tahun
                    </button>
                  ))}
                </div>
              </div>

              {backtestLoading && (
                <div className="flex flex-col items-center justify-center py-20 gap-4">
                  <span className="w-10 h-10 border-4 border-accent border-t-transparent rounded-full animate-spin"></span>
                  <span className="text-secondary font-medium">Menjalankan simulasi backtest {backtestYears} tahun...</span>
                </div>
              )}

              {backtestError && (
                <div className="p-4 bg-loss/10 border border-loss/20 text-red-300 rounded-2xl text-center">⚠️ {backtestError}</div>
              )}

              {!backtestLoading && !backtestError && backtestData && (() => {
                const b = backtestData;
                const logs = b.df || [];

                return (
                  <div className="space-y-6">
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                      <div className="bg-card border border-border rounded-3xl p-5">
                        <p className="text-xs text-secondary font-bold uppercase mb-1">Win Rate Prediksi (D+1)</p>
                        <p className="text-2xl font-black text-profit font-mono">{Number(b.win_rate || 0).toFixed(2)}%</p>
                        <p className="text-xs text-secondary mt-1">{b.win_count} dari {b.total_days} hari tepat</p>
                      </div>

                      <div className="bg-card border border-border rounded-3xl p-5">
                        <p className="text-xs text-secondary font-bold uppercase mb-1">Strategy Return (Long-Short)</p>
                        <p className={`text-2xl font-black font-mono ${Number(b.cum_strat_ls_pct || 0) >= 0 ? 'text-profit' : 'text-loss'}`}>
                          {Number(b.cum_strat_ls_pct || 0) >= 0 ? '+' : ''}{Number(b.cum_strat_ls_pct || 0).toFixed(2)}%
                        </p>
                        <p className="text-xs text-secondary mt-1">Sinyal Long & Short</p>
                      </div>

                      <div className="bg-card border border-border rounded-3xl p-5">
                        <p className="text-xs text-secondary font-bold uppercase mb-1">Strategy Return (Long Only)</p>
                        <p className={`text-2xl font-black font-mono ${Number(b.cum_strat_long_pct || 0) >= 0 ? 'text-profit' : 'text-loss'}`}>
                          {Number(b.cum_strat_long_pct || 0) >= 0 ? '+' : ''}{Number(b.cum_strat_long_pct || 0).toFixed(2)}%
                        </p>
                        <p className="text-xs text-secondary mt-1">Hanya posisi Long saat Bullish</p>
                      </div>

                      <div className="bg-card border border-border rounded-3xl p-5">
                        <p className="text-xs text-secondary font-bold uppercase mb-1">IHSG Benchmark (Buy & Hold)</p>
                        <p className={`text-2xl font-black font-mono ${Number(b.cum_bench_pct || 0) >= 0 ? 'text-profit' : 'text-loss'}`}>
                          {Number(b.cum_bench_pct || 0) >= 0 ? '+' : ''}{Number(b.cum_bench_pct || 0).toFixed(2)}%
                        </p>
                        <p className="text-xs text-secondary mt-1">Return IHSG pasif</p>
                      </div>
                    </div>

                    <div className="bg-card border border-border rounded-3xl p-6 space-y-3">
                      <h4 className="text-sm font-bold text-accent uppercase tracking-wider">💡 Cara Membaca Hasil Backtest:</h4>
                      <ul className="text-xs text-secondary space-y-2 leading-relaxed">
                        <li>• <strong className="text-text">Win Rate 51-55% di Pasar Keuangan</strong>: Di pasar finansial, win rate 54% dengan manajemen risiko positif ($1:1.5+$ R:R) sudah menghasilkan akumulasi profit yang sangat signifikan secara eksponensial.</li>
                        <li>• <strong className="text-text">Long-Short Strategy</strong>: Mengambil posisi Long saat algoritma memprediksi BULLISH, dan mengambil posisi Short (atau kas/hedging) saat algoritma memprediksi BEARISH.</li>
                        <li>• <strong className="text-text">Outperformance vs Benchmark</strong>: Mengukur sejauh mana strategi aktif ini mengungguli strategi pasif *Buy & Hold* IHSG.</li>
                      </ul>
                    </div>

                    {/* Detailed Logs */}
                    <div>
                      <h3 className="text-lg font-bold text-text mb-4 flex items-center gap-2"><span>🔍</span> Log Transaksi Backtest Harian</h3>
                      <div className="overflow-x-auto rounded-2xl border border-border bg-background/40">
                        <table className="w-full text-left border-collapse text-sm">
                          <thead>
                            <tr className="border-b border-border text-xs font-bold uppercase tracking-wider text-secondary bg-white/5">
                              <th className="py-3.5 px-6">Tanggal</th>
                              <th className="py-3.5 px-6 text-right">Close IHSG</th>
                              <th className="py-3.5 px-6 text-center">Score</th>
                              <th className="py-3.5 px-6 text-center">Prediksi Arah</th>
                              <th className="py-3.5 px-6 text-right">Actual Return %</th>
                              <th className="py-3.5 px-6 text-center">Tebakan Benar?</th>
                              <th className="py-3.5 px-6 text-right">Target Pred %</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-white/5 text-secondary font-mono text-xs">
                            {(() => {
                              const ITEMS_PER_PAGE = 10;
                              const totalPages = Math.ceil(logs.length / ITEMS_PER_PAGE);
                              const safePage = Math.max(1, Math.min(backtestPage, totalPages || 1));
                              const paginated = logs.slice((safePage - 1) * ITEMS_PER_PAGE, safePage * ITEMS_PER_PAGE);

                              return paginated.map((row: any, idx: number) => (
                                <tr key={idx} className="hover:bg-white/5 transition">
                                  <td className="py-3 px-6 font-sans text-text font-medium">{row.date}</td>
                                  <td className="py-3 px-6 text-right">{row.close?.toLocaleString('id-ID')}</td>
                                  <td className="py-3 px-6 text-center">{row.combined_score?.toFixed(2)}</td>
                                  <td className="py-3 px-6 text-center">
                                    <span className={`px-2 py-0.5 rounded font-sans font-bold uppercase tracking-wider ${row.predicted_dir === 'BULLISH' ? 'bg-profit/10 text-profit' : 'bg-loss/10 text-loss'}`}>
                                      {row.predicted_dir}
                                    </span>
                                  </td>
                                  <td className={`py-3 px-6 text-right font-bold ${row.actual_return_d1 >= 0 ? 'text-profit' : 'text-loss'}`}>
                                    {row.actual_return_d1 >= 0 ? '+' : ''}{row.actual_return_d1?.toFixed(2)}%
                                  </td>
                                  <td className="py-3 px-6 text-center font-sans">
                                    {row.is_correct_d1 ? <span className="text-profit font-bold">Ya ✅</span> : <span className="text-loss font-bold">Tidak ❌</span>}
                                  </td>
                                  <td className="py-3 px-6 text-right">{row.pred_d1_pct >= 0 ? '+' : ''}{row.pred_d1_pct?.toFixed(2)}%</td>
                                </tr>
                              ));
                            })()}
                          </tbody>
                        </table>
                      </div>

                      {logs.length > 10 && (
                        <div className="flex flex-col sm:flex-row items-center justify-between mt-4 px-2 gap-4">
                          <p className="text-xs text-secondary font-medium">
                            Menampilkan {Math.min(logs.length, (backtestPage - 1) * 10 + 1)} - {Math.min(logs.length, backtestPage * 10)} dari {logs.length} log
                          </p>
                          <div className="flex items-center gap-3">
                            <button
                              onClick={() => setBacktestPage(prev => Math.max(1, prev - 1))}
                              disabled={backtestPage === 1}
                              className="px-3 py-1.5 rounded-lg border border-border text-xs font-semibold text-text hover:bg-white/5 transition disabled:opacity-40 disabled:hover:bg-transparent cursor-pointer disabled:cursor-not-allowed"
                            >
                              Sebelumnya
                            </button>
                            <span className="text-xs text-text font-mono">
                              {backtestPage} / {Math.ceil(logs.length / 10)}
                            </span>
                            <button
                              onClick={() => setBacktestPage(prev => Math.min(Math.ceil(logs.length / 10), prev + 1))}
                              disabled={backtestPage === Math.ceil(logs.length / 10)}
                              className="px-3 py-1.5 rounded-lg border border-border text-xs font-semibold text-text hover:bg-white/5 transition disabled:opacity-40 disabled:hover:bg-transparent cursor-pointer disabled:cursor-not-allowed"
                            >
                              Berikutnya
                            </button>
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                );
              })()}
            </div>
          )}

          {/* ================= TAB 3: 1-YEAR OUTLOOK & REVERSAL DETECTOR ================= */}
          {activeTab === 'outlook' && (() => {
            const outlook = ihsgData.one_year_outlook || {};
            const fibs = outlook.fib_levels || {};
            const pivs = outlook.monthly_pivots || {};

            return (
              <div className="space-y-6">
                <div>
                  <h3 className="text-lg font-bold text-text mb-1 flex items-center gap-2"><span>🌐</span> 1-Year Technical Outlook & Reversal Pivot Detector</h3>
                  <p className="text-secondary text-sm">Proyeksi tren 1-tahun, deteksi titik Reversal Bottom/Top (Fibonacci 5-Tahun & Monthly Pivots), serta estimasi jendela waktu (Bulan & Minggu).</p>
                </div>

                {/* TIMEFRAME DIRECTION CARDS (WEEKLY & MONTHLY) */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="bg-card border border-border rounded-3xl p-5 flex items-center justify-between">
                    <div>
                      <p className="text-xs text-secondary font-bold uppercase tracking-wider mb-1">📅 Prediksi Minggu Ini (Weekly)</p>
                      <div className="flex items-center gap-2">
                        <span className={`w-3 h-3 rounded-full ${outlook.weekly_direction === 'BULLISH' ? 'bg-profit shadow-[0_0_10px_rgba(52,211,153,0.5)]' : 'bg-loss shadow-[0_0_10px_rgba(248,113,113,0.5)]'}`}></span>
                        <span className={`text-2xl font-black font-mono uppercase ${outlook.weekly_direction === 'BULLISH' ? 'text-profit' : 'text-loss'}`}>
                          {outlook.weekly_direction || 'BEARISH'}
                        </span>
                      </div>
                      <p className="text-xs text-secondary mt-1 font-mono">Score: {outlook.weekly_score ?? '-'}</p>
                    </div>
                    <div>
                      <span className={`px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider ${
                        outlook.weekly_confidence === 'HIGH' ? 'bg-profit/10 text-profit border border-profit/20' :
                        outlook.weekly_confidence === 'MEDIUM' ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20' :
                        'bg-loss/10 text-loss border border-loss/20'
                      }`}>
                        {outlook.weekly_confidence || 'LOW'} CONFIDENCE
                      </span>
                    </div>
                  </div>

                  <div className="bg-card border border-border rounded-3xl p-5 flex items-center justify-between">
                    <div>
                      <p className="text-xs text-secondary font-bold uppercase tracking-wider mb-1">📆 Prediksi Bulan Ini (Monthly)</p>
                      <div className="flex items-center gap-2">
                        <span className={`w-3 h-3 rounded-full ${outlook.monthly_direction === 'BULLISH' ? 'bg-profit shadow-[0_0_10px_rgba(52,211,153,0.5)]' : 'bg-loss shadow-[0_0_10px_rgba(248,113,113,0.5)]'}`}></span>
                        <span className={`text-2xl font-black font-mono uppercase ${outlook.monthly_direction === 'BULLISH' ? 'text-profit' : 'text-loss'}`}>
                          {outlook.monthly_direction || 'BEARISH'}
                        </span>
                      </div>
                      <p className="text-xs text-secondary mt-1 font-mono">Score: {outlook.monthly_score ?? '-'}</p>
                    </div>
                    <div>
                      <span className={`px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider ${
                        outlook.monthly_confidence === 'HIGH' ? 'bg-profit/10 text-profit border border-profit/20' :
                        outlook.monthly_confidence === 'MEDIUM' ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20' :
                        'bg-loss/10 text-loss border border-loss/20'
                      }`}>
                        {outlook.monthly_confidence || 'LOW'} CONFIDENCE
                      </span>
                    </div>
                  </div>
                </div>

                {/* 4 HEADER METRICS */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div className="bg-card border border-border rounded-3xl p-5">
                    <p className="text-xs text-secondary font-bold uppercase mb-1">Arah Tren 1-Tahun</p>
                    <div className="flex items-center gap-2">
                      <span className={`w-3 h-3 rounded-full ${outlook.direction_1year === 'BULLISH' ? 'bg-profit shadow-[0_0_10px_rgba(52,211,153,0.5)]' : 'bg-loss shadow-[0_0_10px_rgba(248,113,113,0.5)]'}`}></span>
                      <p className={`text-2xl font-black font-mono ${outlook.direction_1year === 'BULLISH' ? 'text-profit' : 'text-loss'}`}>
                        {outlook.direction_1year || 'BEARISH'}
                      </p>
                    </div>
                  </div>

                  <div className="bg-card border border-border rounded-3xl p-5">
                    <p className="text-xs text-secondary font-bold uppercase mb-1">Zona Bottom Confluence</p>
                    <p className="text-2xl font-black text-text font-mono">{outlook.bottom_confluence_level?.toLocaleString('id-ID') || '5.980'}</p>
                    <p className="text-xs text-loss font-bold mt-1">{outlook.downside_risk_pct}% Risk</p>
                  </div>

                  <div className="bg-card border border-border rounded-3xl p-5">
                    <p className="text-xs text-secondary font-bold uppercase mb-1">Zona Top Resistance</p>
                    <p className="text-2xl font-black text-text font-mono">{outlook.top_confluence_level?.toLocaleString('id-ID') || '7.078'}</p>
                    <p className="text-xs text-profit font-bold mt-1">+{outlook.upside_potential_pct}% Upside</p>
                  </div>

                  <div className="bg-card border border-border rounded-3xl p-5">
                    <p className="text-xs text-secondary font-bold uppercase mb-1">Estimasi Waktu Reversal</p>
                    <p className="text-xl font-black text-accent font-mono">{outlook.estimated_reversal_window || 'Oktober 2026 (±6 Minggu)'}</p>
                    <p className="text-xs text-secondary mt-1">Siklus Volatilitas ATR Mingguan</p>
                  </div>
                </div>

                {/* 2-WAY REVERSAL PIVOT TRIGGER CARDS */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div className="bg-card border border-profit/30 rounded-3xl p-6 space-y-3 relative overflow-hidden">
                    <div className="absolute top-0 right-0 w-32 h-32 bg-profit/5 rounded-full blur-2xl pointer-events-none"></div>
                    <div className="flex items-center gap-2">
                      <span className="text-xl">🟢</span>
                      <h4 className="text-base font-bold text-profit">SAAT BEARISH: Kapan Berbalik NAIK?</h4>
                    </div>
                    <div className="p-3 bg-profit/10 border border-profit/20 rounded-2xl">
                      <p className="text-xs font-bold text-profit uppercase mb-1">Status Reversal</p>
                      <p className="text-sm font-semibold text-text">
                        {outlook.bullish_reversal_confirmed ? '✅ SELESAI BOTTOMLAND (BULLISH)' : '⏳ DALAM PROSES BOTTOMLAND'}
                      </p>
                    </div>
                    <ul className="text-xs text-secondary space-y-2 leading-relaxed">
                      <li>• <strong className="text-text">Zona Bottom Target</strong>: <span className="text-profit font-bold font-mono">{outlook.bottom_confluence_level?.toLocaleString('id-ID')}</span></li>
                      <li>• <strong className="text-text">Syarat Utama</strong>: Breakout & Close di atas <strong className="text-text font-mono">MA50 Weekly ({outlook.ma50_weekly?.toLocaleString('id-ID')})</strong></li>
                      <li>• <strong className="text-text">Konfirmasi Sekunder</strong>: Rebound Weekly RSI & Weekly MACD Golden Cross</li>
                    </ul>
                  </div>

                  <div className="bg-card border border-loss/30 rounded-3xl p-6 space-y-3 relative overflow-hidden">
                    <div className="absolute top-0 right-0 w-32 h-32 bg-loss/5 rounded-full blur-2xl pointer-events-none"></div>
                    <div className="flex items-center gap-2">
                      <span className="text-xl">🔴</span>
                      <h4 className="text-base font-bold text-loss">SAAT BULLISH: Kapan Berbalik TURUN?</h4>
                    </div>
                    <div className="p-3 bg-loss/10 border border-loss/20 rounded-2xl">
                      <p className="text-xs font-bold text-loss uppercase mb-1">Status Reversal</p>
                      <p className="text-sm font-semibold text-text">
                        {outlook.bearish_reversal_confirmed ? '⚠️ BERPOTENSI REVERSAL TURUN' : '🟢 TREN NAIK MASIH SOLID'}
                      </p>
                    </div>
                    <ul className="text-xs text-secondary space-y-2 leading-relaxed">
                      <li>• <strong className="text-text">Zona Top Resistance Target</strong>: <span className="text-loss font-bold font-mono">{outlook.top_confluence_level?.toLocaleString('id-ID')}</span></li>
                      <li>• <strong className="text-text">Syarat Utama</strong>: Breakdown & Close di bawah <strong className="text-text font-mono">MA50 Weekly ({outlook.ma50_weekly?.toLocaleString('id-ID')})</strong></li>
                      <li>• <strong className="text-text">Konfirmasi Sekunder</strong>: Weekly RSI Overbought (&gt;70) & Weekly MACD Death Cross</li>
                    </ul>
                  </div>
                </div>

                {/* SEASONALITY REVERSAL CARDS */}
                <div>
                  <h3 className="text-lg font-bold text-text mb-4 flex items-center gap-2"><span>📅</span> Musim Reversal Historis IHSG (Seasonality Window)</h3>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div className="bg-card border border-border rounded-3xl p-5 flex items-center justify-between">
                      <div>
                        <p className="text-xs text-secondary font-bold uppercase mb-1">Bulan Reversal Naik Terkuat</p>
                        <p className="text-xl font-bold text-profit font-mono">🗓️ {outlook.best_seasonal_month || 'Juli'}</p>
                      </div>
                      <div className="text-right">
                        <p className="text-2xl font-black text-profit font-mono">{outlook.best_seasonal_win_rate}%</p>
                        <p className="text-[11px] text-secondary font-medium">Win Rate Historis</p>
                      </div>
                    </div>

                    <div className="bg-card border border-border rounded-3xl p-5 flex items-center justify-between">
                      <div>
                        <p className="text-xs text-secondary font-bold uppercase mb-1">Bulan Konsolidasi / Terlemah</p>
                        <p className="text-xl font-bold text-loss font-mono">⚠️ {outlook.worst_seasonal_month || 'Maret'}</p>
                      </div>
                      <div className="text-right">
                        <p className="text-2xl font-black text-loss font-mono">{outlook.worst_seasonal_win_rate}%</p>
                        <p className="text-[11px] text-secondary font-medium">Win Rate Historis</p>
                      </div>
                    </div>
                  </div>
                </div>

                {/* TECHNICAL CONFLUENCE LEVEL TABLE */}
                <div>
                  <h3 className="text-lg font-bold text-text mb-4 flex items-center gap-2"><span>📐</span> Level Confluence Support & Resistance (Fibonacci 5-Tahun)</h3>
                  <div className="overflow-x-auto rounded-2xl border border-border bg-background/40">
                    <table className="w-full text-left border-collapse text-sm">
                      <thead>
                        <tr className="border-b border-border text-xs font-bold uppercase tracking-wider text-secondary bg-white/5">
                          <th className="py-3.5 px-6">Kategori Level</th>
                          <th className="py-3.5 px-6">Tipe Indicator / Formula</th>
                          <th className="py-3.5 px-6 text-right">Nilai Level IHSG</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-white/5 text-secondary font-mono text-xs">
                        {[
                          { kat: 'Top Resistance 2', type: 'Fibonacci Extension 161.8%', val: fibs.fib_exp_1618 },
                          { kat: 'Top Resistance 1', type: 'Fibonacci Extension 127.2%', val: fibs.fib_exp_1272 },
                          { kat: 'Monthly Pivot R1', type: 'TradingView Monthly Pivot R1', val: pivs.R1 },
                          { kat: 'MA50 Weekly (Reversal Line)', type: 'Weekly 50 Moving Average', val: outlook.ma50_weekly },
                          { kat: 'Monthly Pivot S1', type: 'TradingView Monthly Pivot S1', val: pivs.S1 },
                          { kat: 'Fibonacci 50.0%', type: '5-Year Retracement 50.0%', val: fibs.fib_500 },
                          { kat: 'Fibonacci 61.8% (Golden Pocket)', type: '5-Year Retracement 61.8%', val: fibs.fib_618 },
                          { kat: 'Bottom Support Confluence', type: 'Zona Support Terkuat', val: outlook.bottom_confluence_level },
                          { kat: 'MA200 Weekly (Major Base)', type: 'Weekly 200 Moving Average', val: outlook.ma200_weekly },
                        ].map((row, i) => (
                          <tr key={i} className="hover:bg-white/5 transition">
                            <td className="py-3 px-6 font-sans text-text font-bold">{row.kat}</td>
                            <td className="py-3 px-6 font-sans text-secondary">{row.type}</td>
                            <td className="py-3 px-6 text-right text-text font-bold">{row.val ? row.val.toLocaleString('id-ID') : '-'}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>
            );
          })()}
        </>
      )}
    </div>
  );
}
