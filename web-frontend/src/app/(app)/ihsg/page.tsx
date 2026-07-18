"use client";
import React, { useState, useEffect } from 'react';
import { useApp } from '../../context/AppContext';

export default function IhsgPage() {
  const { showToast } = useApp();
  const [ihsgData, setIhsgData] = useState<any>(null);
  const [ihsgLoading, setIhsgLoading] = useState(false);
  const [ihsgError, setIhsgError] = useState("");
  const [currentPage, setCurrentPage] = useState(1);

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

  useEffect(() => { fetchIhsgData(); }, []);

  return (
    <div className="space-y-6 animate-fade-in">
      <div>
        <h2 className="text-3xl font-bold text-text mb-2">IHSG <span className="text-accent">Predictor</span></h2>
        <p className="text-secondary">Analisis komparatif arah indeks pasar, skor komponen makro & sektoral, dan prediksi tingkat volatilitas.</p>
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

      {!ihsgLoading && !ihsgError && ihsgData && ihsgData.latest && (() => {
        const latest = ihsgData.latest;
        const realtime = ihsgData.realtime || {};
        const history = ihsgData.history || [];
        const scores = latest.component_scores || {};
        const drivers = latest.key_drivers || [];
        const risks = latest.risks || [];
        const isRealtime = realtime.source === 'stockbit';

        return (
          <>
            {isRealtime && (
              <div className="bg-gradient-to-r from-accent/20 via-accent/10 to-transparent border border-accent/30 rounded-3xl p-6 mt-6 flex items-start gap-4 animate-pulse">
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
                  <p className="text-xs text-secondary/60 mt-3">Updated: {new Date(realtime.timestamp).toLocaleString('id-ID')}</p>
                </div>
              </div>
            )}

            {ihsgData.accuracy && ihsgData.accuracy.total > 0 && (
              <div className="bg-accent/10 border border-accent/20 rounded-2xl p-4 mt-6 flex items-center gap-4">
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
              <div className="grid grid-cols-2 md:grid-cols-4 gap-6 bg-card border border-border rounded-3xl p-6">
                {['momentum', 'breadth', 'macro', 'sectors'].map((key) => (
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
          </>
        );
      })()}
    </div>
  );
}
