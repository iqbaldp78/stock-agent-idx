"use client";
import React, { useState, useEffect } from 'react';
import { useApp } from '../context/AppContext';
import { Card, CardContent } from '@/components/ui/card';
import {
  ArrowUpIcon,
  ArrowDownIcon,
  TargetIcon,
  BarChartIcon,
  InfoCircledIcon,
  LoopIcon,
  CheckCircledIcon,
  StarIcon,
  RocketIcon,
  MagnifyingGlassIcon,
  ReaderIcon,
  ChatBubbleIcon
} from '@radix-ui/react-icons';

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

          {portFill && <path d={portFill} fill="url(#portGradDashboard)" opacity="0.1" />}
          {ihsgFill && <path d={ihsgFill} fill="url(#ihsgGradDashboard)" opacity="0.05" />}

          {ihsgPath && <path d={ihsgPath} fill="none" stroke="#64748b" strokeWidth="2" strokeDasharray="5,4" strokeLinecap="round" strokeLinejoin="round" />}
          {portPath && <path d={portPath} fill="none" stroke="#10b981" strokeWidth="3.5" strokeLinecap="round" strokeLinejoin="round" className="drop-shadow-[0_2px_10px_rgba(16,185,129,0.4)]" />}

          {portCoords.length > 0 && (
            <circle cx={portCoords[portCoords.length - 1].x} cy={portCoords[portCoords.length - 1].y} r="5" fill="#10b981" className="animate-pulse" />
          )}
          {ihsgCoords.length > 0 && (
            <circle cx={ihsgCoords[ihsgCoords.length - 1].x} cy={ihsgCoords[ihsgCoords.length - 1].y} r="4" fill="#64748b" />
          )}

          <defs>
            <linearGradient id="portGradDashboard" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#10b981" stopOpacity="0.4" />
              <stop offset="100%" stopColor="#10b981" stopOpacity="0.0" />
            </linearGradient>
            <linearGradient id="ihsgGradDashboard" x1="0" y1="0" x2="0" y2="1">
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

export default function DashboardPage() {
  const { stats, wallet, holdings, loading, isPro } = useApp();
  const [username, setUsername] = useState("");
  const [comparisonPoints, setComparisonPoints] = useState<any[]>([]);
  const [activeStep, setActiveStep] = useState(0);

  const steps = [
    {
      title: "1. Data Filtering & Quantitative Screening",
      short: "1. Filtering",
      icon: MagnifyingGlassIcon,
      desc: "Platform memproses data teknikal historis (harga open, high, low, close, volume) dan melacak pergerakan transaksi foreign flow (bandarmologi) untuk menyaring saham dengan akumulasi beli tersembunyi yang kuat.",
      logs: [
        "> [INIT] Mengambil data historis bursa...",
        "> [VOLUME] Analisis kelayakan likuiditas harian...",
        "> [BANDAR] Mendeteksi net buy asing & domestik...",
        "> [FILTER] Berhasil menyaring 12 emiten potensial."
      ]
    },
    {
      title: "2. News Sentiment & Market Intelligence Agent",
      short: "2. News Agent",
      icon: ReaderIcon,
      desc: "Agent khusus AI memindai ratusan artikel berita terbaru, pengumuman korporat resmi dari emiten di bursa (IDX), serta sentimen media sosial untuk menghitung sentimen pasar kumulatif.",
      logs: [
        "> [AGENT] Mengindeks berita pasar terbaru...",
        "> [SENTIMENT] Membaca laporan keuangan emiten...",
        "> [SENTIMENT] Nilai sentimen: 85% Positif",
        "> [AGENT] Sentimen emiten terverifikasi OPTIMIS."
      ]
    },
    {
      title: "3. Multi-Agent LLM Debate Arena",
      short: "3. Agent Debate",
      icon: ChatBubbleIcon,
      desc: "Tiga model AI (Bullish Agent, Bearish Agent, dan Neutral Advisor) berdiskusi secara interaktif untuk menganalisis kelemahan dan kekuatan prospek saham agar rekomendasi bebas dari bias subjektif.",
      logs: [
        "> [ROOM] Memulai sesi debat multi-agent...",
        "> [BULL_AGENT] Menemukan pola MA20 golden cross.",
        "> [BEAR_AGENT] Peringatan: Volume melemah dekat resistance.",
        "> [ADVISOR] Mengusulkan target beli aman dekat support."
      ]
    },
    {
      title: "4. Consensus & Dynamic Signal Generation",
      short: "4. Consensus Signal",
      icon: TargetIcon,
      desc: "Hasil perdebatan dirumuskan menjadi konsensus keputusan akhir. Model menghitung skor tingkat kepercayaan, arah transaksi (BUY/HOLD/AVOID), serta menentukan batas Entry Range, target Take Profit (TP), dan Stop Loss (SL).",
      logs: [
        "> [CONSENSUS] Menghitung keputusan akhir...",
        "> [DECISION] Keputusan: BUY. Confidence: 8.5/10",
        "> [CALCULATION] Target TP1: +5.0% | SL: -3.0%",
        "> [SIGNAL] Sinyal Top Picks berhasil diterbitkan."
      ]
    }
  ];

  useEffect(() => {
    try {
      const token = localStorage.getItem("token");
      if (token) {
        const payloadBase64 = token.split('.')[1];
        if (payloadBase64) {
          const payloadString = atob(payloadBase64);
          const payloadData = JSON.parse(payloadString);
          if (payloadData.sub) {
            setUsername(payloadData.sub);
          }
        }
      }
    } catch (e) {
      console.error("Failed to decode token", e);
    }
  }, []);

  useEffect(() => {
    async function fetchComparisonData() {
      try {
        const token = localStorage.getItem("token");
        if (!token) return;
        const res = await fetch('/api/performance/equity-vs-ihsg', {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        });
        if (res.ok) {
          const data = await res.json();
          setComparisonPoints(data.points || []);
        }
      } catch (err) {
        console.error(err);
      }
    }
    fetchComparisonData();
  }, []);

  return (
    <div className="animate-fade-in space-y-10">
      {/* Hero Section */}
      <div className="text-center space-y-4 py-8">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-accent/10 border border-accent/20 text-accent text-xs font-semibold uppercase tracking-widest mb-4">
          <span className="w-1.5 h-1.5 rounded-full bg-accent animate-pulse"></span>
          AI Model is Active
        </div>
        <h2 className="text-3xl sm:text-4xl md:text-5xl font-bold tracking-tight text-text">
          Selamat Datang, {username || "Trader"}! <br />
          <span className="bg-gradient-to-r from-accent to-accent/70 bg-clip-text text-transparent">Hamboo AI Terminal.</span>
        </h2>
        <p className="text-secondary max-w-2xl mx-auto text-lg">Pusat komando investasi cerdasmu. Pantau kondisi pasar, lihat riwayat portofoliomu, dan temukan saham potensial lewat analisa AI.</p>
      </div>

      {/* 3 Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 md:gap-6">
        {/* Market Outlook */}
        <Card className="backdrop-blur-md hover:bg-white/5 transition duration-300">
          <CardContent className="p-6">
            <div className="flex justify-between items-start mb-4">
              <div className={`w-10 h-10 rounded-full flex items-center justify-center ${stats.market_outlook === 'Bullish' ? 'bg-profit/10 text-profit' : stats.market_outlook === 'Bearish' ? 'bg-loss/10 text-loss' : 'bg-secondary/10 text-secondary'}`}>
                {stats.market_outlook === 'Bullish' ? (
                  <ArrowUpIcon className="w-6 h-6" />
                ) : stats.market_outlook === 'Bearish' ? (
                  <ArrowDownIcon className="w-6 h-6" />
                ) : (
                  <TargetIcon className="w-6 h-6" />
                )}
              </div>
              <span className="text-xs font-semibold text-secondary uppercase">Arah Pasar</span>
            </div>
            <h3 className={`text-3xl font-bold font-mono ${stats.market_outlook === 'Bullish' ? 'text-profit' : stats.market_outlook === 'Bearish' ? 'text-loss' : 'text-secondary'}`}>
              {stats.market_outlook}
            </h3>
            <p className="text-sm text-secondary mt-1">Sinyal saham utama</p>
          </CardContent>
        </Card>

        {/* AI Win Rate */}
        <Card className="backdrop-blur-md hover:bg-white/5 transition duration-300">
          <CardContent className="p-6">
            <div className="flex justify-between items-start mb-4">
              <div className="w-10 h-10 rounded-full bg-accent/10 flex items-center justify-center text-accent">
                <TargetIcon className="w-6 h-6" />
              </div>
              <span className="text-xs font-semibold text-secondary uppercase">AI Win Rate</span>
            </div>
            <h3 className="text-3xl font-bold text-text font-mono">{stats.win_rate}%</h3>
            <p className="text-sm text-secondary mt-1">Akurasi historis AI</p>
          </CardContent>
        </Card>

        {/* Profit Factor */}
        <Card className="backdrop-blur-md hover:bg-white/5 transition duration-300">
          <CardContent className="p-6">
            <div className="flex justify-between items-start mb-4">
              <div className="w-10 h-10 rounded-full bg-info/10 flex items-center justify-center text-info">
                <BarChartIcon className="w-6 h-6" />
              </div>
              <span className="text-xs font-semibold text-secondary uppercase">Profit Factor</span>
            </div>
            <h3 className="text-3xl font-bold text-text font-mono">{stats.profit_factor}x</h3>
            <p className="text-sm text-secondary mt-1">Gross profit / Gross loss</p>
          </CardContent>
        </Card>
      </div>

      {/* Onboarding & Conversion Grid */}
      <div className="mt-10 space-y-6">
        <div>
          <h3 className="text-sm font-extrabold text-text tracking-wider uppercase">Panduan & Model Hamboo AI</h3>
          <p className="text-xs text-secondary mt-1">Pelajari workflow pemrosesan sinyal kami dan maksimalkan keuntungan portofolio Anda.</p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
          {/* Card 1: Apa itu Hamboo AI */}
          <div className="bg-card border border-border rounded-3xl p-5 hover:bg-white/[0.03] transition duration-300 flex flex-col justify-between space-y-4">
            <div className="space-y-2">
              <div className="w-10 h-10 rounded-2xl bg-accent/10 flex items-center justify-center text-accent">
                <InfoCircledIcon className="w-5 h-5" />
              </div>
              <h4 className="font-bold text-text text-sm">🤖 Apa itu Hamboo AI?</h4>
              <p className="text-xs text-secondary leading-relaxed">Co-pilot investasi cerdas Anda di Bursa Saham Indonesia (IDX). Hamboo AI memindai, menganalisis, dan memprediksi pergerakan saham secara kuantitatif berdasarkan kalkulasi momentum teknikal dan bandarmologi terintegrasi secara otomatis.</p>
            </div>
          </div>

          {/* Card 2: Workflow Sinyal */}
          <div className="bg-card border border-border rounded-3xl p-5 hover:bg-white/[0.03] transition duration-300 flex flex-col justify-between space-y-4">
            <div className="space-y-2">
              <div className="w-10 h-10 rounded-2xl bg-indigo-500/10 flex items-center justify-center text-indigo-400">
                <LoopIcon className="w-5 h-5" />
              </div>
              <h4 className="font-bold text-text text-sm">🔄 Workflow Sinyal AI</h4>
              <p className="text-xs text-secondary leading-relaxed">Sistem memindai likuiditas pasar → menghitung volume transaksi asing & domestik → mendeteksi akumulasi bandar → memprediksi arah IHSG → merilis rekomendasi beli/jual harian yang presisi.</p>
            </div>
          </div>

          {/* Card 3: AI Performance */}
          <div className="bg-card border border-border rounded-3xl p-5 hover:bg-white/[0.03] transition duration-300 flex flex-col justify-between space-y-4">
            <div className="space-y-3">
              <div className="w-10 h-10 rounded-2xl bg-emerald-500/10 flex items-center justify-center text-emerald-400">
                <RocketIcon className="w-5 h-5" />
              </div>
              <h4 className="font-bold text-text text-sm">📈 AI Performance</h4>
              <p className="text-xs text-secondary leading-relaxed">Seluruh rekomendasi diukur secara transparan terhadap pergerakan pasar. Anda dapat melihat grafik perbandingan performa rekomendasi AI vs IHSG di halaman Performance.</p>
            </div>
            <a href="/performance" className="text-xs text-accent font-bold hover:underline flex items-center gap-1">
              Lihat Histori Performa &rarr;
            </a>
          </div>

          {/* Card 4: Pro Tier Benefits */}
          <div className={`border rounded-3xl p-5 transition duration-300 flex flex-col justify-between space-y-4 ${isPro ? 'border-border bg-card' : 'border-indigo-500/30 bg-gradient-to-br from-indigo-950/20 via-card to-background shadow-[0_0_20px_rgba(99,102,241,0.08)]'}`}>
            <div className="space-y-3">
              <div className="w-10 h-10 rounded-2xl bg-amber-500/10 flex items-center justify-center text-amber-400">
                <StarIcon className="w-5 h-5 fill-amber-400" />
              </div>
              <h4 className="font-bold text-text text-sm flex items-center gap-1.5">
                ✨ Benefit Pro Tier
              </h4>
              <p className="text-xs text-secondary leading-relaxed">Buka sensor target TP/SL Rank #1 & #2, jalankan strategi DCA tanpa batas aktif, dan nikmati fitur investasi instan otomatis dalam 1 kali klik.</p>
            </div>
            {!isPro ? (
              <a href="/billing" className="w-full py-2 bg-indigo-600 hover:bg-accent hover:text-black text-text font-bold rounded-xl text-center text-xs transition shadow-lg shadow-indigo-600/10">
                Upgrade Pro Sekarang
              </a>
            ) : (
              <span className="text-xs text-emerald-400 font-bold flex items-center gap-1">
                <CheckCircledIcon className="w-4 h-4" /> Pro Tier Aktif
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Equity vs IHSG Comparison Chart */}
      <div className="pt-6 border-t border-border">
        <CustomEquityVsIhsgChart points={comparisonPoints} />
      </div>

      {/* Cara Kerja AI Workflow Section */}
      <div className="pt-10 border-t border-border space-y-6">
        <div>
          <h3 className="text-sm font-extrabold text-text tracking-wider uppercase">Cara Kerja Hamboo AI</h3>
          <p className="text-xs text-secondary mt-1">Klik langkah di bawah ini untuk melihat alur kerja di balik layar pembuatan sinyal rekomendasi.</p>
        </div>

        {/* Step Nodes Row */}
        <div className="flex flex-col lg:flex-row items-center justify-between gap-4 p-6 bg-card border border-border rounded-3xl relative overflow-hidden">
          {steps.map((step, idx) => {
            const StepIcon = step.icon;
            const isActive = activeStep === idx;
            return (
              <React.Fragment key={idx}>
                {/* Node */}
                <button
                  onClick={() => setActiveStep(idx)}
                  className={`flex flex-col items-center text-center p-4 rounded-2xl transition duration-300 w-full lg:w-44 z-10 ${isActive ? 'bg-accent/10 border border-accent/35 scale-[1.03] shadow-[0_0_15px_rgba(255,255,255,0.02)]' : 'border border-transparent hover:bg-white/5'}`}
                >
                  <div className={`w-12 h-12 rounded-full flex items-center justify-center mb-2.5 transition-colors ${isActive ? 'bg-accent text-black font-black' : 'bg-white/5 text-secondary'}`}>
                    <StepIcon className="w-5 h-5" />
                  </div>
                  <span className={`text-xs font-bold ${isActive ? 'text-accent' : 'text-secondary'}`}>{step.short}</span>
                </button>

                {/* Connecting Line (Only between nodes, hidden on vertical stack/mobile) */}
                {idx < steps.length - 1 && (
                  <div className="hidden lg:block flex-1 h-0.5 border-t border-dashed border-border relative">
                    <div className={`absolute inset-0 bg-accent transition-all duration-500 origin-left ${activeStep > idx ? 'scale-x-100 opacity-60' : 'scale-x-0 opacity-0'}`} />
                  </div>
                )}
              </React.Fragment>
            );
          })}
        </div>

        {/* Step Details & Terminal Log Panel */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 bg-card border border-border rounded-3xl p-6 relative overflow-hidden">
          {/* Left Details */}
          <div className="space-y-4 flex flex-col justify-center">
            <span className="text-[10px] uppercase font-mono tracking-widest text-accent font-bold">Langkah {activeStep + 1} dari 4</span>
            <h4 className="text-lg font-bold text-text">{steps[activeStep].title}</h4>
            <p className="text-xs text-secondary leading-relaxed">{steps[activeStep].desc}</p>
          </div>

          {/* Right Mock Log Terminal */}
          <div className="bg-black/60 border border-white/5 rounded-2xl p-5 font-mono text-[10px] text-emerald-400 space-y-2 relative shadow-inner h-36 flex flex-col justify-center">
            <div className="absolute top-3 right-4 flex gap-1">
              <span className="w-2 h-2 rounded-full bg-loss/40" />
              <span className="w-2 h-2 rounded-full bg-warning/40" />
              <span className="w-2 h-2 rounded-full bg-profit/40" />
            </div>
            {steps[activeStep].logs.map((log, i) => (
              <p key={i} className="leading-5">{log}</p>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
