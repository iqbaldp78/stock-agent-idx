"use client";
import React, { useState, useEffect } from 'react';
import { useApp } from '../../context/AppContext';

const formatLot = (lots: number) => { if (!lots) return "0"; if (lots >= 1000) return `${(lots / 1000).toFixed(1)}K`; return lots.toLocaleString('id-ID'); };
const formatValue = (val: number) => { if (!val) return "0"; if (val >= 1e9) return `${(val / 1e9).toFixed(2)}B`; if (val >= 1e6) return `${(val / 1e6).toFixed(2)}M`; return val.toLocaleString('id-ID'); };

export default function BandarmologiPage() {
  const { showToast } = useApp();
  const [bandarmologiTicker, setBandarmologiTicker] = useState("MEDC");
  const [bandarmologiData, setBandarmologiData] = useState<any | null>(null);
  const [bandarLoading, setBandarLoading] = useState(false);
  const [bandarTimeframe, setBandarTimeframe] = useState("1m");

  const fetchBandarmologiData = async (ticker: string) => {
    setBandarLoading(true);
    try {
      const res = await fetch(`/api/bandarmologi/${ticker}`);
      const data = await res.json();
      if (data && !data.error) setBandarmologiData(data);
    } catch (err) {
      console.error("Error loading bandarmologi data:", err);
    } finally {
      setBandarLoading(false);
    }
  };

  useEffect(() => { fetchBandarmologiData(bandarmologiTicker); }, [bandarmologiTicker]);

  return (
    <div className="space-y-6 animate-fade-in">
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
            )) || ['MEDC', 'ANTM', 'PGAS'].map((t: string) => (
              <option key={t} value={t}>{t}</option>
            ))}
          </select>
          {bandarLoading && <span className="text-xs text-indigo-400 animate-pulse font-bold">Memuat...</span>}
        </div>
        <div className="flex bg-[#030712] p-1 rounded-xl border border-white/10">
          <button
            onClick={() => setBandarTimeframe("1m")}
            className={`px-4 py-1.5 rounded-lg transition text-xs font-bold ${bandarTimeframe === '1m' ? 'bg-indigo-500 text-white shadow-lg' : 'text-slate-400 hover:text-white'}`}
          >1 Bulan (30 Hari)</button>
          <button
            onClick={() => setBandarTimeframe("7d")}
            className={`px-4 py-1.5 rounded-lg transition text-xs font-bold ${bandarTimeframe === '7d' ? 'bg-indigo-500 text-white shadow-lg' : 'text-slate-400 hover:text-white'}`}
          >7 Hari</button>
        </div>
      </div>

      {/* Top Metrics Cards */}
      {bandarmologiData && bandarmologiData.summary && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-6 bg-white/[0.03] backdrop-blur-md border border-white/5 rounded-3xl p-6 mb-8">
          <div>
            <p className="text-xs text-slate-400 font-bold uppercase tracking-wider mb-2">Signal</p>
            <p className={`text-2xl md:text-3xl font-black uppercase tracking-tight ${
              bandarmologiData.summary.signal === 'BUY' || bandarmologiData.summary.signal?.includes('ACCUMULATION') ? 'text-emerald-400' :
              bandarmologiData.summary.signal === 'SELL' || bandarmologiData.summary.signal?.includes('DISTRIBUTION') ? 'text-red-400' : 'text-indigo-400'
            }`}>
              {bandarmologiData.summary.signal?.replace('_', ' ') || 'HOLD'}
            </p>
          </div>
          <div>
            <p className="text-xs text-slate-400 font-bold uppercase tracking-wider mb-2">Score</p>
            <p className="text-2xl md:text-3xl font-black text-white font-mono">{bandarmologiData.score !== undefined ? `${bandarmologiData.score}/10` : '-'}</p>
          </div>
          <div>
            <p className="text-xs text-slate-400 font-bold uppercase tracking-wider mb-2">Current Price</p>
            <p className="text-2xl md:text-3xl font-black text-white font-mono">
              {bandarmologiData.price_analysis?.current_price ? `Rp ${bandarmologiData.price_analysis.current_price.toLocaleString('id-ID')}` : '-'}
            </p>
          </div>
          <div>
            <p className="text-xs text-slate-400 font-bold uppercase tracking-wider mb-2">Entry Status</p>
            <div className="flex items-center gap-2.5">
              <span className={`inline-block w-4 h-4 rounded-full ${
                bandarmologiData.price_analysis?.entry_status?.toLowerCase().includes('ideal') ? 'bg-blue-400 shadow-[0_0_10px_rgba(96,165,250,0.5)]' :
                bandarmologiData.price_analysis?.entry_status?.toLowerCase().includes('acceptable') ? 'bg-emerald-400 shadow-[0_0_10px_rgba(52,211,153,0.5)]' :
                bandarmologiData.price_analysis?.entry_status?.toLowerCase().includes('caution') ? 'bg-amber-400 shadow-[0_0_10px_rgba(251,191,36,0.5)]' :
                bandarmologiData.price_analysis?.entry_status?.toLowerCase().includes('avoid') ? 'bg-red-400 shadow-[0_0_10px_rgba(248,113,113,0.5)]' : 'bg-slate-400'
              }`}></span>
              <span className="text-xl md:text-2xl font-black text-white uppercase tracking-wide">
                {bandarmologiData.price_analysis?.entry_status?.replace(/[^a-zA-Z]/g, '').trim() || 'N/A'}
              </span>
            </div>
          </div>
        </div>
      )}

      {/* Tables */}
      {bandarmologiData && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Accumulators Table */}
          <div className="bg-emerald-500/[0.02] hover:bg-emerald-500/[0.04] border border-emerald-500/20 rounded-2xl p-6 transition duration-300">
            <h3 className="text-lg font-bold text-emerald-400 mb-4 flex items-center gap-2">
              <span>🏛️</span> Top {(bandarTimeframe === '1m' ? bandarmologiData.accumulators_1m : bandarmologiData.accumulators_7d)?.length || 0} Broker Akumulasi ({bandarTimeframe.toUpperCase()})
            </h3>
            <div className="overflow-x-auto rounded-xl border border-emerald-500/10 bg-[#030712]/40">
              <table className="w-full text-left border-collapse text-sm">
                <thead>
                  <tr className="border-b border-emerald-500/10 text-[11px] font-bold uppercase tracking-wider text-emerald-300/70 bg-emerald-950/10">
                    <th className="py-3 px-4 whitespace-nowrap">Broker</th>
                    <th className="py-3 px-4 whitespace-nowrap">Avg Price</th>
                    <th className="py-3 px-4 whitespace-nowrap">Volume (Lot)</th>
                    <th className="py-3 px-4 whitespace-nowrap">Value</th>
                    <th className="py-3 px-4 whitespace-nowrap">Harga vs Cost</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-emerald-500/5 text-slate-300 font-mono">
                  {(bandarTimeframe === '1m' ? bandarmologiData.accumulators_1m : bandarmologiData.accumulators_7d)?.map((row: any, idx: number) => (
                    <tr key={idx} className="hover:bg-emerald-500/5 transition">
                      <td className="py-3 px-4 font-bold text-white whitespace-nowrap">{row.broker}</td>
                      <td className="py-3 px-4 whitespace-nowrap">Rp {row.avg_price.toLocaleString('id-ID')}</td>
                      <td className="py-3 px-4 whitespace-nowrap">{formatLot(row.total_buy_lot)}</td>
                      <td className="py-3 px-4 whitespace-nowrap">{formatValue(row.total_buy_value)}</td>
                      <td className={`py-3 px-4 font-bold whitespace-nowrap ${row.distance_pct === null ? 'text-slate-400' : row.distance_pct >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                        {row.distance_pct !== null ? `${row.distance_pct >= 0 ? '+' : ''}${row.distance_pct.toFixed(2)}%` : '-'}
                      </td>
                    </tr>
                  ))}
                  {!(bandarTimeframe === '1m' ? bandarmologiData.accumulators_1m : bandarmologiData.accumulators_7d)?.length && (
                    <tr><td colSpan={5} className="py-10 text-center text-slate-500 font-sans">Tidak ada data akumulasi terdeteksi.</td></tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>

          {/* Distributors Table */}
          <div className="bg-red-500/[0.02] hover:bg-red-500/[0.04] border border-red-500/20 rounded-2xl p-6 transition duration-300">
            <h3 className="text-lg font-bold text-red-400 mb-4 flex items-center gap-2">
              <span>📉</span> Top {(bandarTimeframe === '1m' ? bandarmologiData.distributors_1m : bandarmologiData.distributors_7d)?.length || 0} Broker Distribusi ({bandarTimeframe.toUpperCase()})
            </h3>
            <div className="overflow-x-auto rounded-xl border border-red-500/10 bg-[#030712]/40">
              <table className="w-full text-left border-collapse text-sm">
                <thead>
                  <tr className="border-b border-red-500/10 text-[11px] font-bold uppercase tracking-wider text-red-300/70 bg-red-950/10">
                    <th className="py-3 px-4 whitespace-nowrap">Broker</th>
                    <th className="py-3 px-4 whitespace-nowrap">Avg Sell</th>
                    <th className="py-3 px-4 whitespace-nowrap">Volume (Lot)</th>
                    <th className="py-3 px-4 whitespace-nowrap">Value</th>
                    <th className="py-3 px-4 whitespace-nowrap">Harga vs Avg</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-red-500/5 text-slate-300 font-mono">
                  {(bandarTimeframe === '1m' ? bandarmologiData.distributors_1m : bandarmologiData.distributors_7d)?.map((row: any, idx: number) => (
                    <tr key={idx} className="hover:bg-red-500/5 transition">
                      <td className="py-3 px-4 font-bold text-white whitespace-nowrap">{row.broker}</td>
                      <td className="py-3 px-4 whitespace-nowrap">Rp {row.avg_price.toLocaleString('id-ID')}</td>
                      <td className="py-3 px-4 whitespace-nowrap">{formatLot(row.total_sell_lot)}</td>
                      <td className="py-3 px-4 whitespace-nowrap">{formatValue(row.total_sell_value)}</td>
                      <td className={`py-3 px-4 font-bold whitespace-nowrap ${row.distance_pct === null ? 'text-slate-400' : row.distance_pct >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                        {row.distance_pct !== null ? `${row.distance_pct >= 0 ? '+' : ''}${row.distance_pct.toFixed(2)}%` : '-'}
                      </td>
                    </tr>
                  ))}
                  {!(bandarTimeframe === '1m' ? bandarmologiData.distributors_1m : bandarmologiData.distributors_7d)?.length && (
                    <tr><td colSpan={5} className="py-10 text-center text-slate-500 font-sans">Tidak ada data distribusi terdeteksi.</td></tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
