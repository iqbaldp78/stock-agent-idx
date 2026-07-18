"use client";
import React, { useState, useEffect } from 'react';
import { useApp } from '../../context/AppContext';

interface HistoryRow {
  date: string;
  ticker: string;
  signal: string;
  result: string;
  return_pct: number;
}

interface HistorySummary {
  total_signals: number;
  winning_signals: number;
  losing_signals: number;
  win_rate: number;
  avg_return_pct: number;
  best_pick: HistoryRow | null;
  worst_pick: HistoryRow | null;
  current_streak: number;
  recent_win_rate: number;
  recent_avg_return_pct: number;
}

interface PerformanceMetrics {
  cumulative_pnl?: number;
  win_rate?: number;
  profit_factor?: number;
  sharpe_ratio?: number;
  total_trades?: number;
}

interface IhsgPredictor {
  date: string;
  direction: string;
  confidence: string;
  reasoning: string;
  scores: Record<string, number>;
}

const formatPct = (value: number) => `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`;

const formatCurrency = (value: number) => `Rp ${value.toLocaleString('id-ID')}`;

const formatSignal = (value: string) => value ? value.replace(/_/g, ' ').toUpperCase() : '-';

const formatOutcome = (row: HistoryRow) => {
  if (row?.result === 'PROFIT') return 'Benar';
  if (row?.result === 'LOSS') return 'Salah';
  return 'Pending';
};

const deriveSummary = (rows: HistoryRow[]): HistorySummary => {
  const total = rows.length;
  const wins = rows.filter((row) => row.result === 'PROFIT').length;
  const losses = rows.filter((row) => row.result === 'LOSS').length;
  const avgReturn = total
    ? rows.reduce((acc, row) => acc + Number(row.return_pct || 0), 0) / total
    : 0;

  const bestPick = rows.reduce<HistoryRow | null>((best, row) => {
    if (!best) return row;
    return Number(row.return_pct || 0) > Number(best.return_pct || 0) ? row : best;
  }, null);

  const worstPick = rows.reduce<HistoryRow | null>((worst, row) => {
    if (!worst) return row;
    return Number(row.return_pct || 0) < Number(worst.return_pct || 0) ? row : worst;
  }, null);

  let currentStreak = 0;
  for (const row of rows) {
    if (row.result === 'PROFIT') {
      currentStreak += 1;
    } else {
      break;
    }
  }

  const recent = rows.slice(0, 5);
  const recentWins = recent.filter((row) => row.result === 'PROFIT').length;
  const recentAvgReturn = recent.length
    ? recent.reduce((acc, row) => acc + Number(row.return_pct || 0), 0) / recent.length
    : 0;

  return {
    total_signals: total,
    winning_signals: wins,
    losing_signals: losses,
    win_rate: total ? (wins / total) * 100 : 0,
    avg_return_pct: avgReturn,
    best_pick: bestPick,
    worst_pick: worstPick,
    current_streak: currentStreak,
    recent_win_rate: recent.length ? (recentWins / recent.length) * 100 : 0,
    recent_avg_return_pct: recentAvgReturn,
  };
};

const CustomEquityVsIhsgChart = ({ points }: { points: any[] }) => {
  if (!points || points.length === 0) {
    return (
      <div className="relative w-full h-[260px] bg-card border border-border rounded-3xl p-6 flex flex-col items-center justify-center text-secondary text-sm">
        <p className="font-semibold text-text">Belum ada transaksi</p>
        <p className="text-xs text-secondary mt-1">Lakukan topup dan order pertama Anda di Trading Engine untuk memicu kurva pertumbuhan ekuitas.</p>
      </div>
    );
  }

  const portReturns = points.map(p => p.portfolio_return);
  const ihsgReturns = points.map(p => p.ihsg_return);
  const allReturns = [...portReturns, ...ihsgReturns];
  
  const minVal = Math.min(...allReturns) - 2;
  const maxVal = Math.max(...allReturns) + 2;
  const range = maxVal - minVal || 1;

  const width = 600;
  const height = 200;
  const paddingX = 40;
  const paddingY = 20;
  const pointsCount = points.length;

  const getSvgCoordinates = (values: number[]) => {
    return values.map((val, idx) => {
      const x = paddingX + (idx / (pointsCount - 1 || 1)) * (width - 2 * paddingX);
      const y = height - paddingY - ((val - minVal) / range) * (height - 2 * paddingY);
      return { x, y };
    });
  };

  const portCoords = getSvgCoordinates(portReturns);
  const ihsgCoords = getSvgCoordinates(ihsgReturns);

  const getPathD = (coords: { x: number, y: number }[]) => {
    return coords.reduce((acc, p, idx) => acc + `${idx === 0 ? 'M' : 'L'} ${p.x} ${p.y}`, "");
  };

  const getFillD = (coords: { x: number, y: number }[]) => {
    if (coords.length === 0) return "";
    return `${getPathD(coords)} L ${coords[coords.length - 1].x} ${height - paddingY} L ${coords[0].x} ${height - paddingY} Z`;
  };

  const portPath = getPathD(portCoords);
  const portFill = getFillD(portCoords);
  const ihsgPath = getPathD(ihsgCoords);
  const ihsgFill = getFillD(ihsgCoords);

  const lastPoint = points[points.length - 1];

  return (
    <div className="relative w-full bg-card border border-border rounded-3xl p-6 shadow-xl">
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 mb-6">
        <div>
          <h4 className="text-sm font-bold text-text uppercase tracking-wider">Equity Curve vs IHSG Benchmark</h4>
          <p className="text-xs text-secondary mt-0.5">Pertumbuhan persentase Rekomendasi AI Top Picks dibandingkan pergerakan IHSG.</p>
        </div>
        
        <div className="flex items-center gap-6 text-xs font-semibold">
          <div className="flex items-center gap-2">
            <span className="w-3 h-3 rounded bg-emerald-500/20 border border-emerald-500"></span>
            <span className="text-text font-mono">AI Picks: {lastPoint.portfolio_return >= 0 ? '+' : ''}{lastPoint.portfolio_return.toFixed(2)}%</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-3.5 h-0.5 border-t-2 border-dashed border-gray-400"></span>
            <span className="text-text font-mono">IHSG: {lastPoint.ihsg_return >= 0 ? '+' : ''}{lastPoint.ihsg_return.toFixed(2)}%</span>
          </div>
        </div>
      </div>

      <div className="relative w-full overflow-hidden">
        <svg viewBox={`0 0 ${width} ${height}`} className="w-full h-auto overflow-visible">
          {[0, 0.25, 0.5, 0.75, 1].map((ratio, i) => {
            const y = paddingY + ratio * (height - 2 * paddingY);
            const val = maxVal - ratio * range;
            return (
              <g key={i} className="opacity-20">
                <line x1={paddingX} y1={y} x2={width - paddingX} y2={y} stroke="var(--border)" strokeWidth="1" strokeDasharray="3,3" />
                <text x={paddingX - 10} y={y + 3} fill="currentColor" className="text-[9px] font-mono font-bold text-right text-secondary" textAnchor="end">{val.toFixed(1)}%</text>
              </g>
            );
          })}

          {portFill && <path d={portFill} fill="url(#portGrad)" opacity="0.1" />}
          {ihsgFill && <path d={ihsgFill} fill="url(#ihsgGrad)" opacity="0.05" />}

          {ihsgPath && <path d={ihsgPath} fill="none" stroke="#64748b" strokeWidth="2" strokeDasharray="5,4" strokeLinecap="round" strokeLinejoin="round" />}
          {portPath && <path d={portPath} fill="none" stroke="#10b981" strokeWidth="3.5" strokeLinecap="round" strokeLinejoin="round" className="drop-shadow-[0_2px_10px_rgba(16,185,129,0.4)]" />}

          {portCoords.length > 0 && (
            <circle cx={portCoords[portCoords.length - 1].x} cy={portCoords[portCoords.length - 1].y} r="5" fill="#10b981" className="animate-pulse" />
          )}
          {ihsgCoords.length > 0 && (
            <circle cx={ihsgCoords[ihsgCoords.length - 1].x} cy={ihsgCoords[ihsgCoords.length - 1].y} r="4" fill="#64748b" />
          )}

          <defs>
            <linearGradient id="portGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#10b981" stopOpacity="0.4" />
              <stop offset="100%" stopColor="#10b981" stopOpacity="0.0" />
            </linearGradient>
            <linearGradient id="ihsgGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#64748b" stopOpacity="0.3" />
              <stop offset="100%" stopColor="#64748b" stopOpacity="0.0" />
            </linearGradient>
          </defs>
        </svg>
      </div>

      <div className="flex justify-between items-center mt-3 px-8 text-[10px] text-secondary font-mono">
        <span>{points[0]?.date}</span>
        {pointsCount > 2 && <span>{points[Math.floor(pointsCount / 2)]?.date}</span>}
        <span>{lastPoint?.date}</span>
      </div>
    </div>
  );
};

export default function AIPerformancePage() {
  const { logout } = useApp();
  const [metrics, setMetrics] = useState<PerformanceMetrics | null>(null);
  const [ihsg, setIhsg] = useState<IhsgPredictor | null>(null);
  const [historyRows, setHistoryRows] = useState<HistoryRow[]>([]);
  const [historySummary, setHistorySummary] = useState<HistorySummary | null>(null);
  const [comparisonPoints, setComparisonPoints] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 10;

  useEffect(() => {
    async function fetchData() {
      try {
        const token = localStorage.getItem('token');
        if (!token) {
          logout();
          return;
        }

        const res = await fetch('/api/ai/performance-metrics', {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        });
        
        if (!res.ok) {
          throw new Error('Gagal mengambil data dari server');
        }

        const [metricsRes, historyRes, comparisonRes] = await Promise.all([
          fetch('/api/ai/performance-metrics', {
            headers: {
              'Authorization': `Bearer ${token}`
            }
          }),
          fetch('/api/performance/history'),
          fetch('/api/performance/equity-vs-ihsg', {
            headers: {
              'Authorization': `Bearer ${token}`
            }
          })
        ]);

        if (!metricsRes.ok) {
          throw new Error('Gagal mengambil data dari server');
        }

        const metricsData = await metricsRes.json() as {
          metrics: PerformanceMetrics;
          ihsg_predictor: IhsgPredictor | null;
        };
        setMetrics(metricsData.metrics);
        setIhsg(metricsData.ihsg_predictor);

        if (historyRes.ok) {
          const historyData = await historyRes.json() as {
            history: HistoryRow[];
            summary?: HistorySummary;
          };
          const rows = historyData.history || [];
          setHistoryRows(rows);
          setHistorySummary(historyData.summary || deriveSummary(rows));
        } else {
          setHistoryRows([]);
          setHistorySummary(deriveSummary([]));
        }

        if (comparisonRes.ok) {
          const compData = await comparisonRes.json();
          setComparisonPoints(compData.points || []);
        }
      } catch (err: any) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    }

    fetchData();
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[50vh]">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-accent"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-4 bg-red-500/10 border border-red-500/20 rounded-xl text-red-400">
        Error: {error}
      </div>
    );
  }

  const summary = historySummary || deriveSummary(historyRows);
  const bestPick = summary.best_pick;
  const worstPick = summary.worst_pick;

  const totalPages = Math.ceil(historyRows.length / itemsPerPage) || 1;
  const paginatedRows = historyRows.slice((currentPage - 1) * itemsPerPage, currentPage * itemsPerPage);

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="space-y-3">
        <div className="inline-flex items-center gap-2 rounded-full border border-accent/20 bg-accent/10 px-3 py-1 text-xs font-bold uppercase tracking-[0.2em] text-accent">
          Track record rekomendasi AI
        </div>
        <div>
          <h2 className="text-3xl font-bold text-text mb-2">AI Performance <span className="text-accent">History</span></h2>
          <p className="max-w-3xl text-secondary">Halaman ini menampilkan bukti historis top pick AI, sehingga user bisa mengecek apakah rekomendasi lama benar-benar menghasilkan return positif dan konsisten.</p>
        </div>
      </div>

      <div className="rounded-3xl border border-accent/20 bg-gradient-to-br from-accent/10 via-card to-background p-6 shadow-lg">
        <div className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
          <div className="max-w-2xl space-y-2">
            <p className="text-xs font-bold uppercase tracking-[0.25em] text-accent">Why users trust this</p>
            <h3 className="text-2xl font-black text-text">Validasi performa AI yang bisa dicek, bukan klaim kosong.</h3>
            <p className="text-sm leading-relaxed text-secondary">User dapat melihat win rate, rata-rata return, pick terbaik/terburuk, dan deret rekomendasi yang sudah selesai divalidasi. Ini membantu membangun kepercayaan sekaligus menilai apakah model masih layak diikuti.</p>
          </div>
          <div className="grid grid-cols-2 gap-3 md:min-w-[260px]">
            <div className="rounded-2xl border border-white/10 bg-black/20 p-4">
              <p className="text-xs uppercase tracking-wider text-secondary">Total validasi</p>
              <p className="mt-1 text-2xl font-black text-text">{summary.total_signals}</p>
            </div>
            <div className="rounded-2xl border border-white/10 bg-black/20 p-4">
              <p className="text-xs uppercase tracking-wider text-secondary">Current streak</p>
              <p className="mt-1 text-2xl font-black text-profit">{summary.current_streak}x</p>
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        <div className="rounded-2xl border border-border bg-card p-5 shadow-lg relative">
          <p className="text-sm text-secondary mb-1 flex items-center gap-1 group/tooltip relative">
            Cum. Return
            <span className="flex h-3.5 w-3.5 items-center justify-center rounded-full bg-white/10 text-[9px] cursor-help font-bold">?</span>
            <span className="pointer-events-none absolute bottom-full left-0 mb-2 w-64 rounded-xl border border-border bg-background p-3 text-xs text-secondary opacity-0 shadow-2xl transition-opacity group-hover/tooltip:opacity-100 z-50 leading-relaxed normal-case font-normal">
              <strong className="text-text block mb-1">Cumulative Return</strong>
              Total profit/loss bersih yang telah direalisasikan dari transaksi virtual trading yang posisinya sudah ditutup (realized PnL).
              <span className="block mt-1.5 text-accent font-semibold">Sumber: Histori transaksi virtual trading akun Anda.</span>
            </span>
          </p>
          <h3 className={`text-2xl font-bold ${(metrics?.cumulative_pnl || 0) >= 0 ? 'text-profit' : 'text-loss'}`}>{formatCurrency(metrics?.cumulative_pnl || 0)}</h3>
          <p className="mt-1 text-xs text-secondary">Akumulasi realized PnL dari trade tertutup.</p>
        </div>
        <div className="rounded-2xl border border-border bg-card p-5 shadow-lg relative">
          <p className="text-sm text-secondary mb-1 flex items-center gap-1 group/tooltip relative">
            Win Rate
            <span className="flex h-3.5 w-3.5 items-center justify-center rounded-full bg-white/10 text-[9px] cursor-help font-bold">?</span>
            <span className="pointer-events-none absolute bottom-full left-0 mb-2 w-64 rounded-xl border border-border bg-background p-3 text-xs text-secondary opacity-0 shadow-2xl transition-opacity group-hover/tooltip:opacity-100 z-50 leading-relaxed normal-case font-normal">
              <strong className="text-text block mb-1">Win Rate</strong>
              Persentase keberhasilan sinyal rekomendasi atau transaksi yang menghasilkan profit dibanding total keseluruhan sinyal/transaksi.
              <span className="block mt-1.5 text-accent font-semibold">Sumber: Akumulasi seluruh riwayat transaksi virtual dan validasi rekomendasi AI.</span>
            </span>
          </p>
          <h3 className="text-2xl font-bold text-text">{(metrics?.win_rate ?? summary.win_rate).toFixed(2)}%</h3>
          <p className="mt-1 text-xs text-secondary">{metrics?.total_trades || summary.total_signals} trade / validasi</p>
        </div>
        <div className="rounded-2xl border border-border bg-card p-5 shadow-lg relative">
          <p className="text-sm text-secondary mb-1 flex items-center gap-1 group/tooltip relative">
            Average Return
            <span className="flex h-3.5 w-3.5 items-center justify-center rounded-full bg-white/10 text-[9px] cursor-help font-bold">?</span>
            <span className="pointer-events-none absolute bottom-full left-0 mb-2 w-64 rounded-xl border border-border bg-background p-3 text-xs text-secondary opacity-0 shadow-2xl transition-opacity group-hover/tooltip:opacity-100 z-50 leading-relaxed normal-case font-normal">
              <strong className="text-text block mb-1">Average Return</strong>
              Rata-rata persentase keuntungan atau kerugian per transaksi/sinyal yang dihitung secara matematis.
              <span className="block mt-1.5 text-accent font-semibold">Sumber: Rata-rata imbal hasil dari riwayat rekomendasi AI terdahulu.</span>
            </span>
          </p>
          <h3 className={`text-2xl font-bold ${summary.avg_return_pct >= 0 ? 'text-profit' : 'text-loss'}`}>{formatPct(summary.avg_return_pct)}</h3>
          <p className="mt-1 text-xs text-secondary">Rata-rata return dari riwayat top pick yang sudah selesai.</p>
        </div>
        <div className="rounded-2xl border border-border bg-card p-5 shadow-lg relative">
          <p className="text-sm text-secondary mb-1 flex items-center gap-1 group/tooltip relative">
            Profit Factor
            <span className="flex h-3.5 w-3.5 items-center justify-center rounded-full bg-white/10 text-[9px] cursor-help font-bold">?</span>
            <span className="pointer-events-none absolute bottom-full left-0 mb-2 w-64 rounded-xl border border-border bg-background p-3 text-xs text-secondary opacity-0 shadow-2xl transition-opacity group-hover/tooltip:opacity-100 z-50 leading-relaxed normal-case font-normal">
              <strong className="text-text block mb-1">Profit Factor</strong>
              Rasio total kotor laba (gross profit) dibagi total kotor rugi (gross loss). Angka di atas 1.0x menandakan strategi/sistem menghasilkan profit bersih.
              <span className="block mt-1.5 text-accent font-semibold">Sumber: Akumulasi total keuntungan kotor dibagi total kerugian kotor transaksi virtual Anda.</span>
            </span>
          </p>
          <h3 className="text-2xl font-bold text-amber-400">{(metrics?.profit_factor ?? 0).toFixed(2)}x</h3>
          <p className="mt-1 text-xs text-secondary">Gross profit dibanding gross loss.</p>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        <div className="rounded-3xl border border-border bg-card p-6 shadow-lg">
          <p className="text-xs font-bold uppercase tracking-wider text-secondary mb-2">Best pick</p>
          <h4 className="text-xl font-black text-text">{bestPick?.ticker || '-'}</h4>
          <p className="mt-2 text-sm text-secondary">{bestPick ? `${bestPick.date} · ${bestPick.signal} · ${bestPick.result}` : 'Belum ada data terbaik.'}</p>
          <p className={`mt-3 text-2xl font-black ${Number(bestPick?.return_pct || 0) >= 0 ? 'text-profit' : 'text-loss'}`}>{bestPick ? formatPct(Number(bestPick.return_pct || 0)) : '-'}</p>
        </div>
        <div className="rounded-3xl border border-border bg-card p-6 shadow-lg">
          <p className="text-xs font-bold uppercase tracking-wider text-secondary mb-2">Worst pick</p>
          <h4 className="text-xl font-black text-text">{worstPick?.ticker || '-'}</h4>
          <p className="mt-2 text-sm text-secondary">{worstPick ? `${worstPick.date} · ${worstPick.signal} · ${worstPick.result}` : 'Belum ada data terburuk.'}</p>
          <p className={`mt-3 text-2xl font-black ${Number(worstPick?.return_pct || 0) >= 0 ? 'text-profit' : 'text-loss'}`}>{worstPick ? formatPct(Number(worstPick.return_pct || 0)) : '-'}</p>
        </div>
        <div className="rounded-3xl border border-border bg-card p-6 shadow-lg">
          <p className="text-xs font-bold uppercase tracking-wider text-secondary mb-2">Recent validation</p>
          <h4 className="text-xl font-black text-text">{summary.recent_win_rate.toFixed(2)}%</h4>
          <p className="mt-2 text-sm text-secondary">Win rate 5 sinyal terakhir dengan rata-rata return {formatPct(summary.recent_avg_return_pct)}.</p>
        </div>
      </div>

      <div className="rounded-3xl border border-border bg-card p-6 shadow-lg">
        <div className="flex flex-col gap-2 md:flex-row md:items-end md:justify-between mb-5">
          <div>
            <h3 className="text-xl font-bold text-text">Validated top picks</h3>
            <p className="text-sm text-secondary">Riwayat rekomendasi yang sudah bisa divalidasi hasilnya oleh user.</p>
          </div>
          <div className="flex flex-wrap gap-2 text-xs text-secondary">
            <span className="rounded-full border border-profit/20 bg-profit/10 px-3 py-1 text-profit">PROFIT = benar</span>
            <span className="rounded-full border border-loss/20 bg-loss/10 px-3 py-1 text-loss">LOSS = salah</span>
          </div>
        </div>

        <div className="overflow-x-auto rounded-2xl border border-border bg-background/40">
          <table className="w-full border-collapse text-left text-sm">
            <thead>
              <tr className="border-b border-border bg-white/5 text-xs font-bold uppercase tracking-wider text-secondary">
                <th className="px-6 py-3.5">Tanggal</th>
                <th className="px-6 py-3.5">Ticker</th>
                <th className="px-6 py-3.5 text-center">Signal</th>
                <th className="px-6 py-3.5 text-center">Result</th>
                <th className="px-6 py-3.5 text-right">Return</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5 font-mono text-secondary">
              {paginatedRows.map((row: HistoryRow, idx: number) => (
                <tr key={`${row.date}-${row.ticker}-${idx}`} className="transition hover:bg-white/5">
                  <td className="px-6 py-3.5 font-sans text-text font-medium">{row.date}</td>
                  <td className="px-6 py-3.5 font-bold text-text">{row.ticker}</td>
                  <td className="px-6 py-3.5 text-center">
                    <span className={`inline-flex rounded-full border px-2.5 py-1 text-[11px] font-bold tracking-wider ${row.signal === 'BUY' ? 'border-profit/20 bg-profit/10 text-profit' : row.signal === 'SELL' ? 'border-loss/20 bg-loss/10 text-loss' : 'border-amber-500/20 bg-amber-500/10 text-amber-400'}`}>
                      {formatSignal(row.signal)}
                    </span>
                  </td>
                  <td className="px-6 py-3.5 text-center">
                    <span className={`inline-flex rounded-full border px-2.5 py-1 text-[11px] font-bold tracking-wider ${row.result === 'PROFIT' ? 'border-profit/20 bg-profit/10 text-profit' : row.result === 'LOSS' ? 'border-loss/20 bg-loss/10 text-loss' : 'border-slate-500/20 bg-slate-500/10 text-secondary'}`}>
                      {formatOutcome(row)}
                    </span>
                  </td>
                  <td className={`px-6 py-3.5 text-right font-bold ${Number(row.return_pct || 0) >= 0 ? 'text-profit' : 'text-loss'}`}>
                    {formatPct(Number(row.return_pct || 0))}
                  </td>
                </tr>
              ))}
              {paginatedRows.length === 0 && (
                <tr>
                  <td colSpan={5} className="px-6 py-10 text-center text-secondary font-sans">Belum ada riwayat prediksi yang bisa divalidasi.</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        {totalPages > 1 && (
          <div className="flex items-center justify-between mt-4 px-1 text-xs">
            <button
              onClick={() => setCurrentPage(prev => Math.max(prev - 1, 1))}
              disabled={currentPage === 1}
              className="px-3.5 py-2 rounded-xl bg-white/5 border border-border text-text font-bold hover:bg-white/10 disabled:opacity-30 disabled:pointer-events-none transition"
            >
              Sebelumnya
            </button>
            <span className="text-secondary font-mono">
              Halaman <span className="text-text font-bold">{currentPage}</span> dari <span className="text-text font-bold">{totalPages}</span>
            </span>
            <button
              onClick={() => setCurrentPage(prev => Math.min(prev + 1, totalPages))}
              disabled={currentPage === totalPages}
              className="px-3.5 py-2 rounded-xl bg-white/5 border border-border text-text font-bold hover:bg-white/10 disabled:opacity-30 disabled:pointer-events-none transition"
            >
              Berikutnya
            </button>
          </div>
        )}
      </div>

      {ihsg && (
        <div className="mt-2 rounded-3xl border border-border bg-card p-6 shadow-lg">
          <div className="mb-6 flex flex-col items-start justify-between gap-3 md:flex-row md:items-center">
            <div>
              <h3 className="text-xl font-bold text-text">IHSG Predictor <span className="ml-2 rounded bg-accent/20 px-2 py-1 text-xs text-accent">v2</span></h3>
              <p className="text-sm text-secondary">Prediksi Harian: {ihsg.date}</p>
            </div>
            <div className={`flex items-center gap-2 rounded-full px-3.5 py-1.5 text-xs font-bold uppercase tracking-wider border ${
              ihsg.direction === 'BULLISH'
                ? 'bg-profit/10 text-profit border-profit/20 shadow-[0_0_15px_rgba(34,197,94,0.1)]'
                : ihsg.direction === 'BEARISH'
                ? 'bg-loss/10 text-loss border-loss/20 shadow-[0_0_15px_rgba(239,68,68,0.1)]'
                : 'bg-amber-500/10 text-amber-400 border-amber-500/20 shadow-[0_0_15px_rgba(245,158,11,0.1)]'
            }`}>
              <span className={`w-1.5 h-1.5 rounded-full ${
                ihsg.direction === 'BULLISH' ? 'bg-profit animate-pulse' : ihsg.direction === 'BEARISH' ? 'bg-loss animate-pulse' : 'bg-amber-400 animate-pulse'
              }`}></span>
              <span>{ihsg.direction}</span>
              <span className="text-secondary/50 font-normal">|</span>
              <span className="text-secondary font-mono text-[10px] lowercase tracking-normal">confidence: <span className="font-bold text-text">{ihsg.confidence}</span></span>
            </div>
          </div>

          <div className="grid grid-cols-1 gap-6 md:grid-cols-3">
            <div className="space-y-4 md:col-span-2">
              <div className="rounded-xl border border-white/5 bg-black/30 p-4">
                <h4 className="mb-2 text-sm font-semibold text-gray-400">AI Persona Reasoning</h4>
                <p className="text-sm leading-relaxed text-gray-300">{ihsg.reasoning}</p>
              </div>
            </div>

            <div className="space-y-3">
              <h4 className="mb-2 text-sm font-semibold text-gray-400">Signal Strength (Weights)</h4>
              <div className="space-y-2">
                <div className="mb-1 flex justify-between text-xs">
                  <span className="text-gray-300">Market Breadth (60%)</span>
                  <span className="font-bold text-accent">{(ihsg.scores.breadth || 0).toFixed(2)}</span>
                </div>
                <div className="h-1.5 w-full rounded-full bg-gray-800">
                  <div className="h-1.5 rounded-full bg-accent" style={{ width: `${(ihsg.scores.breadth || 0) * 100}%` }}></div>
                </div>
              </div>
              <div className="space-y-2">
                <div className="mb-1 flex justify-between text-xs">
                  <span className="text-gray-300">Momentum (25%)</span>
                  <span className="font-bold text-amber-400">{(ihsg.scores.momentum || 0).toFixed(2)}</span>
                </div>
                <div className="h-1.5 w-full rounded-full bg-gray-800">
                  <div className="h-1.5 rounded-full bg-amber-400" style={{ width: `${(ihsg.scores.momentum || 0) * 100}%` }}></div>
                </div>
              </div>
              <div className="space-y-2">
                <div className="mb-1 flex justify-between text-xs">
                  <span className="text-gray-300">Macro/News (15%)</span>
                  <span className="font-bold text-profit">{(ihsg.scores.macro || 0).toFixed(2)}</span>
                </div>
                <div className="h-1.5 w-full rounded-full bg-gray-800">
                  <div className="h-1.5 rounded-full bg-profit" style={{ width: `${(ihsg.scores.macro || 0) * 100}%` }}></div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      <CustomEquityVsIhsgChart points={comparisonPoints} />
    </div>
  );
}
