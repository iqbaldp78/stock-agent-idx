"use client";
import React, { useState, useEffect } from 'react';
import { useApp } from '../../context/AppContext';

export default function AIPerformancePage() {
  const { isPro, logout, currentUser } = useApp();
  const [metrics, setMetrics] = useState<any>(null);
  const [ihsg, setIhsg] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

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

        const data = await res.json();
        setMetrics(data.metrics);
        setIhsg(data.ihsg_predictor);
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

  return (
    <div className="space-y-6 animate-fade-in">
      <div>
        <h2 className="text-3xl font-bold text-text mb-2">AI Performance <span className="text-accent">Dashboard</span></h2>
        <p className="text-secondary">Mengukur seberapa pintar Agen AI dalam mengelola risiko dan mencetak profit.</p>
      </div>

      {/* Hero Metrics */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-card backdrop-blur-md border border-border rounded-2xl p-5 shadow-lg">
          <p className="text-sm text-secondary mb-1">Total PnL (Cum. Return)</p>
          <h3 className={`text-2xl font-bold ${metrics.cumulative_pnl >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
            Rp {metrics.cumulative_pnl.toLocaleString('id-ID')}
          </h3>
        </div>
        <div className="bg-card backdrop-blur-md border border-border rounded-2xl p-5 shadow-lg">
          <p className="text-sm text-secondary mb-1">Win Rate</p>
          <h3 className="text-2xl font-bold text-text">
            {metrics.win_rate}% <span className="text-sm font-normal text-gray-500">({metrics.total_trades} trades)</span>
          </h3>
        </div>
        <div className="bg-card backdrop-blur-md border border-border rounded-2xl p-5 shadow-lg relative group">
          <p className="text-sm text-secondary mb-1 flex items-center gap-1">
            Profit Factor 
            <span className="text-xs bg-white/10 rounded-full w-4 h-4 flex items-center justify-center cursor-help">?</span>
          </p>
          <h3 className="text-2xl font-bold text-amber-400">{metrics.profit_factor}x</h3>
          <div className="absolute opacity-0 group-hover:opacity-100 transition-opacity bg-black border border-gray-700 text-xs p-2 rounded -top-10 left-0 w-48 pointer-events-none z-10">
            Gross Profit / Gross Loss. &gt; 1.0 berarti AI menghasilkan cuan.
          </div>
        </div>
        <div className="bg-card backdrop-blur-md border border-border rounded-2xl p-5 shadow-lg">
          <p className="text-sm text-secondary mb-1">Sharpe Ratio</p>
          <h3 className="text-2xl font-bold text-accent">{metrics.sharpe_ratio}</h3>
        </div>
      </div>

      {/* IHSG Predictor Section */}
      {ihsg && (
        <div className="bg-card backdrop-blur-md border border-border rounded-3xl p-6 shadow-lg mt-8">
          <div className="flex flex-col md:flex-row justify-between items-start md:items-center mb-6">
            <div>
              <h3 className="text-xl font-bold text-text">IHSG Predictor <span className="text-xs bg-accent/20 text-accent px-2 py-1 rounded ml-2">v2</span></h3>
              <p className="text-sm text-secondary">Prediksi Harian: {ihsg.date}</p>
            </div>
            <div className={`px-4 py-2 rounded-xl mt-4 md:mt-0 font-bold border ${ihsg.direction === 'BULLISH' ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400' : ihsg.direction === 'BEARISH' ? 'bg-red-500/10 border-red-500/30 text-red-400' : 'bg-amber-500/10 border-amber-500/30 text-amber-400'}`}>
              {ihsg.direction} (Confidence: {ihsg.confidence})
            </div>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="md:col-span-2 space-y-4">
              <div className="bg-black/30 rounded-xl p-4 border border-white/5">
                <h4 className="text-sm font-semibold text-gray-400 mb-2">🧠 AI Persona Reasoning</h4>
                <p className="text-sm text-gray-300 leading-relaxed">{ihsg.reasoning}</p>
              </div>
            </div>
            
            <div className="space-y-3">
              <h4 className="text-sm font-semibold text-gray-400 mb-2">📊 Signal Strength (Weights)</h4>
              
              <div className="space-y-2">
                <div className="flex justify-between text-xs mb-1">
                  <span className="text-gray-300">Market Breadth (60%)</span>
                  <span className="text-accent font-bold">{(ihsg.scores.breadth || 0).toFixed(2)}</span>
                </div>
                <div className="w-full bg-gray-800 rounded-full h-1.5">
                  <div className="bg-accent h-1.5 rounded-full" style={{ width: `${(ihsg.scores.breadth || 0) * 100}%` }}></div>
                </div>
              </div>
              
              <div className="space-y-2">
                <div className="flex justify-between text-xs mb-1">
                  <span className="text-gray-300">Momentum (25%)</span>
                  <span className="text-amber-400 font-bold">{(ihsg.scores.momentum || 0).toFixed(2)}</span>
                </div>
                <div className="w-full bg-gray-800 rounded-full h-1.5">
                  <div className="bg-amber-400 h-1.5 rounded-full" style={{ width: `${(ihsg.scores.momentum || 0) * 100}%` }}></div>
                </div>
              </div>

              <div className="space-y-2">
                <div className="flex justify-between text-xs mb-1">
                  <span className="text-gray-300">Macro/News (15%)</span>
                  <span className="text-emerald-400 font-bold">{(ihsg.scores.macro || 0).toFixed(2)}</span>
                </div>
                <div className="w-full bg-gray-800 rounded-full h-1.5">
                  <div className="bg-emerald-400 h-1.5 rounded-full" style={{ width: `${(ihsg.scores.macro || 0) * 100}%` }}></div>
                </div>
              </div>

            </div>
          </div>
        </div>
      )}

      {/* Placeholder for Equity Curve Chart */}
      <div className="bg-card backdrop-blur-md border border-border rounded-3xl p-6 shadow-lg mt-8 opacity-50">
        <h3 className="text-xl font-bold text-text mb-2">Equity Curve (Coming Soon)</h3>
        <p className="text-sm text-secondary mb-6">Visualisasi pertumbuhan portofolio vs IHSG Benchmark sedang dalam pengembangan.</p>
        <div className="h-48 border border-dashed border-gray-700 rounded-xl flex items-center justify-center text-gray-500">
          Chart Area
        </div>
      </div>
    </div>
  );
}
