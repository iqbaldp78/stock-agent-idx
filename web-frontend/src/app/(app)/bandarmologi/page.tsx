"use client";
import React, { useState, useEffect } from 'react';
import { useApp } from '../../context/AppContext';

const formatLot = (lots: number) => { if (!lots) return "0"; if (lots >= 1000) return `${(lots / 1000).toFixed(1)}K`; return lots.toLocaleString('id-ID'); };
const formatValue = (val: number) => { if (!val) return "0"; if (val >= 1e9) return `${(val / 1e9).toFixed(2)}B`; if (val >= 1e6) return `${(val / 1e6).toFixed(2)}M`; return val.toLocaleString('id-ID'); };

const getBrokerColorClass = (brokerCode: string) => {
  const code = brokerCode.toUpperCase().trim();
  const foreign = ["AK", "BK", "KZ", "RX", "ZP", "YU", "BB", "DP", "TP", "AI", "KK", "XA", "AG", "DR", "FS", "HD"];
  const retail = ["XL", "XC", "PD", "YP", "AZ", "AT"];
  const institusi = ["CC", "OD", "NI", "DX", "SQ", "LG", "DH", "MG", "CP", "YJ", "HP", "CD", "KI", "BQ", "RF", "SS", "EP", "BS", "OK", "EL", "GR", "IF", "YB", "PO"];
  
  if (foreign.includes(code)) return "text-red-400 font-extrabold";
  if (retail.includes(code)) return "text-green-400 font-extrabold";
  if (institusi.includes(code)) return "text-purple-400 font-extrabold";
  return "text-secondary font-bold"; // Fallback/default style for unclassified brokers
};

const getBrokerBgClass = (brokerCode: string) => {
  const code = brokerCode.toUpperCase().trim();
  const foreign = ["AK", "BK", "KZ", "RX", "ZP", "YU", "BB", "DP", "TP", "AI", "KK", "XA", "AG", "DR", "FS", "HD"];
  const retail = ["XL", "XC", "PD", "YP", "AZ", "AT"];
  const institusi = ["CC", "OD", "NI", "DX", "SQ", "LG", "DH", "MG", "CP", "YJ", "HP", "CD", "KI", "BQ", "RF", "SS", "EP", "BS", "OK", "EL", "GR", "IF", "YB", "PO"];

  if (foreign.includes(code)) return "bg-red-500/10 text-red-400 border-red-500/25";
  if (retail.includes(code)) return "bg-green-500/10 text-green-400 border-green-500/25";
  if (institusi.includes(code)) return "bg-purple-500/10 text-purple-400 border-purple-500/25";
  return "bg-white/5 text-accent border-white/5";
};

const getBrokerTitle = (brokerCode: string) => {
  const code = brokerCode.toUpperCase().trim();
  const foreign = ["AK", "BK", "KZ", "RX", "ZP", "YU", "BB", "DP", "TP", "AI", "KK", "XA", "AG", "DR", "FS", "HD"];
  const retail = ["XL", "XC", "PD", "YP", "AZ", "AT"];
  const institusi = ["CC", "OD", "NI", "DX", "SQ", "LG", "DH", "MG", "CP", "YJ", "HP", "CD", "KI", "BQ", "RF", "SS", "EP", "BS", "OK", "EL", "GR", "IF", "YB", "PO"];
  
  if (foreign.includes(code)) return "Broker Asing (Foreign)";
  if (retail.includes(code)) return "Broker Ritel (Retail)";
  if (institusi.includes(code)) return "Broker Institusi (Institution)";
  return "Broker Tidak Terklasifikasi";
};

const brokerNames: Record<string, string> = {
  YP: "Mirae Asset", PD: "Indo Premier", CC: "Mandiri Sekuritas", NI: "BNI Sekuritas", 
  CP: "Valbury", KK: "Phillip Sekuritas", OD: "BRI Danareksa", DX: "Bahana Sekuritas", 
  AK: "UBS Sekuritas", BK: "J.P. Morgan", KZ: "CLSA Sekuritas", RX: "Macquarie", 
  ZP: "Maybank", YU: "CGS-CIMB", BB: "Verdhana Sekuritas", DP: "DBS Vickers", 
  TP: "OCBC Sekuritas", AI: "UOB Kay Hian", XA: "NH Korindo", AG: "Kiwoom Sekuritas", 
  DR: "RHB Sekuritas", FS: "Reliance", HD: "KGI Sekuritas", XL: "Ajaib Sekuritas", 
  XC: "Stockbit", AZ: "Sucor Sekuritas", AT: "Phintraco", SQ: "BCA Sekuritas", 
  LG: "Trimegah", DH: "Sinarmas", MG: "Semesta Indovest", YJ: "Lotus Andalan", 
  HP: "Henan Putihrai", CD: "Mega Capital", KI: "Ciptadana", BQ: "Ciptadana", RF: "Buana Capital", 
  SS: "Supra Broker", EP: "MNC Sekuritas", BS: "Victoria Sekuritas", OK: "Net Sekuritas", 
  EL: "Evergreen", GR: "Panin Sekuritas", IF: "Samuel Sekuritas", YB: "Jasa Utama", 
  PO: "Pilarmas Investindo"
};

export default function BandarmologiPage() {
  const { showToast } = useApp();
  const [bandarmologiTicker, setBandarmologiTicker] = useState("MEDC");
  const [bandarmologiData, setBandarmologiData] = useState<any | null>(null);
  const [bandarLoading, setBandarLoading] = useState(false);
  const [bandarTimeframe, setBandarTimeframe] = useState("latest");
  const [customDateFrom, setCustomDateFrom] = useState("");
  const [customDateTo, setCustomDateTo] = useState("");
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
      // Create date format YYYY-MM-DD
      const dateStr = new Date().toISOString().split('T')[0];
      const res = await fetch(`/api/bandarmologi/${ticker}?date_from=${dateStr}&date_to=${dateStr}`);
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
          accumulators_custom: data.custom_window?.top_accumulators || [],
          distributors_custom: data.custom_window?.top_distributors || [],
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
      </div>

      {/* Summary Score */}
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
          <div className="min-w-0">
            <p className="text-xs text-secondary font-bold uppercase tracking-wider mb-2">Signal</p>
            <p className={`text-lg xl:text-2xl font-black uppercase tracking-tight truncate ${
              bandarmologiData.summary.signal === 'BUY' || bandarmologiData.summary.signal?.includes('ACCUMULATION') ? 'text-profit' :
              bandarmologiData.summary.signal === 'SELL' || bandarmologiData.summary.signal?.includes('DISTRIBUTION') ? 'text-loss' : 'text-accent'
            }`} title={bandarmologiData.summary.signal?.replace('_', ' ') || 'HOLD'}>
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

      {/* Broker to Watch */}
      {bandarmologiData && bandarmologiData.broker_to_watch && bandarmologiData.broker_to_watch.length > 0 && (
        <div className="bg-card backdrop-blur-md border border-border rounded-3xl p-6 mb-8 relative overflow-hidden">
          <div className="absolute top-0 right-0 w-48 h-48 bg-accent/5 rounded-full blur-3xl -translate-y-1/2 translate-x-1/2 pointer-events-none"></div>
          <div className="flex items-center justify-between mb-6 pb-3 border-b border-border">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-lg bg-accent/15 border border-accent/20 flex items-center justify-center text-accent">
                🕵️‍♂️
              </div>
              <div>
                <h4 className="text-sm font-bold text-text uppercase tracking-widest">Broker to Watch</h4>
                <p className="text-[10px] text-secondary">Aktivitas broker dominan & anomali transaksi</p>
              </div>
            </div>
            <span className={`text-[10px] font-extrabold uppercase tracking-wider px-3 py-1 rounded-full border ${bandarmologiData.signal === 'STRONG_ACCUMULATION' || bandarmologiData.signal === 'ACCUMULATION'
              ? 'bg-profit/10 border-profit/20 text-profit'
              : bandarmologiData.signal === 'DISTRIBUTION' || bandarmologiData.signal === 'STRONG_DISTRIBUTION'
                ? 'bg-loss/10 border-loss/20 text-loss'
                : 'bg-white/5 border-border text-secondary'
              }`}>
              {bandarmologiData.signal || 'NEUTRAL'}
            </span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
            {bandarmologiData.broker_to_watch.map((broker: string, idx: number) => {
              const isAnomalyDist = broker.includes('[ANOMALI DISTRIBUSI]');
              const isAnomalyAcc = broker.includes('[ANOMALI AKUMULASI]');
              const fullText = broker.replace('[ANOMALI DISTRIBUSI]', '').replace('[ANOMALI AKUMULASI]', '').trim();
              const match = fullText.match(/^([A-Z]{2})\s*\((.*)\)$/);
              const code = match ? match[1] : fullText;
              const name = match ? match[2] : '';

              return (
                <div key={idx} className={`flex items-center justify-between p-3.5 rounded-2xl border transition-all duration-300 hover:scale-[1.02] hover:-translate-y-0.5 ${isAnomalyDist ? 'bg-loss/5 hover:bg-loss/10 border-loss/20 hover:border-loss/30 text-red-200 shadow-sm shadow-loss/5' : isAnomalyAcc ? 'bg-profit/5 hover:bg-profit/10 border-profit/20 hover:border-profit/30 text-emerald-200 shadow-sm shadow-profit/5' : 'bg-white/[0.02] hover:bg-white/[0.04] border-border hover:border-accent/30 text-text'}`}>
                  <div className="flex items-center gap-3">
                    <div className={`w-10 h-10 rounded-xl flex items-center justify-center font-mono font-black text-base tracking-wider border ${getBrokerBgClass(code)}`}>{code}</div>
                    <div className="flex flex-col min-w-0">
                      <span className="font-semibold text-xs text-text truncate max-w-[130px]" title={name || brokerNames[code] || code}>{name || brokerNames[code] || 'Unknown Broker'}</span>
                      <span className="text-[10px] text-secondary font-medium">{isAnomalyDist ? 'Anomali Jual' : isAnomalyAcc ? 'Anomali Beli' : 'Top Buyer'}</span>
                    </div>
                  </div>
                  <div>
                    {isAnomalyDist ? (
                      <span className="text-[9px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-md bg-loss/15 text-loss border border-loss/20">Distribusi 🔴</span>
                    ) : isAnomalyAcc ? (
                      <span className="text-[9px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-md bg-profit/15 text-profit border border-profit/20">Akumulasi 🟢</span>
                    ) : (
                      <span className="text-[9px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-md bg-accent/10 text-accent border border-accent/15">Aktif 🔵</span>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
          
          <div className="mt-5 p-3 rounded-xl bg-background/50 border border-border/60 flex flex-wrap gap-x-6 gap-y-2 items-center text-[10px] text-secondary">
            <div className="flex items-center gap-1.5 font-bold"><span className="w-2.5 h-2.5 rounded-full bg-red-400"></span><span className="text-red-400">Foreign</span></div>
            <div className="flex items-center gap-1.5 font-bold"><span className="w-2.5 h-2.5 rounded-full bg-green-400"></span><span className="text-green-400">Retail</span></div>
            <div className="flex items-center gap-1.5 font-bold"><span className="w-2.5 h-2.5 rounded-full bg-purple-400"></span><span className="text-purple-400">Institusi</span></div>
            <span className="text-border">|</span>
            <div className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded-full bg-loss/20 border border-loss/40 flex items-center justify-center"><span className="w-1 h-1 rounded-full bg-loss"></span></span><span>Anomali Jual ≥3× rata-rata.</span></div>
            <div className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded-full bg-profit/20 border border-profit/40 flex items-center justify-center"><span className="w-1 h-1 rounded-full bg-profit"></span></span><span>Anomali Beli ≥3× rata-rata.</span></div>
          </div>
        </div>
      )}

      {/* Tables */}
      {bandarmologiData && (
        <div className="space-y-4">
          <div className="flex flex-wrap items-center gap-2 bg-background p-1.5 rounded-xl border border-border w-full sm:w-fit">
            <div className="flex items-center gap-1">
              <button
                onClick={() => setBandarTimeframe("latest")}
                className={`px-3 py-1.5 rounded-lg transition text-xs font-bold ${bandarTimeframe === 'latest' ? 'bg-accent text-text shadow-lg' : 'text-secondary hover:text-text'}`}
              >Latest</button>
              <button
                onClick={() => setBandarTimeframe("7d")}
                className={`px-3 py-1.5 rounded-lg transition text-xs font-bold ${bandarTimeframe === '7d' ? 'bg-accent text-text shadow-lg' : 'text-secondary hover:text-text'}`}
              >7 Hari</button>
              <button
                onClick={() => setBandarTimeframe("1m")}
                className={`px-3 py-1.5 rounded-lg transition text-xs font-bold ${bandarTimeframe === '1m' ? 'bg-accent text-text shadow-lg' : 'text-secondary hover:text-text'}`}
              >1 Bulan</button>
            </div>
            <div className="flex flex-wrap items-center gap-1.5 border-t sm:border-t-0 sm:border-l border-border pt-1.5 sm:pt-0 sm:pl-2 sm:ml-1 w-full sm:w-auto">
               <input type="date" value={customDateFrom} onChange={(e) => {setCustomDateFrom(e.target.value); setBandarTimeframe('custom');}} className="bg-background text-xs border border-border rounded-lg px-2 py-1 focus:outline-none focus:border-accent text-text max-w-[130px] sm:max-w-none"/>
               <span className="text-secondary text-xs">s/d</span>
               <input type="date" value={customDateTo} onChange={(e) => {setCustomDateTo(e.target.value); setBandarTimeframe('custom');}} className="bg-background text-xs border border-border rounded-lg px-2 py-1 focus:outline-none focus:border-accent text-text max-w-[130px] sm:max-w-none"/>
            </div>
          </div>
        
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
            {/* Accumulators Table */}
            <div className="bg-profit/[0.02] hover:bg-profit/[0.04] border border-profit/20 rounded-2xl p-6 transition duration-300">
            <h3 className="text-lg font-bold text-profit mb-4 flex items-center gap-2">
              <span>🏛️</span> Top Broker Akumulasi ({bandarTimeframe.toUpperCase()})
            </h3>
            <div className="overflow-x-auto rounded-xl border border-profit/10 bg-background/40">
              <table className="w-full text-left border-collapse text-sm">
                <thead>
                  <tr className="border-b border-profit/10 text-[11px] font-bold uppercase tracking-wider text-emerald-300/70 bg-emerald-950/10">
                    <th className="py-3 px-4 whitespace-nowrap">Broker</th>
                    {bandarTimeframe !== 'latest' && <th className="py-3 px-4 whitespace-nowrap">Keaktifan</th>}
                    <th className="py-3 px-4 whitespace-nowrap">Avg Price</th>
                    <th className="py-3 px-4 whitespace-nowrap">Volume (Lot)</th>
                    <th className="py-3 px-4 whitespace-nowrap">Value</th>
                    <th className="py-3 px-4 whitespace-nowrap">Harga vs Cost</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-emerald-500/5 text-secondary font-mono">
                  {(bandarTimeframe === 'latest' || bandarTimeframe === 'custom' ? bandarmologiData.accumulators_custom : (bandarTimeframe === '1m' ? bandarmologiData.accumulators_1m : bandarmologiData.accumulators_7d))?.map((row: any, idx: number) => (
                    (() => {
                      const distancePct = getDistancePct(row);
                      return (
                        <tr key={idx} className="hover:bg-profit/5 transition">
                          <td className={`py-3 px-4 whitespace-nowrap ${getBrokerColorClass(row.broker)}`} title={getBrokerTitle(row.broker)}>{row.broker}</td>
                          {bandarTimeframe !== 'latest' && <td className="py-3 px-4 whitespace-nowrap text-secondary font-medium">{row.active_days || '-'}</td>}
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
                  {!(bandarTimeframe === 'latest' || bandarTimeframe === 'custom' ? bandarmologiData.accumulators_custom : (bandarTimeframe === '1m' ? bandarmologiData.accumulators_1m : bandarmologiData.accumulators_7d))?.length && (
                    <tr><td colSpan={bandarTimeframe === 'latest' ? 5 : 6} className="py-10 text-center text-secondary font-sans font-medium">Tidak ada data akumulasi terdeteksi.</td></tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>

          {/* Distributors Table */}
          <div className="bg-loss/[0.02] hover:bg-loss/[0.04] border border-loss/20 rounded-2xl p-6 transition duration-300">
            <h3 className="text-lg font-bold text-loss mb-4 flex items-center gap-2">
              <span>📉</span> Top Broker Distribusi ({bandarTimeframe.toUpperCase()})
            </h3>
            <div className="overflow-x-auto rounded-xl border border-loss/10 bg-background/40">
              <table className="w-full text-left border-collapse text-sm">
                <thead>
                  <tr className="border-b border-loss/10 text-[11px] font-bold uppercase tracking-wider text-red-300/70 bg-red-950/10">
                    <th className="py-3 px-4 whitespace-nowrap">Broker</th>
                    {bandarTimeframe !== 'latest' && <th className="py-3 px-4 whitespace-nowrap">Keaktifan</th>}
                    <th className="py-3 px-4 whitespace-nowrap">Avg Sell</th>
                    <th className="py-3 px-4 whitespace-nowrap">Volume (Lot)</th>
                    <th className="py-3 px-4 whitespace-nowrap">Value</th>
                    <th className="py-3 px-4 whitespace-nowrap">Harga vs Avg</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-red-500/5 text-secondary font-mono">
                  {(bandarTimeframe === 'latest' || bandarTimeframe === 'custom' ? bandarmologiData.distributors_custom : (bandarTimeframe === '1m' ? bandarmologiData.distributors_1m : bandarmologiData.distributors_7d))?.map((row: any, idx: number) => (
                    (() => {
                      const distancePct = getDistancePct(row);
                      return (
                        <tr key={idx} className="hover:bg-loss/5 transition">
                          <td className={`py-3 px-4 whitespace-nowrap ${getBrokerColorClass(row.broker)}`} title={getBrokerTitle(row.broker)}>{row.broker}</td>
                          {bandarTimeframe !== 'latest' && <td className="py-3 px-4 whitespace-nowrap text-secondary font-medium">{row.active_days || '-'}</td>}
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
                  {!(bandarTimeframe === 'latest' || bandarTimeframe === 'custom' ? bandarmologiData.distributors_custom : (bandarTimeframe === '1m' ? bandarmologiData.distributors_1m : bandarmologiData.distributors_7d))?.length && (
                    <tr><td colSpan={bandarTimeframe === 'latest' ? 5 : 6} className="py-10 text-center text-secondary font-sans font-medium">Tidak ada data distribusi terdeteksi.</td></tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
      )}
    </div>
  );
}
