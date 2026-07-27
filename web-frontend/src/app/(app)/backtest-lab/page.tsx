"use client";
import React, { useState, useEffect } from 'react';
import { useApp } from '../../context/AppContext';

interface BacktestTrade {
  buy_date: string;
  sell_date: string;
  buy_price: number;
  sell_price: number;
  pnl_pct: number;
  profit: number;
  capital_after: number;
  prob_up: number;
  prob?: number;
}

interface BacktestTickerResult {
  ticker: string;
  pnl: number;
  win_rate: number;
  trades_count: number;
  trades: BacktestTrade[];
}

interface BacktestSession {
  id: number;
  run_date: string;
  horizon: string;
  threshold: number;
  start_date: string;
  end_date: string;
  initial_capital: number;
  final_capital: number;
  total_pnl: number;
  total_trades: number;
  win_rate: number;
  tickers: BacktestTickerResult[];
}

const formatCurrency = (value: number) => `Rp ${value.toLocaleString('id-ID', { maximumFractionDigits: 0 })}`;
const formatPct = (value: number) => `${value > 0 ? '+' : ''}${value.toFixed(2)}%`;

export default function BacktestLabPage() {
  const { logout } = useApp();
  const [sessions, setSessions] = useState<BacktestSession[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedSession, setExpandedSession] = useState<number | null>(null);
  const [expandedTicker, setExpandedTicker] = useState<string | null>(null);

  useEffect(() => {
    async function fetchHistory() {
      try {
        const token = localStorage.getItem('token');
        if (!token) {
          logout();
          return;
        }

        const res = await fetch('/api/backtest/history', {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        });
        
        if (!res.ok) {
          throw new Error('Gagal mengambil data riwayat backtest');
        }

        const data = await res.json();
        setSessions(data.data || []);
      } catch (err: any) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    }

    fetchHistory();
  }, []);

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="space-y-3">
        <div className="inline-flex items-center gap-2 rounded-full border border-emerald-500/20 bg-emerald-500/10 px-3 py-1 text-xs font-bold uppercase tracking-[0.2em] text-emerald-400">
          Laboratorium Simulasi AI
        </div>
        <div>
          <h2 className="text-3xl font-bold text-text mb-2">AI Backtest <span className="text-emerald-400">Lab</span></h2>
          <p className="max-w-3xl text-secondary">Halaman khusus yang membedah arsitektur kecerdasan buatan, menguji teori, dan membuktikan konsistensi strategi trading mesin melalui backtest historis.</p>
        </div>
      </div>

      <div className="rounded-3xl border border-accent/20 bg-slate-900/50 p-6 shadow-lg">
        <h3 className="text-lg font-bold text-emerald-400 mb-4 flex items-center gap-2">
          <span>💡 Insight: Rahasia Performa AI (Win Rate 85-95%)</span>
        </h3>
        <div className="grid md:grid-cols-3 gap-6">
          <div className="p-4 rounded-2xl bg-black/20 border border-white/5">
            <h4 className="font-semibold text-text mb-2 flex items-center gap-2">
              <span>🎯</span> Sangat Selektif
            </h4>
            <p className="text-xs leading-relaxed text-secondary">
              Model tidak memaksa trading setiap hari. Secara cerdas menghindari market sideways/downtrend dan murni hanya masuk saat probabilitas profit &gt; 51%.
            </p>
          </div>
          <div className="p-4 rounded-2xl bg-black/20 border border-white/5">
            <h4 className="font-semibold text-text mb-2 flex items-center gap-2">
              <span>⚡</span> Hit & Run Cepat (1D)
            </h4>
            <p className="text-xs leading-relaxed text-secondary">
              Horizon 1 Hari (Beli sore, Jual besok sore) meminimalisir risiko terseret nyangkut. Sekalinya meleset, batas kerugian terukur sangat kecil.
            </p>
          </div>
          <div className="p-4 rounded-2xl bg-black/20 border border-white/5">
            <h4 className="font-semibold text-text mb-2 flex items-center gap-2">
              <span>❄️</span> Efek Compounding
            </h4>
            <p className="text-xs leading-relaxed text-secondary">
              Menggunakan strategi gulung keuntungan. Profit kecil harian yang secara konsisten diputar ulang (reinvestasi) mampu menghasilkan lonjakan hasil eksponensial.
            </p>
          </div>
        </div>
        <div className="mt-5 pt-4 border-t border-white/5 flex items-start gap-2">
          <span className="text-amber-400 text-sm mt-0.5">⚠️</span>
          <p className="text-[11px] text-secondary">
            <strong className="text-amber-400/90">Dosis Realita:</strong> Simulasi sistem AI di atas menampilkan Gross P&L murni pergerakan harga. Praktik aktualnya belum menyertakan pemotongan <i>fee broker</i>, pajak transaksi ritel, maupun kendala <i>slippage</i> (antrean order) di market nyata.
          </p>
        </div>
      </div>

      <div className="rounded-3xl border border-accent/20 bg-slate-900/50 p-6 shadow-lg mt-8">
        <h3 className="text-xl font-bold text-text mb-4">🔬 Historical Backtest Runs (Database)</h3>
        <p className="text-sm text-secondary mb-6">
          Berikut adalah log sesi backtest terakhir yang dijalankan oleh mesin AI dan disimpan permanen di database sistem.
        </p>
        <div className="mb-6 p-4 rounded-xl bg-blue-900/10 border border-blue-500/20 text-xs text-blue-200 leading-relaxed">
          <strong className="text-blue-400 block mb-1">📝 Notes: Skenario Perhitungan Total Return (Rp)</strong>
          <ul className="list-disc list-inside space-y-1 ml-1 opacity-90">
            <li>Mesin melakukan alokasi modal penuh (<span className="text-blue-300 font-mono">all-in initial capital</span>) pada rekomendasi saham pertama yang sesuai dengan kriteria (di atas threshold Conviction).</li>
            <li>Hasil penjualan beserta modalnya (<span className="text-blue-300 font-mono">realized balance</span>) digulungkan 100% (reinvestasi) pada penemuan sinyal saham berikutnya.</li>
            <li>Pada simulasi All-Universe (banyak Ticker sekaligus), <strong>modal awal disimulasikan terpisah dan utuh sebesar Initial Capital untuk masing-masing Ticker</strong> (skenario single-ticker compound), dan Total Return merupakan agregasi murni dari seluruh performa tersebut.</li>
          </ul>
        </div>

        {loading ? (
          <div className="flex justify-center items-center py-12">
            <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-accent"></div>
          </div>
        ) : error ? (
          <div className="rounded-xl border border-red-500/20 bg-red-500/10 p-6 text-center text-red-400">
            {error}
          </div>
        ) : sessions.length === 0 ? (
          <div className="rounded-xl border border-white/5 bg-black/20 p-8 text-center text-secondary">
            Belum ada histori simulasi backtest tersimpan.
          </div>
        ) : (
          <div className="space-y-4">
            {sessions.map((session) => (
              <div key={session.id} className="rounded-2xl border border-white/10 bg-card overflow-hidden transition-all">
                {/* Session Header (Clickable) */}
                <div 
                  className="p-5 cursor-pointer hover:bg-white/5 flex flex-col md:flex-row gap-4 justify-between items-start md:items-center"
                  onClick={() => {
                    setExpandedSession(expandedSession === session.id ? null : session.id);
                    setExpandedTicker(null);
                  }}
                >
                  <div>
                    <div className="flex items-center gap-3 mb-1">
                      <span className="bg-accent text-background text-xs font-bold px-2 py-0.5 rounded">ID: #{session.id}</span>
                      <span className="text-sm font-semibold text-text">{session.run_date}</span>
                    </div>
                    <div className="text-xs text-secondary font-mono flex flex-wrap gap-x-4 gap-y-1">
                      <span>Periode: {session.start_date} s/d {session.end_date}</span>
                      <span>Target: {session.horizon.toUpperCase()}</span>
                      <span>Conviction: &ge; {session.threshold}</span>
                      <span>Modal Awal (per Ticker): {formatCurrency(session.initial_capital)}</span>
                    </div>
                  </div>
                  
                  <div className="flex gap-6 items-center text-right w-full md:w-auto border-t md:border-none border-white/5 pt-3 md:pt-0">
                    <div>
                      <p className="text-[10px] text-secondary uppercase tracking-wider mb-0.5">Total Return</p>
                      <p className={`font-bold text-lg ${session.total_pnl >= 0 ? 'text-profit' : 'text-loss'}`}>
                        {formatCurrency(session.total_pnl)}
                      </p>
                    </div>
                    <div className="w-20">
                      <p className="text-[10px] text-secondary uppercase tracking-wider mb-0.5">Win Rate</p>
                      <p className="font-mono font-semibold text-text">{session.win_rate.toFixed(1)}%</p>
                    </div>
                    <div className="text-secondary">
                      {expandedSession === session.id ? '▲' : '▼'}
                    </div>
                  </div>
                </div>

                {/* Tickers Detail */}
                {expandedSession === session.id && (
                  <div className="border-t border-white/10 bg-black/40 p-5 animate-in slide-in-from-top-2">
                    <h4 className="text-sm font-bold text-secondary uppercase tracking-wider mb-4">Breakdown per Ticker</h4>
                    <div className="space-y-3">
                      {session.tickers.map((tickerResult, tIdx) => {
                        // Gunakan tIdx + ticker sebagai key unik menghindari duplikasi string
                        const tkey = `${tickerResult.ticker}_${tIdx}`;
                        const isTickerExpanded = expandedTicker === tkey;
                        
                        return (
                          <div key={tkey} className="rounded-xl border border-white/5 bg-background overflow-hidden">
                            {/* Ticker Header */}
                            <div 
                              className="p-4 cursor-pointer hover:bg-white/5 flex justify-between items-center group"
                              onClick={() => setExpandedTicker(isTickerExpanded ? null : tkey)}
                            >
                              <div className="flex items-center gap-3">
                                <span className="text-lg font-bold text-text">{tickerResult.ticker}</span>
                                <span className="text-xs text-secondary">{tickerResult.trades_count} Trade</span>
                              </div>
                              <div className="flex gap-6 items-center text-right">
                                <div>
                                  <p className={`font-semibold ${tickerResult.pnl >= 0 ? 'text-profit' : 'text-loss'}`}>
                                    {formatCurrency(tickerResult.pnl)}
                                  </p>
                                </div>
                                <div className="w-16">
                                  <p className="font-mono text-sm text-text">{tickerResult.win_rate.toFixed(0)}%</p>
                                </div>
                                <div className="flex items-center gap-1.5 text-accent text-xs font-semibold px-2 py-1 rounded bg-accent/10 group-hover:bg-accent/20 transition-colors">
                                  <span>{isTickerExpanded ? 'Tutup Daftar' : 'Buka Trade'}</span>
                                  <span>{isTickerExpanded ? '▲' : '▼'}</span>
                                </div>
                              </div>
                            </div>

                            {/* Ticker Trades List */}
                            {isTickerExpanded && (
                              <div className="border-t border-white/5 p-4 overflow-x-auto">
                                {tickerResult.trades.length === 0 ? (
                                  <p className="text-center text-sm text-secondary py-2">Tidak ada sinyal trade yang memenuhi syarat conviction.</p>
                                ) : (
                                  <table className="w-full text-sm text-left">
                                    <thead className="text-xs text-secondary uppercase bg-black/40 border-b border-white/5">
                                      <tr>
                                        <th className="px-4 py-2 font-medium">Beli</th>
                                        <th className="px-4 py-2 font-medium">Prob</th>
                                        <th className="px-4 py-2 font-medium text-right">Hrg Beli</th>
                                        <th className="px-4 py-2 font-medium">Jual</th>
                                        <th className="px-4 py-2 font-medium text-right">Hrg Jual</th>
                                        <th className="px-4 py-2 font-medium text-right">P&L (%)</th>
                                      </tr>
                                    </thead>
                                    <tbody className="divide-y divide-white/5 font-mono text-xs">
                                      {tickerResult.trades.map((trade, idx) => (
                                        <tr key={idx} className="hover:bg-white/5">
                                          <td className="px-4 py-2 whitespace-nowrap">{trade.buy_date.split('T')[0]}</td>
                                          <td className="px-4 py-2 text-accent">{(trade.prob !== undefined ? trade.prob : (trade.prob_up !== undefined ? trade.prob_up * 100 : 0)).toFixed(1)}%</td>
                                          <td className="px-4 py-2 text-right">{trade.buy_price.toLocaleString('id-ID')}</td>
                                          <td className="px-4 py-2 whitespace-nowrap">{trade.sell_date.split('T')[0]}</td>
                                          <td className="px-4 py-2 text-right">{trade.sell_price.toLocaleString('id-ID')}</td>
                                          <td className={`px-4 py-2 text-right font-bold ${trade.pnl_pct >= 0 ? 'text-profit' : 'text-loss'}`}>
                                            {formatPct(trade.pnl_pct)}
                                          </td>
                                        </tr>
                                      ))}
                                    </tbody>
                                  </table>
                                )}
                              </div>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
