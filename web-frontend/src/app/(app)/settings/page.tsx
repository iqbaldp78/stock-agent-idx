"use client";
import React, { useState } from 'react';
import { useApp } from '../../context/AppContext';

export default function SettingsPage() {
  const { isPro, setIsPro } = useApp();

  return (
    <div className="space-y-8 animate-fade-in">
      <div>
        <h2 className="text-3xl font-bold text-text mb-2">⚙️ <span className="text-accent">Preferences</span></h2>
        <p className="text-secondary">Pengaturan akun, tampilan, dan konfigurasi agen AI.</p>
      </div>

      <div className="bg-card backdrop-blur-md border border-border rounded-3xl p-8 space-y-6">
        <div className="space-y-4">
          <h4 className="text-lg font-bold text-text border-b border-border pb-2">Informasi Akun</h4>
          <div className="flex justify-between items-center p-2">
            <div>
              <p className="font-bold text-text">Status Tier</p>
              <p className="text-sm text-secondary">Mode saat ini yang sedang aktif</p>
            </div>
            <div className="flex bg-background p-1 rounded-xl border border-border">
              <button
                className={`px-4 py-2 rounded-lg transition text-sm font-bold ${!isPro ? 'bg-accent text-text shadow-lg' : 'text-secondary hover:text-text'}`}
                onClick={() => setIsPro(false)}
              >Free Tier</button>
              <button
                className={`px-4 py-2 rounded-lg transition text-sm font-bold flex items-center gap-2 ${isPro ? 'bg-accent text-text shadow-lg' : 'text-secondary hover:text-text'}`}
                onClick={() => setIsPro(localStorage?.getItem("tier") === "pro")}
              >Pro Tier ✨</button>
            </div>
          </div>
        </div>

        <div className="space-y-4">
          <h4 className="text-lg font-bold text-text border-b border-border pb-2">Konfigurasi Agen AI</h4>
          <div className="space-y-3">
            <div className="flex justify-between items-center p-2">
              <p className="text-secondary">Model Prediksi Analisa</p>
              <span className="px-3 py-1 bg-white/10 rounded-lg text-xs font-mono text-accent">OpenRouter (Debate)</span>
            </div>
            <div className="flex justify-between items-center p-2">
              <p className="text-secondary">Agresivitas Trading</p>
              <span className="px-3 py-1 bg-white/10 rounded-lg text-xs font-mono text-accent">MODERATE (Defensive)</span>
            </div>
            <div className="flex justify-between items-center p-2">
              <p className="text-secondary">Notifikasi WhatsApp</p>
              <button className="w-12 h-6 bg-profit rounded-full relative transition">
                <span className="absolute right-1 top-1 w-4 h-4 bg-white rounded-full"></span>
              </button>
            </div>
          </div>
        </div>

        <div className="pt-4 border-t border-border flex justify-end">
          <button className="bg-white hover:bg-slate-200 text-black font-bold py-2 px-6 rounded-xl transition shadow-[0_0_15px_rgba(255,255,255,0.2)]">
            Simpan Perubahan
          </button>
        </div>
      </div>

      {/* Danger Zone */}
      <div className="bg-loss/5 border border-loss/10 rounded-3xl p-6">
        <h4 className="text-lg font-bold text-loss mb-2">🚪 Sign Out</h4>
        <p className="text-sm text-secondary mb-4">Keluar dari akun Hamboo.ai Anda.</p>
        <button
          onClick={() => {
            localStorage.removeItem("token");
            localStorage.removeItem("tier");
            window.location.href = "/login";
          }}
          className="bg-loss hover:bg-red-700 text-text font-bold py-2.5 px-6 rounded-xl text-sm transition"
        >
          Sign Out
        </button>
      </div>
    </div>
  );
}
