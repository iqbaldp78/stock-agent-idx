"use client";
import React, { useState, useEffect } from 'react';
import { useApp } from '../../context/AppContext';

export default function HistoryPage() {
  const { historyData } = useApp();

  return (
    <div className="space-y-6 animate-fade-in">
      <div>
        <h2 className="text-3xl font-bold text-white mb-2">Track Record <span className="text-indigo-400">AI Sinyal</span></h2>
        <p className="text-slate-400">Laporan transparan performa historis agen AI Hamboo pada seluruh transaksi.</p>
      </div>

      <div className="bg-white/[0.03] backdrop-blur-md border border-white/5 rounded-3xl p-6">
        <div className="overflow-x-auto">
          <table className="w-full text-sm text-left text-slate-300">
            <thead className="text-xs text-slate-400 uppercase bg-white/5 border-b border-white/5">
              <tr>
                <th className="px-4 py-4 rounded-tl-lg">Tanggal</th>
                <th className="px-4 py-4">Saham</th>
                <th className="px-4 py-4">Sinyal Awal</th>
                <th className="px-4 py-4 text-center">Status</th>
                <th className="px-4 py-4 text-right rounded-tr-lg">Profit / Loss (%)</th>
              </tr>
            </thead>
            <tbody>
              {historyData.map((h, i) => (
                <tr key={i} className="border-b border-white/5 hover:bg-white/5 transition duration-150">
                  <td className="px-4 py-4">{h.date}</td>
                  <td className="px-4 py-4 font-bold text-white text-lg">{h.ticker}</td>
                  <td className="px-4 py-4">
                    <span className={`px-3 py-1 rounded-full text-xs font-bold border ${h.signal === 'BUY' ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' : h.signal === 'SELL' ? 'bg-red-500/10 text-red-400 border-red-500/20' : 'bg-slate-500/10 text-slate-400 border-slate-500/20'}`}>
                      {h.signal}
                    </span>
                  </td>
                  <td className="px-4 py-4 text-center">
                    <span className={`px-3 py-1 rounded-lg text-xs font-bold ${h.result === 'PROFIT' ? 'bg-emerald-500 text-white shadow-[0_0_10px_rgba(16,185,129,0.3)]' : h.result === 'LOSS' ? 'bg-red-500 text-white shadow-[0_0_10px_rgba(239,68,68,0.3)]' : 'bg-slate-700 text-slate-300'}`}>
                      {h.result}
                    </span>
                  </td>
                  <td className={`px-4 py-4 text-right font-mono font-bold text-lg ${h.return_pct > 0 ? 'text-emerald-400' : h.return_pct < 0 ? 'text-red-400' : 'text-slate-400'}`}>
                    {h.return_pct > 0 ? '+' : ''}{h.return_pct}%
                  </td>
                </tr>
              ))}
              {historyData.length === 0 && (
                <tr><td colSpan={5} className="px-4 py-10 text-center text-slate-500">Belum ada riwayat trading yang tercatat.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
