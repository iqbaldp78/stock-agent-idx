"use client";
import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useApp } from '../../context/AppContext';

const formatEntry = (stock: any) => {
  if (!stock) return "-";
  if (stock.entry_low && stock.entry_high) return `${stock.entry_low.toLocaleString('id-ID')} - ${stock.entry_high.toLocaleString('id-ID')}`;
  if (stock.entry_low) return `${stock.entry_low.toLocaleString('id-ID')}`;
  if (stock.entry_high) return `${stock.entry_high.toLocaleString('id-ID')}`;
  return "-";
};
const formatTP = (stock: any) => {
  if (!stock) return "-";
  const tps = [stock.target_1, stock.target_2, stock.target_3].filter(tp => tp !== null && tp !== undefined);
  return tps.length > 0 ? tps.map(tp => `${tp.toLocaleString('id-ID')}`).join(" / ") : "-";
};
const formatSL = (stock: any) => (!stock || !stock.stop_loss) ? "-" : `${stock.stop_loss.toLocaleString('id-ID')}`;
const formatLot = (lots: number) => { if (!lots) return "0"; if (lots >= 1000) return `${(lots / 1000).toFixed(1)}K`; return lots.toLocaleString('id-ID'); };
const formatValue = (val: number) => { if (!val) return "0"; if (val >= 1e9) return `${(val / 1e9).toFixed(2)}B`; if (val >= 1e6) return `${(val / 1e6).toFixed(2)}M`; return val.toLocaleString('id-ID'); };
const formatPercentage = (pct: number) => { if (pct === undefined || pct === null) return "0.00%"; return `${pct >= 0 ? '+' : ''}${pct.toFixed(2)}%`; };

export default function TopPicksPage() {
  const { picks, runDate, isPro, setIsPro, showToast } = useApp();
  const router = useRouter();
  const [selectedStock, setSelectedStock] = useState<any | null>(null);
  const [showFairValueDetails, setShowFairValueDetails] = useState(false);
  const [showTrueCostDetails, setShowTrueCostDetails] = useState(true);
  const [showDistDetails, setShowDistDetails] = useState(true);

  if (selectedStock) {
    return (
      <div className="space-y-6 animate-fade-in">
        <button
          onClick={() => setSelectedStock(null)}
          className="flex items-center gap-2 text-slate-400 hover:text-white transition group mb-4"
        >
          <span className="w-8 h-8 rounded-full bg-white/5 group-hover:bg-white/10 flex items-center justify-center transition">←</span>
          <span className="text-sm font-semibold">Kembali ke Daftar</span>
        </button>

        <div className="bg-[#030712] border border-white/5 rounded-3xl p-8 relative overflow-hidden">
          <div className="absolute top-0 right-0 w-96 h-96 bg-indigo-500/10 rounded-full blur-3xl -translate-y-1/2 translate-x-1/2 pointer-events-none"></div>
          <div className="relative z-10">
            <div className="flex justify-between items-start mb-8">
              <div>
                <h2 className="text-4xl font-black text-white mb-1">{selectedStock.ticker}</h2>
                <p className="text-slate-500 font-medium text-sm mb-3">Saham Tbk.</p>
                <span className={`px-4 py-1.5 rounded-full text-xs font-bold uppercase tracking-wider border inline-block ${selectedStock.action === 'BUY' ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' : selectedStock.action === 'SELL' ? 'bg-red-500/10 text-red-400 border-red-500/20' : 'bg-slate-500/10 text-slate-400 border-slate-500/20'}`}>
                  {selectedStock.action}
                </span>
              </div>
              <div className="text-right">
                <div className="text-4xl font-bold text-white font-mono">{selectedStock.current_price || selectedStock.entry_price}</div>
                <p className="text-[10px] text-slate-500 font-bold mt-1 uppercase tracking-wider">Entry Price</p>
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
                    sessionStorage.setItem('tradingPrefill', JSON.stringify({
                      ticker: selectedStock.ticker,
                      price: selectedStock.current_price || selectedStock.entry_price || 1000,
                      tp: selectedStock.target_1 || 0,
                      sl: selectedStock.stop_loss || 0,
                      signalId: selectedStock.id || null,
                    }));
                    showToast(`Form order untuk ${selectedStock.ticker} telah diisi. Silakan periksa di Trading Engine!`, 'info');
                    router.push('/trading');
                  }}
                  className="w-full py-3 rounded-lg font-bold text-white bg-indigo-500 hover:bg-indigo-600 transition text-sm shadow-lg shadow-indigo-500/20"
                >
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

            {/* Fair Value Details */}
            {selectedStock.fair_value_details && (
              <div className="bg-white/[0.03] backdrop-blur-md border border-white/5 rounded-3xl p-6 mb-8 hover:bg-white/5 transition duration-300">
                <div className="flex flex-wrap items-center justify-between gap-4 mb-4 pb-4 border-b border-white/5">
                  <div className="flex items-center gap-2 text-base font-semibold text-white">
                    <span>💰 Fair Value:</span>
                    <span className={`inline-block w-2.5 h-2.5 rounded-full ${selectedStock.fair_value_details.valuation_label?.includes('UNDERVALUED') ? 'bg-emerald-500 shadow-[0_0_10px_rgba(16,185,129,0.5)]' : selectedStock.fair_value_details.valuation_label?.includes('OVERVALUED') ? 'bg-red-500 shadow-[0_0_10px_rgba(239,68,68,0.5)]' : 'bg-yellow-500 shadow-[0_0_10px_rgba(245,158,11,0.5)]'}`}></span>
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
                <button
                  onClick={() => setShowFairValueDetails(!showFairValueDetails)}
                  className="w-full flex items-center justify-between py-2 text-slate-300 hover:text-white transition font-medium text-sm border border-white/5 bg-white/5 px-4 rounded-xl"
                >
                  <span className="flex items-center gap-2"><span className="text-indigo-400">📐</span> Detail Fair Value {selectedStock.ticker}</span>
                  <span>{showFairValueDetails ? '▲' : '▼'}</span>
                </button>
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
                  </div>
                )}
              </div>
            )}

            {/* Price Projections */}
            {selectedStock.predictions && Object.keys(selectedStock.predictions).length > 0 && (
              <div className="bg-white/[0.03] border border-white/5 rounded-2xl p-6 mb-8">
                <h4 className="text-sm font-bold text-slate-400 uppercase tracking-widest mb-4 border-b border-white/5 pb-2 flex items-center gap-2">
                  <span>🎯</span> Price Projections
                </h4>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  {['day_1', 'day_3', 'day_5', 'day_7'].map((day, idx) => (
                    selectedStock.predictions[day] && (
                      <div key={idx} className="bg-white/5 rounded-xl p-4 text-center border border-white/5">
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
              <div className="space-y-8">
                <div className="bg-white/[0.03] border border-white/5 rounded-2xl p-6">
                  <h4 className="text-sm font-bold text-slate-400 uppercase tracking-widest mb-4 border-b border-white/5 pb-2 flex items-center gap-2"><span>🧠</span> AI Deep Reasoning</h4>
                  <p className="text-sm text-slate-300 leading-relaxed">{selectedStock.reasoning}</p>
                </div>
                {selectedStock.thesis && (
                  <div className="bg-indigo-500/5 border border-indigo-500/10 rounded-2xl p-6">
                    <h4 className="text-sm font-bold text-indigo-300 uppercase tracking-widest mb-4 border-b border-indigo-500/10 pb-2 flex items-center gap-2"><span>📜</span> Investment Thesis</h4>
                    <p className="text-sm text-slate-300 leading-relaxed">{selectedStock.thesis}</p>
                  </div>
                )}
              </div>
              <div className="space-y-8">
                {selectedStock.key_drivers && selectedStock.key_drivers.length > 0 && (
                  <div className="bg-white/[0.03] border border-white/5 rounded-2xl p-6">
                    <h4 className="text-sm font-bold text-slate-400 uppercase tracking-widest mb-4 border-b border-white/5 pb-2 flex items-center gap-2"><span>⚡</span> Key Drivers</h4>
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
                {selectedStock.risks && selectedStock.risks.length > 0 && (
                  <div className="bg-red-500/5 border border-red-500/10 rounded-2xl p-6">
                    <h4 className="text-sm font-bold text-red-300 uppercase tracking-widest mb-4 border-b border-red-500/10 pb-2 flex items-center gap-2"><span>⚠️</span> Risk Factors</h4>
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

            {/* Broker True Cost */}
            {selectedStock.broker_true_cost?.w1m && (
              <div className="bg-white/[0.03] backdrop-blur-md border border-white/5 rounded-3xl p-6 mb-8 mt-8">
                <button
                  onClick={() => setShowTrueCostDetails(!showTrueCostDetails)}
                  className="w-full flex items-center justify-between py-2 text-slate-200 hover:text-white transition font-bold text-base"
                >
                  <span className="flex items-center gap-2"><span className="text-indigo-400">🏛️</span> True Cost Broker Akumulasi</span>
                  <span>{showTrueCostDetails ? '▲' : '▼'}</span>
                </button>
                {showTrueCostDetails && (
                  <div className="mt-4 animate-fade-in overflow-x-auto rounded-xl border border-white/5 bg-[#030712]/40">
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
                            <td className="py-3 px-4 font-bold text-white">{row.broker}</td>
                            <td className="py-3 px-4 text-white">Rp {(row.true_cost || 0).toLocaleString('id-ID')}</td>
                            <td className="py-3 px-4">{formatLot(row.total_buy_lot)}</td>
                            <td className="py-3 px-4">{formatValue(row.total_buy_value)}</td>
                            <td className={`py-3 px-4 font-bold ${row.distance_pct >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>{formatPercentage(row.distance_pct)}</td>
                            <td className="py-3 px-4 text-right">{row.active_days || '-'}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    );
  }

  return (
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

      {picks.length === 0 ? (
        <div className="text-center py-20 text-slate-400">
          <div className="w-16 h-16 rounded-full bg-slate-800 flex items-center justify-center mx-auto mb-4 text-2xl">🔍</div>
          <h4 className="text-lg font-bold text-white mb-2">No Data Found</h4>
          <p>Tidak ada sinyal rekomendasi saham yang aktif saat ini dari AI.</p>
        </div>
      ) : (
        <div className="space-y-8">
          <div className="flex justify-between items-end mb-2">
            <h3 className="text-2xl font-bold text-white">Today&apos;s AI Picks</h3>
            <p className="text-sm text-slate-500">Running Date: <span className="font-mono text-indigo-300">{runDate}</span></p>
          </div>

          {/* 1st Top Pick (Featured) */}
          <div className="bg-gradient-to-b from-indigo-500/10 to-transparent border border-indigo-500/20 rounded-3xl p-1 shadow-[0_0_50px_rgba(99,102,241,0.05)] relative overflow-hidden">
            <div className="absolute top-0 right-0 w-64 h-64 bg-indigo-500/10 rounded-full blur-3xl -translate-y-1/2 translate-x-1/2"></div>
            <div className="bg-[#030712]/80 backdrop-blur-xl rounded-[23px] p-8 h-full flex flex-col relative z-10">
              <div className="flex justify-between items-start mb-6">
                <div>
                  <h4 className="text-3xl font-black text-white hover:text-indigo-400 cursor-pointer transition-colors mb-1" onClick={() => setSelectedStock(picks[0])}>
                    {picks[0].ticker}
                  </h4>
                  <p className="text-slate-500 font-medium text-sm mb-3">Saham Tbk.</p>
                  <span className={`px-4 py-1.5 rounded-full text-xs font-bold uppercase tracking-wider border inline-block ${picks[0].action === 'BUY' ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' : picks[0].action === 'SELL' ? 'bg-red-500/10 text-red-400 border-red-500/20' : 'bg-slate-500/10 text-slate-400 border-slate-500/20'}`}>
                    {picks[0].action}
                  </span>
                </div>
                <div className="text-right">
                  <div className="text-3xl font-bold text-white font-mono">{picks[0].current_price || picks[0].entry_price}</div>
                  <p className="text-slate-500 text-xs mt-1 uppercase font-bold tracking-widest">Entry Price</p>
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
                <div className="bg-white/5 rounded-xl p-4 border border-white/5"><p className="text-[10px] text-slate-400 font-bold uppercase tracking-wider mb-1">Entry Range</p><p className="text-sm font-bold text-white font-mono">{formatEntry(picks[0])}</p></div>
                <div className="bg-white/5 rounded-xl p-4 border border-white/5"><p className="text-[10px] text-slate-400 font-bold uppercase tracking-wider mb-1">Take Profit</p><p className="text-sm font-bold text-emerald-400 font-mono">{formatTP(picks[0])}</p></div>
                <div className="bg-white/5 rounded-xl p-4 border border-white/5"><p className="text-[10px] text-slate-400 font-bold uppercase tracking-wider mb-1">Stop Loss</p><p className="text-sm font-bold text-red-400 font-mono">{formatSL(picks[0])}</p></div>
              </div>
              <div className="mt-auto">
                <p className="text-sm text-slate-400 mb-6 line-clamp-2">{picks[0].reasoning}</p>
                <button onClick={() => setSelectedStock(picks[0])} className="w-full py-4 rounded-xl font-bold text-white bg-indigo-500 hover:bg-indigo-600 transition shadow-lg shadow-indigo-500/20 text-lg">
                  Lihat Detail & Analisis
                </button>
              </div>
            </div>
          </div>

          {/* Grid remaining picks */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 relative">
            {picks.slice(1).map((pick, i) => (
              <div key={i} className={`bg-white/[0.03] backdrop-blur-md border border-white/5 rounded-3xl p-6 flex flex-col hover:bg-white/5 transition duration-300 ${!isPro ? 'filter blur-sm opacity-50 pointer-events-none' : ''}`}>
                <div className="flex justify-between items-start mb-4">
                  <div>
                    <h4 className="text-2xl font-black text-white mb-1 hover:text-indigo-400 cursor-pointer transition-colors" onClick={() => setSelectedStock(pick)}>{pick.ticker}</h4>
                    <span className={`px-3 py-1 rounded-full text-[10px] font-bold uppercase tracking-wider border ${pick.action === 'BUY' ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' : pick.action === 'SELL' ? 'bg-red-500/10 text-red-400 border-red-500/20' : 'bg-slate-500/10 text-slate-400 border-slate-500/20'}`}>{pick.action}</span>
                  </div>
                  <div className="text-right">
                    <div className="text-xl font-bold text-white font-mono">{pick.current_price || pick.entry_price}</div>
                    <div className="text-[10px] text-slate-500 font-bold mt-1 uppercase tracking-wider">Current Price</div>
                  </div>
                </div>
                <div className="grid grid-cols-3 gap-2 mb-4">
                  <div className="bg-white/5 rounded-lg p-2 border border-white/5"><p className="text-[9px] text-slate-400 font-bold uppercase tracking-wider mb-0.5">Entry</p><p className="text-[11px] font-bold text-white font-mono truncate">{formatEntry(pick)}</p></div>
                  <div className="bg-white/5 rounded-lg p-2 border border-white/5"><p className="text-[9px] text-slate-400 font-bold uppercase tracking-wider mb-0.5">TP</p><p className="text-[11px] font-bold text-emerald-400 font-mono truncate">{formatTP(pick)}</p></div>
                  <div className="bg-white/5 rounded-lg p-2 border border-white/5"><p className="text-[9px] text-slate-400 font-bold uppercase tracking-wider mb-0.5">SL</p><p className="text-[11px] font-bold text-red-400 font-mono truncate">{formatSL(pick)}</p></div>
                </div>
                <div className="mt-auto">
                  <p className="text-sm text-slate-400 mb-6 line-clamp-2">{pick.reasoning}</p>
                  <button onClick={() => setSelectedStock(pick)} className="w-full py-3 rounded-xl font-bold text-white bg-indigo-500 hover:bg-indigo-600 transition text-sm shadow-lg shadow-indigo-500/20">
                    Lihat Detail & Analisis
                  </button>
                </div>
              </div>
            ))}
            {!isPro && picks.length > 1 && (
              <div className="absolute inset-0 bg-[#030712]/60 backdrop-blur-[2px] rounded-3xl flex flex-col justify-center items-center text-center p-8 z-20 border border-white/10">
                <div className="w-16 h-16 bg-gradient-to-tr from-indigo-500 to-purple-500 rounded-2xl flex items-center justify-center mb-6 shadow-xl shadow-indigo-500/20">
                  <span className="text-3xl">🔒</span>
                </div>
                <h4 className="text-2xl font-bold text-white mb-3">Pro Tier Required</h4>
                <p className="text-slate-400 mb-8 max-w-sm">Upgrade ke akun Pro untuk membuka seluruh sinyal trading harian, deteksi algoritma bandarmologi, dan prediksi harga AI lanjutan.</p>
                <button onClick={() => setIsPro(localStorage?.getItem("tier") === "pro")} className="px-8 py-4 rounded-xl font-bold text-white bg-gradient-to-r from-indigo-500 to-purple-500 shadow-lg shadow-purple-500/25 hover:scale-105 transition transform">
                  Upgrade ke Pro ✨
                </button>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
