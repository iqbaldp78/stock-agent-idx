"use client";
import React, { useState, useEffect } from 'react';
import { useApp } from '../../context/AppContext';

export default function IhsgPage() {
  const { showToast } = useApp();
  const [ihsgData, setIhsgData] = useState<any>(null);
  const [ihsgLoading, setIhsgLoading] = useState(false);
  const [ihsgError, setIhsgError] = useState("");

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
        <div className="p-4 bg-red-500/10 border border-red-500/20 text-red-300 rounded-2xl text-center">⚠️ {ihsgError}</div>
      )}

      {!ihsgLoading && !ihsgError && ihsgData && ihsgData.latest && (() => {
        const latest = ihsgData.latest;
        const history = ihsgData.history || [];
        const scores = latest.component_scores || {};
        const drivers = latest.key_drivers || [];
        const risks = latest.risks || [];

        return (
          <>
            {ihsgData.accuracy && ihsgData.accuracy.total > 0 && (
              <div className="bg-indigo-500/10 border border-indigo-500/20 rounded-2xl p-4 mt-6 flex items-center gap-4">
                <div className="w-12 h-12 bg-indigo-500/20 rounded-full flex items-center justify-center text-xl">🎯</div>
                <div>
                  <h4 className="text-sm font-bold text-indigo-300 tracking-wider uppercase mb-1">Track Record Akurasi</h4>
                  <p className="text-white font-medium">Akurasi Arah (Historical): <span className="text-emerald-400 font-bold">{ihsgData.accuracy.percentage}%</span> ({ihsgData.accuracy.correct}/{ihsgData.accuracy.total} hari prediksi tepat)</p>
                </div>
              </div>
            )}

            <div className="grid grid-cols-2 md:grid-cols-4 gap-6 bg-white/[0.03] backdrop-blur-md border border-white/5 rounded-3xl p-6">
              <div>
                <p className="text-xs text-slate-400 font-bold uppercase tracking-wider mb-2">Current Level</p>
                <p className="text-2xl md:text-3xl font-black text-white font-mono">{latest.current_price?.toLocaleString('id-ID')}</p>
              </div>
              <div>
                <p className="text-xs text-slate-400 font-bold uppercase tracking-wider mb-2">Confidence</p>
                <div className="flex items-center gap-2">
                  <span className={`inline-block w-4 h-4 rounded-full ${latest.confidence === 'HIGH' ? 'bg-emerald-400 shadow-[0_0_10px_rgba(52,211,153,0.5)]' : latest.confidence === 'MEDIUM' ? 'bg-amber-400 shadow-[0_0_10px_rgba(251,191,36,0.5)]' : 'bg-red-400 shadow-[0_0_10px_rgba(248,113,113,0.5)]'}`}></span>
                  <span className="text-lg md:text-xl font-extrabold text-white uppercase tracking-wide">{latest.confidence}</span>
                </div>
              </div>
              <div>
                <p className="text-xs text-slate-400 font-bold uppercase tracking-wider mb-2">Direction</p>
                <p className={`text-xl md:text-2xl font-black uppercase tracking-wide ${latest.direction === 'BULLISH' ? 'text-emerald-400' : latest.direction === 'BEARISH' ? 'text-red-400' : 'text-slate-300'}`}>{latest.direction}</p>
              </div>
              <div>
                <p className="text-xs text-slate-400 font-bold uppercase tracking-wider mb-2">Volatility</p>
                <p className="text-xl md:text-2xl font-black text-white uppercase tracking-wide">{latest.volatility_level}</p>
              </div>
            </div>

            <div>
              <h3 className="text-lg font-bold text-white mb-4 flex items-center gap-2"><span>📊</span> Price Predictions</h3>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                {[
                  { label: 'D+1', price: latest.day_1_price, pct: latest.day_1_pct },
                  { label: 'D+3', price: latest.day_3_price, pct: latest.day_3_pct },
                  { label: 'D+5', price: latest.day_5_price, pct: latest.day_5_pct },
                  { label: 'D+7', price: latest.day_7_price, pct: latest.day_7_pct },
                ].map((item, idx) => (
                  <div key={idx} className="bg-white/[0.03] border border-white/5 rounded-2xl p-5 font-mono">
                    <p className="text-xs text-slate-400 font-bold font-sans uppercase mb-2">{item.label} Prediction</p>
                    <p className="text-xl font-bold text-white">{item.price?.toLocaleString('id-ID')}</p>
                    <p className={`text-xs mt-1 font-bold ${item.pct >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                      {item.pct >= 0 ? '+' : ''}{item.pct?.toFixed(2)}%
                    </p>
                  </div>
                ))}
              </div>
            </div>

            <div>
              <h3 className="text-lg font-bold text-white mb-4 flex items-center gap-2"><span>⚙️</span> Component Scores</h3>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-6 bg-white/[0.03] border border-white/5 rounded-3xl p-6">
                {['momentum', 'breadth', 'macro', 'sectors'].map((key) => (
                  <div key={key}>
                    <p className="text-xs text-slate-400 font-bold uppercase tracking-wider mb-2">{key.charAt(0).toUpperCase() + key.slice(1)}</p>
                    <p className="text-2xl font-black text-white font-mono">{scores[key] !== undefined ? scores[key].toFixed(2) : '-'}</p>
                  </div>
                ))}
              </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
              <div className="space-y-6">
                <div className="bg-white/[0.03] border border-white/5 rounded-3xl p-6">
                  <h3 className="text-lg font-bold text-white mb-4 flex items-center gap-2"><span>📝</span> Reasoning & Analysis</h3>
                  <div className="text-slate-300 text-sm leading-relaxed whitespace-pre-wrap font-sans">{latest.reasoning || 'No analysis reasoning details available.'}</div>
                </div>
              </div>
              <div className="space-y-6">
                <div className="bg-white/[0.03] border border-white/5 rounded-3xl p-6">
                  <h3 className="text-lg font-bold text-white mb-4 flex items-center gap-2"><span className="text-emerald-400">✓</span> Key Drivers</h3>
                  {drivers.length > 0 ? (
                    <ul className="space-y-2.5">{drivers.map((driver: string, i: number) => (<li key={i} className="flex items-start gap-3 text-slate-300 text-sm"><span className="text-emerald-400 mt-0.5">•</span><span>{driver}</span></li>))}</ul>
                  ) : <p className="text-slate-500 text-sm">No drivers identified.</p>}
                </div>
                <div className="bg-white/[0.03] border border-white/5 rounded-3xl p-6">
                  <h3 className="text-lg font-bold text-white mb-4 flex items-center gap-2"><span className="text-red-400">⚠️</span> Risk Factors</h3>
                  {risks.length > 0 ? (
                    <ul className="space-y-2.5">{risks.map((risk: string, i: number) => (<li key={i} className="flex items-start gap-3 text-slate-300 text-sm"><span className="text-red-400 mt-0.5">•</span><span>{risk}</span></li>))}</ul>
                  ) : <p className="text-slate-500 text-sm">No major risks identified.</p>}
                </div>
              </div>
            </div>

            <div>
              <h3 className="text-lg font-bold text-white mb-4 flex items-center gap-2"><span>📈</span> Historical Predictions</h3>
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
                      <th className="py-3.5 px-6 text-center">Status Validasi</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-white/5 text-slate-300 font-mono">
                    {history.map((row: any, idx: number) => (
                      <tr key={idx} className="hover:bg-white/5 transition">
                        <td className="py-3.5 px-6 font-sans text-white font-medium">{row.run_date}</td>
                        <td className="py-3.5 px-6 text-right">{row.current_price?.toLocaleString('id-ID')}</td>
                        <td className="py-3.5 px-6 text-right">{row.day_1_price?.toLocaleString('id-ID')}</td>
                        <td className={`py-3.5 px-6 text-right font-bold ${row.day_1_pct >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>{row.day_1_pct >= 0 ? '+' : ''}{row.day_1_pct?.toFixed(2)}%</td>
                        <td className="py-3.5 px-6 text-center">
                          <span className={`px-2.5 py-0.5 rounded text-[11px] font-sans font-bold uppercase tracking-wider ${row.direction === 'BULLISH' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' : row.direction === 'BEARISH' ? 'bg-red-500/10 text-red-400 border border-red-500/20' : 'bg-slate-500/10 text-slate-400 border border-slate-500/20'}`}>{row.direction}</span>
                        </td>
                        <td className="py-3.5 px-6 text-center">
                          <span className={`px-2.5 py-0.5 rounded text-[11px] font-sans font-bold uppercase tracking-wider ${row.confidence === 'HIGH' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' : row.confidence === 'MEDIUM' ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20' : 'bg-red-500/10 text-red-400 border border-red-500/20'}`}>{row.confidence}</span>
                        </td>
                        <td className="py-3.5 px-6 text-center font-sans">
                          {row.is_correct === true && <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-bold bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">Benar ✅</span>}
                          {row.is_correct === false && <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-bold bg-red-500/20 text-red-400 border border-red-500/30">Salah ❌</span>}
                          {row.is_correct === null && <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-bold bg-gray-500/20 text-gray-400 border border-gray-500/30">Pending ⏳</span>}
                        </td>
                      </tr>
                    ))}
                    {history.length === 0 && <tr><td colSpan={7} className="py-10 text-center text-slate-500 font-sans">Belum ada riwayat prediksi.</td></tr>}
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
