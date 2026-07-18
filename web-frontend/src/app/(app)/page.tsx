"use client";
import React, { useState, useEffect } from 'react';
import { useApp } from '../context/AppContext';
import { Card, CardContent } from '@/components/ui/card';
import { ArrowUpIcon, ArrowDownIcon, TargetIcon, BarChartIcon } from '@radix-ui/react-icons';

export default function DashboardPage() {
  const { stats, wallet, holdings, loading } = useApp();
  const [username, setUsername] = useState("");

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

  return (
    <div className="animate-fade-in">
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
            <p className="text-sm text-secondary mt-1">Akurasi historis portfolio</p>
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
    </div>
  );
}
