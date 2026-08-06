"use client";
import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useApp } from '../../context/AppContext';
import authenticatedFetch from '@/lib/apiClient';
import { 
  RocketIcon, 
  ArrowDownIcon, 
  UpdateIcon, 
  TargetIcon,
  EyeOpenIcon,
  BarChartIcon,
  LightningBoltIcon
} from '@radix-ui/react-icons';

const extractEntryFromReasoning = (stock: any) => {
  if (!stock || !stock.reasoning) return null;
  const reason = stock.reasoning.toLowerCase();
  
  // Mencari pola angka harga e.g. "1.335", "1.340" yang diawali dengan kata-kata support/pullback/MA/entry/Fibonacci
  const match = reason.match(/(?:pullback ke|support|entry ideal|ideal entry|area|ma\d+ di|fibonacci)(?:\s+(?:di|ke|zona|area|range|level))*\s+(\d{1,3}(?:\.\d{3})+)(?:\s*(?:atau|hingga|sampai|-)\s+(\d{1,3}(?:\.\d{3})+))?/);
  
  if (match) {
    const val1 = parseInt(match[1].replace(/\./g, ''));
    const val2 = match[2] ? parseInt(match[2].replace(/\./g, '')) : null;
    
    if (val1 > 100) { // filter out small numbers
      if (val2 && val2 > 100) {
        const low = Math.min(val1, val2);
        const high = Math.max(val1, val2);
        return { low, high };
      }
      // Jika hanya ada 1 angka, kita jadikan range kecil +/- 1% dari target harga pullback
      const low = Math.round(val1 * 0.99);
      const high = Math.round(val1 * 1.01);
      return { low, high };
    }
  }
  return null;
};

const formatEntry = (stock: any) => {
  if (!stock) return "-";
  if (stock.entry_low === null || stock.entry_low === undefined) return "🔒 Upgrade Pro";
  
  const extracted = extractEntryFromReasoning(stock);
  if (extracted) {
    return `${extracted.low.toLocaleString('id-ID')} - ${extracted.high.toLocaleString('id-ID')}`;
  }
  
  if (stock.entry_low && stock.entry_high) return `${stock.entry_low.toLocaleString('id-ID')} - ${stock.entry_high.toLocaleString('id-ID')}`;
  if (stock.entry_low) return `${stock.entry_low.toLocaleString('id-ID')}`;
  if (stock.entry_high) return `${stock.entry_high.toLocaleString('id-ID')}`;
  return "-";
};

const formatTP = (stock: any) => {
  if (!stock) return "-";
  if (stock.target_1 === null || stock.target_1 === undefined) return "🔒 Upgrade Pro";
  const tps = [stock.target_1, stock.target_2, stock.target_3].filter(tp => tp !== null && tp !== undefined);
  return tps.length > 0 ? tps.map(tp => `${tp.toLocaleString('id-ID')}`).join(" / ") : "-";
};

const formatSL = (stock: any) => {
  if (!stock) return "-";
  if (stock.stop_loss === null || stock.stop_loss === undefined) return "🔒 Upgrade Pro";
  return `${stock.stop_loss.toLocaleString('id-ID')}`;
};
const formatLot = (lots: number) => { if (!lots) return "0"; if (lots >= 1000) return `${(lots / 1000).toFixed(1)}K`; return lots.toLocaleString('id-ID'); };
const formatValue = (val: number) => { if (!val) return "0"; if (val >= 1e9) return `${(val / 1e9).toFixed(2)}B`; if (val >= 1e6) return `${(val / 1e6).toFixed(2)}M`; return val.toLocaleString('id-ID'); };
const formatPercentage = (pct: number) => { if (pct === undefined || pct === null) return "0.00%"; return `${pct >= 0 ? '+' : ''}${pct.toFixed(2)}%`; };

const getBrokerColorClass = (brokerCode: string) => {
  const code = brokerCode.toUpperCase().trim();
  const foreign = ["AK", "BK", "KZ", "RX", "ZP", "YU", "BB", "DP", "TP", "AI", "KK", "XA", "AG", "DR", "FS", "HD"];
  const retail = ["XL", "XC", "PD", "YP", "AZ", "AT"];
  const institusi = ["CC", "OD", "NI", "DX", "SQ", "LG", "DH", "MG", "CP", "YJ", "HP", "CD", "KI", "BQ", "RF", "SS", "EP", "BS", "OK", "EL", "GR", "IF", "YB", "PO"];

  if (foreign.includes(code)) return "text-red-400 font-extrabold";
  if (retail.includes(code)) return "text-green-400 font-extrabold";
  if (institusi.includes(code)) return "text-purple-400 font-extrabold";
  return "text-secondary font-bold";
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

const getEntryType = (stock: any) => {
  if (!stock) return null;
  // Sinyal SELL tidak perlu tipe entry pembelian
  if (stock.action === 'SELL') return null;

  // Prioritas utama: gunakan entry_style dari JSON response backend
  if (stock.entry_style) {
    const style = stock.entry_style.toLowerCase();
    if (style.includes('breakout') || style.includes('bob')) {
      return { label: stock.entry_style, color: "bg-blue-500/10 text-blue-300 border-blue-500/20", icon: <RocketIcon className="w-3.5 h-3.5" /> };
    } else if (style.includes('weakness') || style.includes('bow')) {
      return { label: stock.entry_style, color: "bg-amber-500/10 text-amber-300 border-amber-500/20", icon: <ArrowDownIcon className="w-3.5 h-3.5" /> };
    } else {
      return { label: stock.entry_style, color: "bg-emerald-500/10 text-emerald-300 border-emerald-500/20", icon: <TargetIcon className="w-3.5 h-3.5" /> };
    }
  }
  
  const current = stock.current_price || stock.entry_price || 0;
  
  // Ambil low/high dari hasil ekstraksi reasoning terlebih dahulu, jika gagal fallback ke database
  const extracted = extractEntryFromReasoning(stock);
  const low = extracted ? extracted.low : (stock.entry_low || 0);
  const high = extracted ? extracted.high : (stock.entry_high || 0);

  if (current > 0 && low > 0 && high > 0) {
    if (current < low * 0.995) {
      return { label: "Buy on Breakout", color: "bg-blue-500/10 text-blue-300 border-blue-500/20", icon: <RocketIcon className="w-3.5 h-3.5" /> };
    } else if (current > high * 1.005) {
      return { label: "Buy on Weakness", color: "bg-amber-500/10 text-amber-300 border-amber-500/20", icon: <ArrowDownIcon className="w-3.5 h-3.5" /> };
    } else {
      return { label: "Market Buy", color: "bg-emerald-500/10 text-emerald-300 border-emerald-500/20", icon: <TargetIcon className="w-3.5 h-3.5" /> };
    }
  }
  
  return { label: "Buy on Accumulation", color: "bg-emerald-500/10 text-emerald-300 border-emerald-500/20", icon: <TargetIcon className="w-3.5 h-3.5" /> };
};

export default function TopPicksPage() {
  const { isPro, setIsPro, showToast } = useApp();
  const router = useRouter();
  const [activeTab, setActiveTab] = useState<'regular' | 'konglo'>('regular');
  const [picks, setPicks] = useState<any[]>([]);
  const [runDate, setRunDate] = useState<string>('');
  const [debateCandidates, setDebateCandidates] = useState<any[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [selectedStock, setSelectedStock] = useState<any | null>(null);
  const [showFairValueDetails, setShowFairValueDetails] = useState(false);
  const [showTrueCostDetails, setShowTrueCostDetails] = useState(true);
  const [showDistDetails, setShowDistDetails] = useState(true);

  useEffect(() => {
    let isMounted = true;
    setLoading(true);
    authenticatedFetch(`/api/signals/top-picks?type=${activeTab}`)
      .then(res => res.json())
      .then(data => {
        if (!isMounted) return;
        if (data.data && Array.isArray(data.data)) {
          setPicks(data.data);
          setRunDate(data.run_date || "");
          setDebateCandidates(data.debate_candidates || []);
        } else {
          setPicks([]);
          setRunDate("");
          setDebateCandidates([]);
        }
      })
      .catch(err => {
        console.error("Error loading tab picks:", err);
        if (isMounted) {
          setPicks([]);
          setDebateCandidates([]);
        }
      })
      .finally(() => {
        if (isMounted) setLoading(false);
      });
    return () => { isMounted = false; };
  }, [activeTab]);

  if (selectedStock) {
    return (
      <div className="space-y-6 animate-fade-in">
        <button
          onClick={() => setSelectedStock(null)}
          className="flex items-center gap-2 text-secondary hover:text-text transition group mb-4"
        >
          <span className="w-8 h-8 rounded-full bg-white/5 group-hover:bg-white/10 flex items-center justify-center transition">←</span>
          <span className="text-sm font-semibold">Kembali ke Daftar</span>
        </button>

        <div className="bg-background border border-border rounded-3xl p-8 relative overflow-hidden">
          <div className="absolute top-0 right-0 w-96 h-96 bg-accent/10 rounded-full blur-3xl -translate-y-1/2 translate-x-1/2 pointer-events-none"></div>
          <div className="relative z-10">
            <div className="flex justify-between items-start mb-8">
              <div>
                <h2 className="text-4xl font-black text-text mb-1">{selectedStock.ticker}</h2>
                <p className="text-secondary font-medium text-sm mb-3">Saham Tbk.</p>
                <div className="flex items-center gap-2">
                  <span className={`px-4 py-1.5 rounded-full text-xs font-bold uppercase tracking-wider border inline-block ${selectedStock.action === 'BUY' ? 'bg-profit/10 text-profit border-profit/20' : selectedStock.action === 'SELL' ? 'bg-loss/10 text-loss border-loss/20' : 'bg-slate-500/10 text-secondary border-slate-500/20'}`}>
                    {selectedStock.action}
                  </span>
                  {(() => {
                    const eType = getEntryType(selectedStock);
                    if (!eType) return null;
                    return (
                      <span className={`px-4 py-1.5 rounded-full text-xs font-bold uppercase tracking-wider border inline-flex items-center gap-1.5 ${eType.color}`}>
                        <span>{eType.icon}</span>
                        <span>{eType.label}</span>
                      </span>
                    );
                  })()}
                </div>
              </div>
              <div className="text-right">
                <div className="flex items-center justify-end gap-2">
                  <span className="text-4xl font-bold text-text font-mono">{(selectedStock.current_price || selectedStock.entry_price)?.toLocaleString('id-ID')}</span>
                  {selectedStock.change_percent !== undefined && selectedStock.change_percent !== null && (
                    <span className={`px-2.5 py-1 rounded-lg text-sm font-bold font-mono border ${selectedStock.change_percent >= 0 ? 'bg-profit/10 text-profit border-profit/20' : 'bg-loss/10 text-loss border-loss/20'}`}>
                      {selectedStock.change_percent >= 0 ? '+' : ''}{selectedStock.change_percent.toFixed(2)}%
                    </span>
                  )}
                </div>
                <p className="text-[10px] text-secondary font-bold mt-1 uppercase tracking-wider">Current Price</p>
              </div>
            </div>

            {/* Summary Stats */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
              <div className="bg-white/5 rounded-xl p-4 border border-border">
                <p className="text-xs text-secondary font-bold uppercase tracking-wider mb-1">AI Confidence</p>
                <div className="flex items-end gap-2">
                  <span className="text-2xl font-bold text-accent">{selectedStock.confidence_score}</span>
                  <span className="text-secondary mb-1">/ 10</span>
                </div>
              </div>
              <div className="bg-white/5 rounded-xl p-4 border border-border">
                <p className="text-xs text-secondary font-bold uppercase tracking-wider mb-1">Target Fair Value</p>
                <p className="text-xl font-bold text-profit">{selectedStock.fair_value ? `Rp ${selectedStock.fair_value.toLocaleString('id-ID')}` : "-"}</p>
              </div>
              <div className="bg-white/5 rounded-xl p-4 border border-border">
                <p className="text-xs text-secondary font-bold uppercase tracking-wider mb-1">Bandar Avg Cost</p>
                <p className="text-xl font-bold text-accent">{selectedStock.bandar_avg ? `Rp ${selectedStock.bandar_avg.toLocaleString('id-ID')}` : "-"}</p>
              </div>
              <div className="bg-white/5 rounded-xl p-4 border border-border flex items-center justify-center">
                <button
                  onClick={() => {
                    if (selectedStock.target_1 === null || selectedStock.target_1 === undefined) {
                      showToast("Fitur simulasi transaksi dari sinyal membutuhkan Pro Tier", "error");
                      return;
                    }
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
                  className="w-full py-3 rounded-lg font-bold text-text bg-accent hover:bg-indigo-600 transition text-sm shadow-lg shadow-indigo-500/20"
                >
                  Simulasi Transaksi
                </button>
              </div>
            </div>

            {/* Entry, TP, SL targets */}
            <div className="grid grid-cols-1 md:grid-cols-2 md:grid-cols-3 gap-4 mb-8">
              <div className="bg-white/5 rounded-xl p-4 border border-border flex flex-col justify-center">
                <p className="text-xs text-secondary font-bold uppercase tracking-wider mb-1">Entry Range</p>
                <p className="text-base font-bold text-text font-mono">{formatEntry(selectedStock)}</p>
              </div>
              <div className="bg-white/5 rounded-xl p-4 border border-border flex flex-col justify-center">
                <p className="text-xs text-secondary font-bold uppercase tracking-wider mb-1">Take Profit Targets</p>
                <p className="text-base font-bold text-profit font-mono">{formatTP(selectedStock)}</p>
              </div>
              <div className="bg-white/5 rounded-xl p-4 border border-border flex flex-col justify-center">
                <p className="text-xs text-secondary font-bold uppercase tracking-wider mb-1">Stop Loss</p>
                <p className="text-base font-bold text-loss font-mono">{formatSL(selectedStock)}</p>
              </div>
            </div>

            {/* Fair Value Details */}
            {selectedStock.fair_value_details && (
              <div className="bg-card backdrop-blur-md border border-border rounded-3xl p-6 mb-8 hover:bg-white/5 transition duration-300">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-4 pb-4 border-b border-border">
                  <div className="flex flex-wrap items-center gap-2 text-sm sm:text-base font-semibold text-text">
                    <span className="flex items-center gap-1.5 whitespace-nowrap">
                      <span>💰</span>
                      <span className="text-secondary">Fair Value:</span>
                      <span className={`inline-block w-2.5 h-2.5 rounded-full shrink-0 ${selectedStock.fair_value_details.valuation_label?.includes('UNDERVALUED') ? 'bg-profit shadow-[0_0_10px_rgba(34,197,94,0.5)]' : selectedStock.fair_value_details.valuation_label?.includes('OVERVALUED') ? 'bg-loss shadow-[0_0_10px_rgba(239,68,68,0.5)]' : 'bg-warning shadow-[0_0_10px_rgba(245,158,11,0.5)]'}`}></span>
                      <span className="font-bold text-profit">Rp {(selectedStock.fair_value_details.fair_value_base || selectedStock.fair_value_details.fair_value || 0).toLocaleString('id-ID')}</span>
                    </span>
                    <span className="text-secondary hidden sm:inline">|</span>
                    <span className="flex items-center gap-1 whitespace-nowrap">
                      <span className="text-secondary">Upside:</span>
                      <span className={`font-mono font-bold ${selectedStock.fair_value_details.upside_pct >= 0 ? 'text-profit' : 'text-loss'}`}>
                        {selectedStock.fair_value_details.upside_pct >= 0 ? '+' : ''}{selectedStock.fair_value_details.upside_pct?.toFixed(2)}%
                      </span>
                    </span>
                  </div>
                  <div className="flex items-center shrink-0">
                    <span className="text-secondary font-bold uppercase tracking-wider text-xs bg-white/5 px-2.5 py-1 rounded-md border border-border shrink-0">
                      {selectedStock.fair_value_details.valuation_label?.replace('_', ' ')} ({selectedStock.fair_value_details.confidence})
                    </span>
                  </div>
                </div>
                <button
                  onClick={() => setShowFairValueDetails(!showFairValueDetails)}
                  className="w-full flex items-center justify-between py-2 text-secondary hover:text-text transition font-medium text-sm border border-border bg-white/5 px-4 rounded-xl"
                >
                  <span className="flex items-center gap-2"><span className="text-accent">📐</span> Detail Fair Value {selectedStock.ticker}</span>
                  <span>{showFairValueDetails ? '▲' : '▼'}</span>
                </button>
                {showFairValueDetails && (
                  <div className="mt-4 p-4 rounded-xl bg-background/60 border border-border space-y-4 animate-fade-in">
                    <div className="text-sm font-bold text-secondary">
                      Range: <span className="font-mono text-text">Rp {(selectedStock.fair_value_details.fair_value_low || 0).toLocaleString('id-ID')}</span> – <span className="font-mono text-text">Rp {(selectedStock.fair_value_details.fair_value_high || 0).toLocaleString('id-ID')}</span>
                    </div>
                    <ul className="space-y-2 text-sm text-secondary">
                      {selectedStock.fair_value_details.methods && Object.keys(selectedStock.fair_value_details.methods).map((method) => {
                        const mData = selectedStock.fair_value_details.methods[method];
                        if (!mData || !mData.available) return null;
                        return (
                          <li key={method} className="flex items-center gap-2">
                            <span className="text-accent">•</span>
                            <span className="font-semibold font-mono">{method}:</span>
                            <span className="font-bold text-text">Rp {(mData.fair_value || 0).toLocaleString('id-ID')}</span>
                          </li>
                        );
                      })}
                    </ul>
                  </div>
                )}
              </div>
            )}
            
            {/* ML Prediction Details */}
            <div className="bg-card border border-border rounded-2xl p-6 mb-8">
              <h4 className="text-sm font-bold text-secondary uppercase tracking-widest mb-4 border-b border-border pb-2 flex items-center gap-2">
                <span>🤖</span> ML Prediction
              </h4>
              <div className="flex items-center gap-4 flex-wrap">
                {selectedStock.ml_prediction ? (
                  <>
                    <div className="flex flex-col">
                      <span className="text-xs text-secondary uppercase font-bold tracking-wider mb-1">Signal</span>
                      <span className={`font-mono text-lg font-bold px-3 py-1 rounded-lg ${
                        selectedStock.ml_prediction.signal === 'STRONG BUY' ? 'bg-profit/20 text-profit' : 
                        selectedStock.ml_prediction.signal === 'BUY' ? 'bg-profit/10 text-profit' : 
                        selectedStock.ml_prediction.signal === 'AVOID' ? 'bg-loss/10 text-loss' : 'bg-secondary/10 text-secondary'
                      }`}>
                        {selectedStock.ml_prediction.signal}
                      </span>
                    </div>
                    <div className="flex flex-col">
                      <span className="text-xs text-secondary uppercase font-bold tracking-wider mb-1">Win Prob. (1D)</span>
                      <span className="font-mono text-lg font-bold text-text">
                        {selectedStock.ml_prediction.pred_prob ? `${selectedStock.ml_prediction.pred_prob}%` : '-'}
                      </span>
                    </div>
                    <div className="flex flex-col">
                      <span className="text-xs text-secondary uppercase font-bold tracking-wider mb-1">Confidence</span>
                      <span className="font-mono text-lg font-bold text-text">{selectedStock.ml_prediction.confidence || '-'}</span>
                    </div>
                  </>
                ) : (
                  <div className="text-secondary font-mono">-</div>
                )}
              </div>
            </div>

            {/* Price Projections */}
            {selectedStock.predictions && Object.keys(selectedStock.predictions).length > 0 && (
              <div className="bg-card border border-border rounded-2xl p-6 mb-8">
                <h4 className="text-sm font-bold text-secondary uppercase tracking-widest mb-4 border-b border-border pb-2 flex items-center gap-2">
                  <span>🎯</span> Price Projections
                </h4>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  {['day_1', 'day_3', 'day_5', 'day_7'].map((day, idx) => (
                    selectedStock.predictions[day] && (
                      <div key={idx} className="bg-white/5 rounded-xl p-4 text-center border border-border">
                        <p className="text-xs text-secondary font-mono mb-1">T+{day.split('_')[1]}</p>
                        <p className="font-extrabold text-text text-lg font-mono">{selectedStock.predictions[day].price}</p>
                        <p className={`text-xs font-bold font-mono mt-1 ${String(selectedStock.predictions[day].pct_change).includes('-') ? 'text-loss' : 'text-profit'}`}>
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
                <div className="bg-card border border-border rounded-2xl p-6">
                  <h4 className="text-sm font-bold text-secondary uppercase tracking-widest mb-4 border-b border-border pb-2 flex items-center gap-2"><span>🧠</span> AI Deep Reasoning</h4>
                  <p className="text-sm text-secondary leading-relaxed">{selectedStock.reasoning}</p>
                </div>
                {selectedStock.thesis && (
                  <div className="bg-accent/5 border border-accent/10 rounded-2xl p-6">
                    <h4 className="text-sm font-bold text-accent uppercase tracking-widest mb-4 border-b border-accent/10 pb-2 flex items-center gap-2"><span>📜</span> Investment Thesis</h4>
                    <p className="text-sm text-secondary leading-relaxed">{selectedStock.thesis}</p>
                  </div>
                )}
              </div>
              <div className="space-y-8">
                {selectedStock.key_drivers && selectedStock.key_drivers.length > 0 && (
                  <div className="bg-card border border-border rounded-2xl p-6">
                    <h4 className="text-sm font-bold text-secondary uppercase tracking-widest mb-4 border-b border-border pb-2 flex items-center gap-2"><span>⚡</span> Key Drivers</h4>
                    <ul className="space-y-3">
                      {selectedStock.key_drivers.map((driver: string, idx: number) => (
                        <li key={idx} className="text-sm text-secondary flex items-start gap-3">
                          <span className="text-profit shrink-0 mt-0.5 text-lg leading-none">✓</span>
                          <span>{driver}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
                {selectedStock.risks && selectedStock.risks.length > 0 && (
                  <div className="bg-loss/5 border border-loss/10 rounded-2xl p-6">
                    <h4 className="text-sm font-bold text-red-300 uppercase tracking-widest mb-4 border-b border-loss/10 pb-2 flex items-center gap-2"><span>⚠️</span> Risk Factors</h4>
                    <ul className="space-y-3">
                      {selectedStock.risks.map((risk: string, idx: number) => (
                        <li key={idx} className="text-sm text-secondary flex items-start gap-3">
                          <span className="text-loss shrink-0 mt-0.5 text-lg leading-none">!</span>
                          <span>{risk}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            </div>

            {/* Broker to Watch */}
            {selectedStock.broker_to_watch && selectedStock.broker_to_watch.length > 0 && (
              <div className="bg-card backdrop-blur-md border border-border rounded-3xl p-6 mb-8 mt-8 relative overflow-hidden">
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
                  <span className={`text-[10px] font-extrabold uppercase tracking-wider px-3 py-1 rounded-full border ${selectedStock.bandarm_signal === 'STRONG_ACCUMULATION' || selectedStock.bandarm_signal === 'ACCUMULATION'
                    ? 'bg-profit/10 border-profit/20 text-profit'
                    : selectedStock.bandarm_signal === 'DISTRIBUTION' || selectedStock.bandarm_signal === 'STRONG_DISTRIBUTION'
                      ? 'bg-loss/10 border-loss/20 text-loss'
                      : 'bg-white/5 border-border text-secondary'
                    }`}>
                    {selectedStock.bandarm_signal || 'NEUTRAL'}
                  </span>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
                  {selectedStock.broker_to_watch.map((broker: string, idx: number) => {
                    const isAnomalyDist = broker.includes('[ANOMALI DISTRIBUSI]');
                    const isAnomalyAcc = broker.includes('[ANOMALI AKUMULASI]');

                    // Format broker string e.g. "DX (BNI Sekuritas)"
                    const fullText = broker
                      .replace('[ANOMALI DISTRIBUSI]', '')
                      .replace('[ANOMALI AKUMULASI]', '')
                      .trim();

                    // Pisahkan kode broker dan nama (contoh: "DX (BNI Sekuritas)" -> code: "DX", name: "BNI Sekuritas")
                    const match = fullText.match(/^([A-Z]{2})\s*\((.*)\)$/);
                    const code = match ? match[1] : fullText;
                    const name = match ? match[2] : '';

                    return (
                      <div
                        key={idx}
                        className={`flex items-center justify-between p-3.5 rounded-2xl border transition-all duration-300 hover:scale-[1.02] hover:-translate-y-0.5 ${isAnomalyDist
                          ? 'bg-loss/5 hover:bg-loss/10 border-loss/20 hover:border-loss/30 text-red-200 shadow-sm shadow-loss/5'
                          : isAnomalyAcc
                            ? 'bg-profit/5 hover:bg-profit/10 border-profit/20 hover:border-profit/30 text-emerald-200 shadow-sm shadow-profit/5'
                            : 'bg-white/[0.02] hover:bg-white/[0.04] border-border hover:border-accent/30 text-text'
                          }`}
                      >
                        <div className="flex items-center gap-3">
                          <div className={`w-10 h-10 rounded-xl flex items-center justify-center font-mono font-black text-base tracking-wider border ${getBrokerBgClass(code)}`}>
                            {code}
                          </div>
                          <div className="flex flex-col min-w-0">
                            <span className="font-semibold text-xs text-text truncate max-w-[130px]" title={name || brokerNames[code] || code}>
                              {name || brokerNames[code] || 'Unknown Broker'}
                            </span>
                            <span className="text-[10px] text-secondary font-medium">
                              {isAnomalyDist ? 'Anomali Jual' : isAnomalyAcc ? 'Anomali Beli' : 'Top Buyer'}
                            </span>
                          </div>
                        </div>

                        {/* Status Tag */}
                        <div>
                          {isAnomalyDist ? (
                            <span className="text-[9px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-md bg-loss/15 text-loss border border-loss/20">
                              Distribusi 🔴
                            </span>
                          ) : isAnomalyAcc ? (
                            <span className="text-[9px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-md bg-profit/15 text-profit border border-profit/20">
                              Akumulasi 🟢
                            </span>
                          ) : (
                            <span className="text-[9px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-md bg-accent/10 text-accent border border-accent/15">
                              Aktif 🔵
                            </span>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>

                <div className="mt-5 p-3 rounded-xl bg-background/50 border border-border/60 flex flex-wrap gap-x-6 gap-y-2 items-center text-[10px] text-secondary">
                  <div className="flex items-center gap-1.5 font-bold">
                    <span className="w-2.5 h-2.5 rounded-full bg-red-400"></span>
                    <span className="text-red-400">Foreign</span>
                  </div>
                  <div className="flex items-center gap-1.5 font-bold">
                    <span className="w-2.5 h-2.5 rounded-full bg-green-400"></span>
                    <span className="text-green-400">Retail</span>
                  </div>
                  <div className="flex items-center gap-1.5 font-bold">
                    <span className="w-2.5 h-2.5 rounded-full bg-purple-400"></span>
                    <span className="text-purple-400">Institusi</span>
                  </div>
                  <span className="text-border">|</span>
                  <div className="flex items-center gap-1.5">
                    <span className="w-2.5 h-2.5 rounded-full bg-loss/20 border border-loss/40 flex items-center justify-center"><span className="w-1 h-1 rounded-full bg-loss"></span></span>
                    <span>Anomali Jual ≥3× rata-rata.</span>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <span className="w-2.5 h-2.5 rounded-full bg-profit/20 border border-profit/40 flex items-center justify-center"><span className="w-1 h-1 rounded-full bg-profit"></span></span>
                    <span>Anomali Beli ≥3× rata-rata.</span>
                  </div>
                </div>
              </div>
            )}

            {/* Broker Legend */}
            <div className="flex flex-wrap items-center gap-4 text-xs bg-white/5 px-4 py-2.5 rounded-2xl border border-border w-fit mb-4">
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

            {/* Broker True Cost */}
            {selectedStock.broker_true_cost?.w7 && (
              <div className="bg-card backdrop-blur-md border border-border rounded-3xl p-6 mb-8">
                <button
                  onClick={() => setShowTrueCostDetails(!showTrueCostDetails)}
                  className="w-full flex items-center justify-between py-2 text-text hover:text-text transition font-bold text-base"
                >
                  <span className="flex items-center gap-2"><span className="text-accent">🏛️</span> True Cost Broker Akumulasi (7D)</span>
                  <span>{showTrueCostDetails ? '▲' : '▼'}</span>
                </button>
                {showTrueCostDetails && (
                  <div className="mt-4 animate-fade-in overflow-x-auto rounded-xl border border-border bg-background/40">
                    <table className="w-full text-left border-collapse">
                      <thead>
                        <tr className="border-b border-border text-[11px] font-bold uppercase tracking-wider text-secondary bg-white/5">
                          <th className="py-3 px-4">Broker</th>
                          <th className="py-3 px-4">True Cost</th>
                          <th className="py-3 px-4">Total Buy Lot</th>
                          <th className="py-3 px-4">Total Buy Value</th>
                          <th className="py-3 px-4">Harga vs Cost</th>
                          <th className="py-3 px-4 text-right">Active</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-white/5 text-sm font-mono text-secondary">
                        {selectedStock.broker_true_cost.w7.map((row: any, idx: number) => (
                          <tr key={idx} className="hover:bg-white/5 transition">
                            <td className={`py-3 px-4 whitespace-nowrap ${getBrokerColorClass(row.broker)}`} title={getBrokerTitle(row.broker)}>{row.broker}</td>
                            <td className="py-3 px-4 text-text">Rp {(row.true_cost || 0).toLocaleString('id-ID')}</td>
                            <td className="py-3 px-4">{formatLot(row.total_buy_lot)}</td>
                            <td className="py-3 px-4">{formatValue(row.total_buy_value)}</td>
                            <td className={`py-3 px-4 font-bold ${row.distance_pct >= 0 ? 'text-profit' : 'text-loss'}`}>{formatPercentage(row.distance_pct)}</td>
                            <td className="py-3 px-4 text-right">{row.active_days || '-'}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            )}

            {/* Broker Distribusi */}
            {selectedStock.broker_distributors?.w7 && (
              <div className="bg-card backdrop-blur-md border border-border rounded-3xl p-6 mb-8">
                <button
                  onClick={() => setShowDistDetails(!showDistDetails)}
                  className="w-full flex items-center justify-between py-2 text-text hover:text-text transition font-bold text-base"
                >
                  <span className="flex items-center gap-2"><span className="text-loss">🏛️</span> Avg Sell Broker Distribusi (7D)</span>
                  <span>{showDistDetails ? '▲' : '▼'}</span>
                </button>
                {showDistDetails && (
                  <div className="mt-4 animate-fade-in overflow-x-auto rounded-xl border border-border bg-background/40">
                    <table className="w-full text-left border-collapse">
                      <thead>
                        <tr className="border-b border-border text-[11px] font-bold uppercase tracking-wider text-secondary bg-white/5">
                          <th className="py-3 px-4">Broker</th>
                          <th className="py-3 px-4">Avg Sell</th>
                          <th className="py-3 px-4">Total Sell Lot</th>
                          <th className="py-3 px-4">Total Sell Value</th>
                          <th className="py-3 px-4">Harga vs Avg</th>
                          <th className="py-3 px-4 text-right">Active</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-white/5 text-sm font-mono text-secondary">
                        {selectedStock.broker_distributors.w7.map((row: any, idx: number) => (
                          <tr key={idx} className="hover:bg-white/5 transition">
                            <td className={`py-3 px-4 whitespace-nowrap ${getBrokerColorClass(row.broker)}`} title={getBrokerTitle(row.broker)}>{row.broker}</td>
                            <td className="py-3 px-4 text-text">Rp {(row.avg_sell || row.avg_price || 0).toLocaleString('id-ID')}</td>
                            <td className="py-3 px-4">{formatLot(row.total_sell_lot)}</td>
                            <td className="py-3 px-4">{formatValue(row.total_sell_value)}</td>
                            <td className={`py-3 px-4 font-bold ${row.distance_pct >= 0 ? 'text-profit' : 'text-loss'}`}>{formatPercentage(row.distance_pct)}</td>
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
        <h2 className="text-4xl md:text-5xl font-bold tracking-tight text-text">
          Sinyal Trading Masa Depan, <br />
          <span className="bg-gradient-to-r from-indigo-400 to-purple-400 bg-clip-text text-transparent">Ditenagai oleh AI.</span>
        </h2>
        <p className="text-secondary max-w-2xl mx-auto text-lg">Pilihan saham eksklusif hasil perdebatan beberapa LLM independen dan analisis fundamental teknikal mendalam.</p>
      </div>

      {/* Tab Control Bar (Rata Kiri & Kanan / Full Width) */}
      <div className="w-full pb-2 mb-6">
        <div className="grid grid-cols-2 gap-3 w-full bg-white/5 p-1.5 rounded-2xl border border-white/10">
          <button
            onClick={() => { setActiveTab('regular'); setSelectedStock(null); }}
            className={`flex items-center justify-center gap-2.5 py-3 px-6 rounded-xl font-bold text-sm transition-all duration-200 ${
              activeTab === 'regular'
                ? 'bg-accent/20 text-white border border-accent/40 shadow-sm'
                : 'text-secondary hover:text-text hover:bg-white/5'
            }`}
          >
            <BarChartIcon className="w-4 h-4 text-accent" />
            <span>Regular Top Picks</span>
            {activeTab === 'regular' && picks.length > 0 && (
              <span className="bg-white/10 text-text text-xs px-2 font-mono">
                {picks.length}
              </span>
            )}
          </button>

          <button
            onClick={() => { setActiveTab('konglo'); setSelectedStock(null); }}
            className={`flex items-center justify-center gap-2.5 py-3 px-6 rounded-xl font-bold text-sm transition-all duration-200 ${
              activeTab === 'konglo'
                ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40 shadow-sm'
                : 'text-secondary hover:text-text hover:bg-white/5'
            }`}
          >
            <LightningBoltIcon className="w-4 h-4 text-amber-400" />
            <span>Konglo Play Picks</span>
            {activeTab === 'konglo' && picks.length > 0 && (
              <span className="bg-white/10 text-text text-xs px-2 font-mono">
                {picks.length}
              </span>
            )}
          </button>
        </div>
      </div>

      {loading ? (
        <div className="text-center py-20 space-y-4">
          <div className="w-10 h-10 rounded-full border-2 border-accent border-t-transparent animate-spin mx-auto"></div>
          <p className="text-secondary text-sm font-medium animate-pulse">Memuat sinyal {activeTab === 'konglo' ? 'Konglo Play' : 'Regular'}...</p>
        </div>
      ) : picks.length === 0 ? (
        <div className="bg-card/40 backdrop-blur-md border border-white/10 rounded-3xl p-12 text-center max-w-xl mx-auto space-y-4 shadow-2xl">
          <div className="w-16 h-16 rounded-full bg-amber-500/10 border border-amber-500/20 text-amber-400 flex items-center justify-center mx-auto">
            {activeTab === 'konglo' ? <LightningBoltIcon className="w-8 h-8" /> : <BarChartIcon className="w-8 h-8" />}
          </div>
          <h4 className="text-xl font-bold text-text">
            {activeTab === 'konglo' ? 'Belum Ada Data Konglo Picks' : 'No Data Found'}
          </h4>
          <p className="text-secondary text-sm leading-relaxed">
            {activeTab === 'konglo'
              ? "Belum ada sinyal Konglo Play yang aktif saat ini. Silakan jalankan 'Konglo Analysis' melalui dashboard Streamlit terlebih dahulu."
              : "Tidak ada sinyal rekomendasi saham yang aktif saat ini dari AI."}
          </p>
        </div>
      ) : (
        <div className="space-y-8">
          <div className="flex justify-between items-end mb-2">
            <h3 className="text-2xl font-bold text-text">Today&apos;s AI Picks</h3>
            <p className="text-sm text-secondary">Running Date: <span className="font-mono text-accent">{runDate}</span></p>
          </div>

          {/* 1st Top Pick (Featured) */}
          <div className="bg-gradient-to-b from-accent/10 to-transparent border border-accent/20 rounded-3xl p-1 shadow-[0_0_50px_rgba(124,58,237,0.05)] relative overflow-hidden">
            <div className="absolute top-0 right-0 w-64 h-64 bg-accent/10 rounded-full blur-3xl -translate-y-1/2 translate-x-1/2"></div>
            <div className="bg-background/80 backdrop-blur-xl rounded-[23px] p-8 h-full flex flex-col relative z-10">
              <div className="flex justify-between items-start mb-6">
                <div>
                  <h4 className="text-3xl font-black text-text hover:text-accent cursor-pointer transition-colors mb-1" onClick={() => setSelectedStock(picks[0])}>
                    {picks[0].ticker}
                  </h4>
                  <p className="text-secondary font-medium text-sm mb-3">Saham Tbk.</p>
                  <div className="flex items-center gap-2">
                    <span className={`px-4 py-1.5 rounded-full text-xs font-bold uppercase tracking-wider border inline-block ${picks[0].action === 'BUY' ? 'bg-profit/10 text-profit border-profit/20' : picks[0].action === 'SELL' ? 'bg-loss/10 text-loss border-loss/20' : 'bg-slate-500/10 text-secondary border-slate-500/20'}`}>
                      {picks[0].action}
                    </span>
                    {(() => {
                      const eType = getEntryType(picks[0]);
                      if (!eType) return null;
                      return (
                        <span className={`px-4 py-1.5 rounded-full text-xs font-bold uppercase tracking-wider border inline-flex items-center gap-1.5 ${eType.color}`}>
                          <span>{eType.icon}</span>
                          <span>{eType.label}</span>
                        </span>
                      );
                    })()}
                  </div>
                </div>
                <div className="text-right">
                  <div className="flex items-center justify-end gap-2">
                    <span className="text-3xl font-bold text-text font-mono">{(picks[0].current_price || picks[0].entry_price)?.toLocaleString('id-ID')}</span>
                    {picks[0].change_percent !== undefined && picks[0].change_percent !== null && (
                      <span className={`px-2.5 py-1 rounded-full text-xs font-bold font-mono border ${picks[0].change_percent >= 0 ? 'bg-profit/10 text-profit border-profit/20' : 'bg-loss/10 text-loss border-loss/20'}`}>
                        {picks[0].change_percent >= 0 ? '+' : ''}{picks[0].change_percent.toFixed(2)}%
                      </span>
                    )}
                  </div>
                  <p className="text-secondary text-xs mt-1 uppercase font-bold tracking-widest">Current Price</p>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4 mb-4">
                <div className="bg-white/5 rounded-xl p-4 border border-border">
                  <p className="text-xs text-secondary font-bold uppercase tracking-wider mb-1">AI Confidence</p>
                  <div className="flex items-end gap-2">
                    <span className="text-2xl font-bold text-accent">{picks[0].confidence_score}</span>
                    <span className="text-secondary mb-1">/ 10</span>
                  </div>
                </div>
                <div className="bg-white/5 rounded-xl p-4 border border-border">
                  <p className="text-xs text-secondary font-bold uppercase tracking-wider mb-1">Risk Profile</p>
                  <p className="text-xl font-bold text-text">Moderate</p>
                </div>
              </div>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-4 mb-8">
                <div className="bg-white/5 rounded-xl p-4 border border-border"><p className="text-[10px] text-secondary font-bold uppercase tracking-wider mb-1">Entry Range</p><p className="text-sm font-bold text-text font-mono">{formatEntry(picks[0])}</p></div>
                <div className="bg-white/5 rounded-xl p-4 border border-border"><p className="text-[10px] text-secondary font-bold uppercase tracking-wider mb-1">Take Profit</p><p className="text-sm font-bold text-profit font-mono">{formatTP(picks[0])}</p></div>
                <div className="bg-white/5 rounded-xl p-4 border border-border"><p className="text-[10px] text-secondary font-bold uppercase tracking-wider mb-1">Stop Loss</p><p className="text-sm font-bold text-loss font-mono">{formatSL(picks[0])}</p></div>
              </div>
              <div className="mt-auto">
                <p className="text-sm text-secondary mb-6 line-clamp-2">{picks[0].reasoning}</p>
                <button onClick={() => setSelectedStock(picks[0])} className="w-full py-4 rounded-xl font-bold text-text bg-accent hover:bg-indigo-600 transition shadow-lg shadow-indigo-500/20 text-lg">
                  Lihat Detail & Analisis
                </button>
              </div>
            </div>
          </div>

          {/* Grid remaining picks */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 md:gap-6 relative">
            {picks.slice(1).map((pick, i) => (
              <div key={i} className="bg-card backdrop-blur-md border border-border rounded-3xl p-6 flex flex-col hover:bg-white/5 transition duration-300">
                <div className="flex justify-between items-start mb-4">
                  <div>
                    <h4 className="text-2xl font-black text-text mb-1 hover:text-accent cursor-pointer transition-colors" onClick={() => setSelectedStock(pick)}>{pick.ticker}</h4>
                    <div className="flex items-center gap-1.5 flex-wrap">
                      <span className={`px-3 py-1 rounded-full text-[10px] font-bold uppercase tracking-wider border ${pick.action === 'BUY' ? 'bg-profit/10 text-profit border-profit/20' : pick.action === 'SELL' ? 'bg-loss/10 text-loss border-loss/20' : 'bg-slate-500/10 text-secondary border-slate-500/20'}`}>{pick.action}</span>
                      {(() => {
                        const eType = getEntryType(pick);
                        if (!eType) return null;
                        return (
                          <span className={`px-3 py-1 rounded-full text-[10px] font-bold uppercase tracking-wider border inline-flex items-center gap-1 ${eType.color}`}>
                            <span>{eType.icon}</span>
                            <span>{eType.label}</span>
                          </span>
                        );
                      })()}
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="flex items-center justify-end gap-1.5">
                      <span className="text-xl font-bold text-text font-mono">{(pick.current_price || pick.entry_price)?.toLocaleString('id-ID')}</span>
                      {pick.change_percent !== undefined && pick.change_percent !== null && (
                        <span className={`px-2 py-0.5 rounded text-[10px] font-bold font-mono border ${pick.change_percent >= 0 ? 'bg-profit/10 text-profit border-profit/20' : 'bg-loss/10 text-loss border-loss/20'}`}>
                          {pick.change_percent >= 0 ? '+' : ''}{pick.change_percent.toFixed(2)}%
                        </span>
                      )}
                    </div>
                    <div className="text-[10px] text-secondary font-bold mt-1 uppercase tracking-wider">Current Price</div>
                  </div>
                </div>
                <div className="grid grid-cols-2 md:grid-cols-3 gap-2 mb-4">
                  <div className="bg-white/5 rounded-lg p-2 border border-border"><p className="text-[9px] text-secondary font-bold uppercase tracking-wider mb-0.5">Range</p><p className="text-[11px] font-bold text-text font-mono truncate">{formatEntry(pick)}</p></div>
                  <div className="bg-white/5 rounded-lg p-2 border border-border"><p className="text-[9px] text-secondary font-bold uppercase tracking-wider mb-0.5">TP</p><p className="text-[11px] font-bold text-profit font-mono truncate">{formatTP(pick)}</p></div>
                  <div className="bg-white/5 rounded-lg p-2 border border-border"><p className="text-[9px] text-secondary font-bold uppercase tracking-wider mb-0.5">SL</p><p className="text-[11px] font-bold text-loss font-mono truncate">{formatSL(pick)}</p></div>
                </div>
                <div className="mt-auto">
                  <p className="text-sm text-secondary mb-6 line-clamp-2">{pick.reasoning}</p>
                  <button onClick={() => setSelectedStock(pick)} className="w-full py-3 rounded-xl font-bold text-text bg-accent hover:bg-indigo-600 transition text-sm shadow-lg shadow-indigo-500/20">
                    Lihat Detail & Analisis
                  </button>
                </div>
              </div>
            ))}
          </div>

          {/* Section: Debate Candidates */}
          {debateCandidates && debateCandidates.length > 0 && (
            <div className="mt-12 bg-card border border-border rounded-3xl p-6 md:p-8 relative overflow-hidden">
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-6 border-b border-border/50 pb-4">
                <div>
                  <h3 className="text-xl md:text-2xl font-bold text-text flex items-center gap-2">
                    <span>💬</span>
                    <span>Kandidat Debat Multi-Agent (10 Besar)</span>
                  </h3>
                  <p className="text-secondary text-sm mt-1">
                    Daftar emiten dengan peringkat skor komposit tertinggi yang lolos ke tahap debat multi-agent harian.
                  </p>
                </div>
              </div>
              
              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse">
                  <thead>
                    <tr className="border-b border-border/50 text-[10px] uppercase tracking-wider text-secondary font-bold">
                      <th className="pb-3 pr-4">Saham</th>
                      <th className="pb-3 px-4 text-center">Score Komposit</th>
                      <th className="pb-3 px-4 text-center">Bandarmologi</th>
                      <th className="pb-3 px-4 text-center">Technical</th>
                      <th className="pb-3 px-4 text-center">Fundamental</th>
                      <th className="pb-3 px-4 text-center">Weight Mode</th>
                      <th className="pb-3 pl-4 text-right">Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {debateCandidates.map((cand: any, idx: number) => {
                      const isPicked = picks.some((p: any) => p.ticker === cand.ticker);
                      return (
                        <tr key={idx} className="border-b border-border/30 last:border-0 hover:bg-white/[0.02] transition duration-200">
                          <td className="py-4 pr-4 font-black text-text text-lg">{cand.ticker}</td>
                          <td className="py-4 px-4 text-center font-mono font-bold text-accent text-base">{cand.composite_score.toFixed(2)}</td>
                          <td className="py-4 px-4 text-center font-mono text-text/80">{cand.bandarm_score.toFixed(1)}</td>
                          <td className="py-4 px-4 text-center font-mono text-text/80">{cand.technical_score.toFixed(1)}</td>
                          <td className="py-4 px-4 text-center font-mono text-text/80">{cand.fundamental_score.toFixed(1)}</td>
                          <td className="py-4 px-4 text-center text-secondary text-xs capitalize">{cand.weight_mode.replace('_', ' ')}</td>
                          <td className="py-4 pl-4 text-right">
                            {isPicked ? (
                              <span className="px-2.5 py-1 bg-profit/10 text-profit border border-profit/20 rounded-full text-[10px] font-bold uppercase tracking-wider">
                                Top Picked
                              </span>
                            ) : (
                              <span className="px-2.5 py-1 bg-white/5 text-secondary border border-border rounded-full text-[10px] font-semibold">
                                Eliminated
                              </span>
                            )}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
