"use client";
import React, { useState } from 'react';
import { useApp } from '../../context/AppContext';

export default function SettingsPage() {
  const { isPro, setIsPro } = useApp();

  return (
    <div className="space-y-8 animate-fade-in">
      <div>
        <h2 className="text-3xl font-bold text-white mb-2">⚙️ <span className="text-indigo-400">Preferences</span></h2>
        <p className="text-slate-400">Pengaturan akun, tampilan, dan konfigurasi agen AI.</p>
      </div>

      <div className="bg-white/[0.03] backdrop-blur-md border border-white/5 rounded-3xl p-8 space-y-6">
        <div className="space-y-4">
          <h4 className="text-lg font-bold text-white border-b border-white/10 pb-2">Informasi Akun</h4>
          <div className="flex justify-between items-center p-2">
            <div>
              <p className="font-bold text-white">Status Tier</p>
              <p className="text-sm text-slate-400">Mode saat ini yang sedang aktif</p>
            </div>
            <div className="flex bg-[#030712] p-1 rounded-xl border border-white/10">
              <button
                className={`px-4 py-2 rounded-lg transition text-sm font-bold ${!isPro ? 'bg-indigo-500 text-white shadow-lg' : 'text-slate-400 hover:text-white'}`}
                onClick={() => setIsPro(false)}
              >Free Tier</button>
              <button
                className={`px-4 py-2 rounded-lg transition text-sm font-bold flex items-center gap-2 ${isPro ? 'bg-gradient-to-r from-indigo-500 to-purple-500 text-white shadow-lg' : 'text-slate-400 hover:text-white'}`}
                onClick={() => setIsPro(localStorage?.getItem("tier") === "pro")}
              >Pro Tier ✨</button>
            </div>
          </div>
        </div>

        <div className="space-y-4">
          <h4 className="text-lg font-bold text-white border-b border-white/10 pb-2">Konfigurasi Agen AI</h4>
          <div className="space-y-3">
            <div className="flex justify-between items-center p-2">
              <p className="text-slate-300">Model Prediksi Analisa</p>
              <span className="px-3 py-1 bg-white/10 rounded-lg text-xs font-mono text-indigo-300">OpenRouter (Debate)</span>
            </div>
            <div className="flex justify-between items-center p-2">
              <p className="text-slate-300">Agresivitas Trading</p>
              <span className="px-3 py-1 bg-white/10 rounded-lg text-xs font-mono text-indigo-300">MODERATE (Defensive)</span>
            </div>
            <div className="flex justify-between items-center p-2">
              <p className="text-slate-300">Notifikasi WhatsApp</p>
              <button className="w-12 h-6 bg-emerald-500 rounded-full relative transition">
                <span className="absolute right-1 top-1 w-4 h-4 bg-white rounded-full"></span>
              </button>
            </div>
          </div>
        </div>

        <div className="pt-4 border-t border-white/10 flex justify-end">
          <button className="bg-white hover:bg-slate-200 text-black font-bold py-2 px-6 rounded-xl transition shadow-[0_0_15px_rgba(255,255,255,0.2)]">
            Simpan Perubahan
          </button>
        </div>
      </div>

      {/* Danger Zone */}
      <div className="bg-red-500/5 border border-red-500/10 rounded-3xl p-6">
        <h4 className="text-lg font-bold text-red-400 mb-2">🚪 Sign Out</h4>
        <p className="text-sm text-slate-400 mb-4">Keluar dari akun Hamboo.ai Anda.</p>
        <button
          onClick={() => {
            localStorage.removeItem("token");
            localStorage.removeItem("tier");
            window.location.href = "/login";
          }}
          className="bg-red-600 hover:bg-red-700 text-white font-bold py-2.5 px-6 rounded-xl text-sm transition"
        >
          Sign Out
        </button>
      </div>
    </div>
  );
}
