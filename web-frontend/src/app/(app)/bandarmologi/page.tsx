"use client";
import React, { useState, useEffect } from 'react';
import { useApp } from '../../context/AppContext';

const formatLot = (lots: number) => { if (!lots) return "0"; if (lots >= 1000) return `${(lots / 1000).toFixed(1)}K`; return lots.toLocaleString('id-ID'); };
const formatValue = (val: number) => { if (!val) return "0"; if (val >= 1e9) return `${(val / 1e9).toFixed(2)}B`; if (val >= 1e6) return `${(val / 1e6).toFixed(2)}M`; return val.toLocaleString('id-ID'); };

const getBrokerColorClass = (brokerCode: string) => {
  const code = brokerCode.toUpperCase().trim();
  const foreign = ["AK", "BK", "KZ", "RX", "ZP", "YU", "BB", "DP", "TP", "AI", "KK", "XA", "AG", "DR", "FS", "HD"];
  const retail = ["XL", "XC", "PD", "YP", "AZ", "AT"];
  const institusi = ["CC", "OD", "NI", "DX", "SQ", "LG", "DH", "MG", "CP", "YJ", "HP", "CD", "KI", "RF", "SS", "EP", "BS", "OK", "EL", "GR", "IF", "YB", "PO"];
  
  if (foreign.includes(code)) return "text-red-400 font-extrabold";
  if (retail.includes(code)) return "text-green-400 font-extrabold";
  if (institusi.includes(code)) return "text-purple-400 font-extrabold";
  return "text-secondary font-bold"; // Fallback/default style for unclassified brokers
};

const getBrokerTitle = (brokerCode: string) => {
  const code = brokerCode.toUpperCase().trim();
  const foreign = ["AK", "BK", "KZ", "RX", "ZP", "YU", "BB", "DP", "TP", "AI", "KK", "XA", "AG", "DR", "FS", "HD"];
  const retail = ["XL", "XC", "PD", "YP", "AZ", "AT"];
  const institusi = ["CC", "OD", "NI", "DX", "SQ", "LG", "DH", "MG", "CP", "YJ", "HP", "CD", "KI", "RF", "SS", "EP", "BS", "OK", "EL", "GR", "IF", "YB", "PO"];
  
  if (foreign.includes(code)) return "Broker Asing (Foreign)";
  if (retail.includes(code)) return "Broker Ritel (Retail)";
  if (institusi.includes(code)) return "Broker Institusi (Institution)";
  return "Broker Tidak Terklasifikasi";
};

export default function BandarmologiPage() {
  const { showToast } = useApp();
  const [bandarmologiTicker, setBandarmologiTicker] = useState("MEDC");
  const [bandarmologiData, setBandarmologiData] = useState<any | null>(null);
  const [bandarLoading, setBandarLoading] = useState(false);
  const [bandarTimeframe, setBandarTimeframe] = useState("1m");

  const getCurrentPrice = () => {
    const fromSummary = Number(bandarmologiData?.summary?.current_price);
    if (Number.isFinite(fromSummary) && fromSummary > 0) return fromSummary;

    const fromAnalysis = Number(bandarmologiData?.price_analysis?.current_price);
    if (Number.isFinite(fromAnalysis) && fromAnalysis > 0) return fromAnalysis;

    return null;
  };

  const getDistancePct = (row: any) => {
    const direct = Number(row?.distance_pct);
    if (Number.isFinite(direct)) return direct;

    const avgPrice = Number(row?.avg_price);
    const currentPrice = getCurrentPrice();
    if (!Number.isFinite(avgPrice) || avgPrice <= 0 || currentPrice === null) return null;

    return ((currentPrice - avgPrice) / avgPrice) * 100;
  };

  const fetchBandarmologiData = async (ticker: string) => {
    setBandarLoading(true);
    try {
      const res = await fetch(`/api/bandarmologi/${ticker}`);
      const data = await res.json();
      if (data && !data.error) {
        // Map agent response to frontend structure
        const mapped = {
          ...data,
          summary: {
            current_price: data.price_analysis?.current_price,
            signal: data.signal,
          },
          accumulators_7d: data.window_7d?.top_accumulators || [],
          accumulators_1m: data.window_1m?.top_accumulators || [],
          distributors_7d: data.window_7d?.top_distributors || [],
          distributors_1m: data.window_1m?.top_distributors || [],
          window_7d_summary: data.window_7d || {},
          window_1m_summary: data.window_1m || {},
        };
        setBandarmologiData(mapped);
      }
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
        <h2 className="text-3xl font-bold text-text mb-2">Analisis <span className="text-accent">Bandarmologi</span></h2>
        <p className="text-secondary">Peta aliran dana institusi besar, rata-rata harga beli/jual bandar, dan status entry zone.</p>
      </div>

      {/* Ticker Selector */}
      <div className="flex flex-wrap items-center justify-between gap-4 bg-white/5 p-4 rounded-2xl border border-border mb-6">
        <div className="flex items-center gap-3">
          <span className="text-secondary font-bold text-sm">Pilih Saham:</span>
          <select
            value={bandarmologiTicker}
            onChange={(e) => setBandarmologiTicker(e.target.value)}
            className="bg-background text-text border border-border rounded-xl px-4 py-2 text-sm focus:outline-none focus:border-accent font-mono font-bold"
          >
            {bandarmologiData?.all_tickers?.map((t: string) => (
              <option key={t} value={t}>{t}</option>
            )) || ['MEDC', 'ANTM', 'PGAS'].map((t: string) => (
              <option key={t} value={t}>{t}</option>
            ))}
          </select>
          {bandarLoading && <span className="text-xs text-accent animate-pulse font-bold">Memuat...</span>}
        </div>
        <div className="flex bg-background p-1 rounded-xl border border-border">
          <button
            onClick={() => setBandarTimeframe("1m")}
            className={`px-4 py-1.5 rounded-lg transition text-xs font-bold ${bandarTimeframe === '1m' ? 'bg-accent text-text shadow-lg' : 'text-secondary hover:text-text'}`}
          >1 Bulan (30 Hari)</button>
          <button
            onClick={() => setBandarTimeframe("7d")}
            className={`px-4 py-1.5 rounded-lg transition text-xs font-bold ${bandarTimeframe === '7d' ? 'bg-accent text-text shadow-lg' : 'text-secondary hover:text-text'}`}
          >7 Hari</button>
        </div>
      </div>

      {/* Broker Legend */}
      <div className="flex flex-wrap items-center gap-4 text-xs bg-white/5 px-4 py-2.5 rounded-2xl border border-border w-fit mb-6">
        <span className="text-secondary font-bold">Kategori Broker:</span>
        <div className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded-full bg-red-400"></span>
          <span className="text-red-400 font-bold">Foreign (Asing)</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded-full bg-green-400"></span>
          <span className="text-green-400 font-bold">Retail (Ritel)</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded-full bg-purple-400"></span>
          <span className="text-purple-400 font-bold">Institusi</span>
        </div>
      </div>

      {/* Top Metrics Cards */}
      {bandarmologiData && bandarmologiData.summary && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-6 bg-card backdrop-blur-md border border-border rounded-3xl p-6 mb-8">
          <div>
            <p className="text-xs text-secondary font-bold uppercase tracking-wider mb-2">Signal</p>
            <p className={`text-2xl md:text-3xl font-black uppercase tracking-tight ${
              bandarmologiData.summary.signal === 'BUY' || bandarmologiData.summary.signal?.includes('ACCUMULATION') ? 'text-profit' :
              bandarmologiData.summary.signal === 'SELL' || bandarmologiData.summary.signal?.includes('DISTRIBUTION') ? 'text-loss' : 'text-accent'
            }`}>
              {bandarmologiData.summary.signal?.replace('_', ' ') || 'HOLD'}
            </p>
          </div>
          <div>
            <p className="text-xs text-secondary font-bold uppercase tracking-wider mb-2">Score</p>
            <p className="text-2xl md:text-3xl font-black text-text font-mono">{bandarmologiData.score !== undefined ? `${bandarmologiData.score}/10` : '-'}</p>
          </div>
          <div>
            <p className="text-xs text-secondary font-bold uppercase tracking-wider mb-2">Current Price</p>
            <p className="text-2xl md:text-3xl font-black text-text font-mono">
              {bandarmologiData.price_analysis?.current_price ? `Rp ${bandarmologiData.price_analysis.current_price.toLocaleString('id-ID')}` : '-'}
            </p>
          </div>
          <div>
            <p className="text-xs text-secondary font-bold uppercase tracking-wider mb-2">Entry Status</p>
            <div className="flex items-center gap-2.5">
              <span className={`inline-block w-4 h-4 rounded-full ${
                bandarmologiData.price_analysis?.entry_status?.toLowerCase().includes('ideal') ? 'bg-blue-400 shadow-[0_0_10px_rgba(96,165,250,0.5)]' :
                bandarmologiData.price_analysis?.entry_status?.toLowerCase().includes('acceptable') ? 'bg-emerald-400 shadow-[0_0_10px_rgba(52,211,153,0.5)]' :
                bandarmologiData.price_analysis?.entry_status?.toLowerCase().includes('caution') ? 'bg-amber-400 shadow-[0_0_10px_rgba(251,191,36,0.5)]' :
                bandarmologiData.price_analysis?.entry_status?.toLowerCase().includes('avoid') ? 'bg-red-400 shadow-[0_0_10px_rgba(248,113,113,0.5)]' : 'bg-slate-400'
              }`}></span>
              <span className="text-xl md:text-2xl font-black text-text uppercase tracking-wide">
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
          <div className="bg-profit/[0.02] hover:bg-profit/[0.04] border border-profit/20 rounded-2xl p-6 transition duration-300">
            <h3 className="text-lg font-bold text-profit mb-4 flex items-center gap-2">
              <span>🏛️</span> Top {(bandarTimeframe === '1m' ? bandarmologiData.accumulators_1m : bandarmologiData.accumulators_7d)?.length || 0} Broker Akumulasi ({bandarTimeframe.toUpperCase()})
            </h3>
            <div className="overflow-x-auto rounded-xl border border-profit/10 bg-background/40">
              <table className="w-full text-left border-collapse text-sm">
                <thead>
                  <tr className="border-b border-profit/10 text-[11px] font-bold uppercase tracking-wider text-emerald-300/70 bg-emerald-950/10">
                    <th className="py-3 px-4 whitespace-nowrap">Broker</th>
                    <th className="py-3 px-4 whitespace-nowrap">Keaktifan</th>
                    <th className="py-3 px-4 whitespace-nowrap">Avg Price</th>
                    <th className="py-3 px-4 whitespace-nowrap">Volume (Lot)</th>
                    <th className="py-3 px-4 whitespace-nowrap">Value</th>
                    <th className="py-3 px-4 whitespace-nowrap">Harga vs Cost</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-emerald-500/5 text-secondary font-mono">
                  {(bandarTimeframe === '1m' ? bandarmologiData.accumulators_1m : bandarmologiData.accumulators_7d)?.map((row: any, idx: number) => (
                    (() => {
                      const distancePct = getDistancePct(row);
                      return (
                        <tr key={idx} className="hover:bg-profit/5 transition">
                          <td className={`py-3 px-4 whitespace-nowrap ${getBrokerColorClass(row.broker)}`} title={getBrokerTitle(row.broker)}>{row.broker}</td>
                          <td className="py-3 px-4 whitespace-nowrap text-secondary font-medium">{row.active_days}</td>
                          <td className="py-3 px-4 whitespace-nowrap">Rp {row.avg_price.toLocaleString('id-ID')}</td>
                          <td className="py-3 px-4 whitespace-nowrap">{formatLot(row.total_buy_lot)}</td>
                          <td className="py-3 px-4 whitespace-nowrap">{formatValue(row.total_buy_value)}</td>
                          <td className={`py-3 px-4 font-bold whitespace-nowrap ${distancePct === null ? 'text-secondary' : distancePct >= 0 ? 'text-profit' : 'text-loss'}`}>
                            {distancePct !== null ? `${distancePct >= 0 ? '+' : ''}${distancePct.toFixed(2)}%` : '-'}
                          </td>
                        </tr>
                      );
                    })()
                  ))}
                  {!(bandarTimeframe === '1m' ? bandarmologiData.accumulators_1m : bandarmologiData.accumulators_7d)?.length && (
                    <tr><td colSpan={6} className="py-10 text-center text-secondary font-sans">Tidak ada data akumulasi terdeteksi.</td></tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>

          {/* Distributors Table */}
          <div className="bg-loss/[0.02] hover:bg-loss/[0.04] border border-loss/20 rounded-2xl p-6 transition duration-300">
            <h3 className="text-lg font-bold text-loss mb-4 flex items-center gap-2">
              <span>📉</span> Top {(bandarTimeframe === '1m' ? bandarmologiData.distributors_1m : bandarmologiData.distributors_7d)?.length || 0} Broker Distribusi ({bandarTimeframe.toUpperCase()})
            </h3>
            <div className="overflow-x-auto rounded-xl border border-loss/10 bg-background/40">
              <table className="w-full text-left border-collapse text-sm">
                <thead>
                  <tr className="border-b border-loss/10 text-[11px] font-bold uppercase tracking-wider text-red-300/70 bg-red-950/10">
                    <th className="py-3 px-4 whitespace-nowrap">Broker</th>
                    <th className="py-3 px-4 whitespace-nowrap">Keaktifan</th>
                    <th className="py-3 px-4 whitespace-nowrap">Avg Sell</th>
                    <th className="py-3 px-4 whitespace-nowrap">Volume (Lot)</th>
                    <th className="py-3 px-4 whitespace-nowrap">Value</th>
                    <th className="py-3 px-4 whitespace-nowrap">Harga vs Avg</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-red-500/5 text-secondary font-mono">
                  {(bandarTimeframe === '1m' ? bandarmologiData.distributors_1m : bandarmologiData.distributors_7d)?.map((row: any, idx: number) => (
                    (() => {
                      const distancePct = getDistancePct(row);
                      return (
                        <tr key={idx} className="hover:bg-loss/5 transition">
                          <td className={`py-3 px-4 whitespace-nowrap ${getBrokerColorClass(row.broker)}`} title={getBrokerTitle(row.broker)}>{row.broker}</td>
                          <td className="py-3 px-4 whitespace-nowrap text-secondary font-medium">{row.active_days}</td>
                          <td className="py-3 px-4 whitespace-nowrap">Rp {row.avg_price.toLocaleString('id-ID')}</td>
                          <td className="py-3 px-4 whitespace-nowrap">{formatLot(row.total_sell_lot)}</td>
                          <td className="py-3 px-4 whitespace-nowrap">{formatValue(row.total_sell_value)}</td>
                          <td className={`py-3 px-4 font-bold whitespace-nowrap ${distancePct === null ? 'text-secondary' : distancePct >= 0 ? 'text-profit' : 'text-loss'}`}>
                            {distancePct !== null ? `${distancePct >= 0 ? '+' : ''}${distancePct.toFixed(2)}%` : '-'}
                          </td>
                        </tr>
                      );
                    })()
                  ))}
                  {!(bandarTimeframe === '1m' ? bandarmologiData.distributors_1m : bandarmologiData.distributors_7d)?.length && (
                    <tr><td colSpan={6} className="py-10 text-center text-secondary font-sans">Tidak ada data distribusi terdeteksi.</td></tr>
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
