"use client";
import React, { useState, useEffect } from 'react';
import { useApp } from '../context/AppContext';

export default function DashboardPage() {
  const { stats, wallet, holdings, loading } = useApp();
  const [username, setUsername] = useState("");

  useEffect(() => {
    try {
      // Decode JWT token to get username
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

  return (
    <div className="space-y-10 animate-fade-in">
      {/* Hero Section */}
      <div className="text-center space-y-4 py-8">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-accent/10 border border-[#7C3AED]/20 text-accent text-xs font-semibold uppercase tracking-widest mb-4">
          <span className="w-1.5 h-1.5 rounded-full bg-indigo-400 animate-pulse"></span>
          AI Model is Active
        </div>
        <h2 className="text-4xl md:text-5xl font-bold tracking-tight text-text">
          Selamat Datang, {username || "Trader"}! <br />
          <span className="bg-gradient-to-r from-indigo-400 to-purple-400 bg-clip-text text-transparent">Hamboo AI Terminal.</span>
        </h2>
        <p className="text-secondary max-w-2xl mx-auto text-lg">Pusat komando investasi cerdasmu. Pantau kondisi pasar, lihat riwayat portofoliomu, dan temukan saham potensial lewat analisa AI.</p>
      </div>

      {/* 3 Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="bg-card backdrop-blur-md border border-border rounded-2xl p-6 hover:bg-white/5 transition duration-300">
          <div className="flex justify-between items-start mb-4">
            <div className={`w-10 h-10 rounded-full flex items-center justify-center font-bold ${stats.market_outlook === 'Bullish' ? 'bg-[#22C55E]/10 text-[#22C55E]' : stats.market_outlook === 'Bearish' ? 'bg-loss/10 text-loss' : 'bg-slate-500/10 text-secondary'}`}>
              {stats.market_outlook === 'Bullish' ? '↗' : stats.market_outlook === 'Bearish' ? '↘' : '→'}
            </div>
            <span className="text-xs font-semibold text-secondary uppercase">Arah Pasar</span>
          </div>
          <h3 className={`text-3xl font-bold ${stats.market_outlook === 'Bullish' ? 'text-[#22C55E]' : stats.market_outlook === 'Bearish' ? 'text-loss' : 'text-secondary'}`}>
            {stats.market_outlook}
          </h3>
          <p className="text-sm text-secondary mt-1">Sinyal saham utama</p>
        </div>

        <div className="bg-card backdrop-blur-md border border-border rounded-2xl p-6 hover:bg-white/5 transition duration-300">
          <div className="flex justify-between items-start mb-4">
            <div className="w-10 h-10 rounded-full bg-purple-500/10 flex items-center justify-center text-purple-400 font-bold">◎</div>
            <span className="text-xs font-semibold text-secondary uppercase">AI Win Rate</span>
          </div>
          <h3 className="text-3xl font-bold text-text">{stats.win_rate}%</h3>
          <p className="text-sm text-secondary mt-1">Akurasi historis portfolio</p>
        </div>

        <div className="bg-card backdrop-blur-md border border-border rounded-2xl p-6 hover:bg-white/5 transition duration-300">
          <div className="flex justify-between items-start mb-4">
            <div className="w-10 h-10 rounded-full bg-[#3B82F6]/10 flex items-center justify-center text-[#3B82F6] font-bold">⚖</div>
            <span className="text-xs font-semibold text-secondary uppercase">Profit Factor</span>
          </div>
          <h3 className="text-3xl font-bold text-text">{stats.profit_factor}x</h3>
          <p className="text-sm text-secondary mt-1">Gross profit / Gross loss</p>
        </div>
      </div>
    </div>
  );
}
