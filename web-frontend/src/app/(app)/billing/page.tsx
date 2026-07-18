"use client";
import React, { useState, useEffect } from 'react';
import { useApp } from '../../context/AppContext';
import {
  CheckCircledIcon,
  CrossCircledIcon,
  IdCardIcon,
  StarIcon,
  ShadowIcon,
  InfoCircledIcon
} from '@radix-ui/react-icons';

export default function BillingUpgradePage() {
  const { isPro, setIsPro, showToast } = useApp();
  const [loading, setLoading] = useState(false);
  const [showPaymentDetails, setShowPaymentDetails] = useState(false);
  const [selectedMethod, setSelectedMethod] = useState<'qris' | 'va'>('qris');
  const [currentTier, setCurrentTier] = useState<string>('free');

  useEffect(() => {
    async function checkCurrentTier() {
      try {
        const token = localStorage.getItem('token');
        if (!token) return;
        const res = await fetch('/api/auth/me', {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        });
        if (res.ok) {
          const data = await res.json();
          setCurrentTier(data.tier || 'free');
          setIsPro(data.tier === 'pro');
          localStorage.setItem('tier', data.tier || 'free');
        }
      } catch (err) {
        console.error("Gagal sinkronisasi tier:", err);
      }
    }
    checkCurrentTier();
  }, [isPro, setIsPro]);

  const handleUpgrade = async () => {
    setLoading(true);
    try {
      const token = localStorage.getItem('token');
      const res = await fetch('/api/user/upgrade', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      if (res.ok) {
        setIsPro(true);
        setCurrentTier('pro');
        localStorage.setItem('tier', 'pro');
        showToast("Pembayaran berhasil diverifikasi! Tier Anda kini PRO ✨", "success");
        setShowPaymentDetails(false);
      } else {
        showToast("Gagal memverifikasi pembayaran", "error");
      }
    } catch (err) {
      showToast("Kesalahan jaringan", "error");
    } finally {
      setLoading(false);
    }
  };

  const handleDowngrade = async () => {
    setLoading(true);
    try {
      const token = localStorage.getItem('token');
      const res = await fetch('/api/user/downgrade', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      if (res.ok) {
        setIsPro(false);
        setCurrentTier('free');
        localStorage.setItem('tier', 'free');
        showToast("Tier diturunkan ke FREE untuk keperluan pengujian", "info");
      } else {
        showToast("Gagal mengubah tier", "error");
      }
    } catch (err) {
      showToast("Kesalahan jaringan", "error");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-8 animate-fade-in">
      <div className="space-y-3">
        <div className="inline-flex items-center gap-2 rounded-full border border-accent/20 bg-accent/10 px-3 py-1 text-xs font-bold uppercase tracking-[0.2em] text-accent">
          Billing & Subscription Plan
        </div>
        <div>
          <h2 className="text-3xl font-bold text-text mb-2">Upgrade to <span className="text-accent">Pro Tier</span></h2>
          <p className="max-w-3xl text-secondary">Akses penuh ke seluruh sinyal dan hilangkan batasan strategi DCA untuk maksimalkan profit simulasi Anda.</p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
        <div className={`relative rounded-3xl border p-6 bg-card transition duration-300 flex flex-col justify-between ${currentTier === 'free' ? 'border-accent shadow-[0_0_20px_rgba(255,255,255,0.05)]' : 'border-border'}`}>
          {currentTier === 'free' && (
            <span className="absolute -top-3 left-6 px-3 py-1 bg-accent text-black font-extrabold text-[10px] uppercase rounded-full tracking-wider">
              Aktif Saat Ini
            </span>
          )}
          <div>
            <h3 className="text-xl font-extrabold text-text">Free Tier</h3>
            <p className="text-xs text-secondary mt-1">Paket dasar untuk mencoba platform</p>
            <div className="my-6">
              <span className="text-3xl font-black text-text">Rp 0</span>
              <span className="text-xs text-secondary">/ selamanya</span>
            </div>
            <ul className="space-y-3 text-xs text-secondary border-t border-border pt-6">
              <li className="flex items-center gap-2 text-text">
                <CheckCircledIcon className="text-profit w-4 h-4" />
                <span>Melihat list Top Picks & IHSG Predictor</span>
              </li>
              <li className="flex items-center gap-2 text-text">
                <CheckCircledIcon className="text-profit w-4 h-4" />
                <span>Simulasi manual order di Trading Engine</span>
              </li>
              <li className="flex items-center gap-2">
                <CrossCircledIcon className="text-loss w-4 h-4" />
                <span>Terbatas maksimal 1 strategi DCA aktif</span>
              </li>
              <li className="flex items-center gap-2">
                <CrossCircledIcon className="text-loss w-4 h-4" />
                <span>Target TP/SL & Entry Range disensor (🔒 Upgrade Pro)</span>
              </li>
              <li className="flex items-center gap-2">
                <CrossCircledIcon className="text-loss w-4 h-4" />
                <span>Aksi simulasi langsung dari sinyal dinonaktifkan</span>
              </li>
            </ul>
          </div>
          {currentTier === 'pro' && (
            <button onClick={handleDowngrade} disabled={loading} className="mt-8 w-full py-3 border border-loss/20 hover:bg-loss/10 text-loss font-bold rounded-xl transition text-sm flex items-center justify-center gap-2">
              Turunkan ke Free (Pengujian)
            </button>
          )}
        </div>

        <div className={`relative rounded-3xl border p-6 bg-gradient-to-br from-indigo-950/20 via-card to-background transition duration-300 flex flex-col justify-between ${currentTier === 'pro' ? 'border-accent shadow-[0_0_20px_rgba(255,255,255,0.08)]' : 'border-indigo-500/30'}`}>
          {currentTier === 'pro' && (
            <span className="absolute -top-3 left-6 px-3 py-1 bg-gradient-to-r from-amber-400 to-amber-500 text-black font-extrabold text-[10px] uppercase rounded-full tracking-wider flex items-center gap-1">
              <StarIcon className="w-3 h-3 fill-black" /> Pro Aktif
            </span>
          )}
          <div>
            <h3 className="text-xl font-extrabold text-text flex items-center gap-2">Pro Tier <StarIcon className="text-amber-400 fill-amber-400 w-4 h-4" /></h3>
            <p className="text-xs text-secondary mt-1">Solusi komprehensif untuk pengujian intensif</p>
            <div className="my-6">
              <span className="text-3xl font-black text-text">Rp 149.000</span>
              <span className="text-xs text-secondary">/ bulan</span>
            </div>
            <ul className="space-y-3 text-xs text-text border-t border-border pt-6">
              <li className="flex items-center gap-2">
                <CheckCircledIcon className="text-profit w-4 h-4" />
                <span>Unlimited DCA Strategies aktif secara bersamaan</span>
              </li>
              <li className="flex items-center gap-2">
                <CheckCircledIcon className="text-profit w-4 h-4" />
                <span>Buka sensor target TP, SL, dan Entry Range</span>
              </li>
              <li className="flex items-center gap-2">
                <CheckCircledIcon className="text-profit w-4 h-4" />
                <span>Aktifkan simulasi beli instan langsung dari halaman sinyal</span>
              </li>
              <li className="flex items-center gap-2">
                <CheckCircledIcon className="text-profit w-4 h-4" />
                <span>Akses prioritas IHSG Predictor harian</span>
              </li>
            </ul>
          </div>
          {currentTier === 'free' && !showPaymentDetails && (
            <button onClick={() => setShowPaymentDetails(true)} className="mt-8 w-full py-3 bg-indigo-600 hover:bg-accent hover:text-black text-text font-bold rounded-xl transition text-sm shadow-lg shadow-indigo-600/20">
              Upgrade Sekarang
            </button>
          )}
        </div>
      </div>

      {showPaymentDetails && currentTier === 'free' && (
        <div className="rounded-3xl border border-border bg-card p-6 shadow-xl space-y-6 max-w-2xl mx-auto">
          <div className="flex justify-between items-center border-b border-border pb-4">
            <h3 className="text-lg font-bold text-text flex items-center gap-2">
              <IdCardIcon className="w-5 h-5 text-accent" />
              <span>Simulasi Pembayaran Pro Plan</span>
            </h3>
            <button onClick={() => setShowPaymentDetails(false)} className="text-xs text-secondary hover:text-text">Batal</button>
          </div>

          <div className="flex gap-2">
            <button
              onClick={() => setSelectedMethod('qris')}
              className={`flex-1 py-2 text-xs font-bold rounded-xl border transition ${selectedMethod === 'qris' ? 'bg-accent/10 border-accent text-accent' : 'bg-white/5 border-border text-secondary'}`}
            >
              QRIS (Gopay/OVO/Dana)
            </button>
            <button
              onClick={() => setSelectedMethod('va')}
              className={`flex-1 py-2 text-xs font-bold rounded-xl border transition ${selectedMethod === 'va' ? 'bg-accent/10 border-accent text-accent' : 'bg-white/5 border-border text-secondary'}`}
            >
              Virtual Account Bank
            </button>
          </div>

          <div className="bg-black/30 border border-white/5 rounded-2xl p-5 flex flex-col items-center justify-center space-y-4">
            {selectedMethod === 'qris' ? (
              <>
                <div className="w-40 h-40 bg-white p-2 rounded-xl flex items-center justify-center relative">
                  <div className="w-full h-full bg-slate-900 rounded flex flex-col items-center justify-center text-[10px] text-accent font-black tracking-widest font-mono p-4 text-center">
                    QRIS PRO PLAN
                    <div className="w-16 h-16 border-4 border-dashed border-accent mt-2 flex items-center justify-center">
                      <StarIcon className="w-6 h-6 animate-spin text-accent" />
                    </div>
                  </div>
                </div>
                <div className="text-center">
                  <p className="text-sm font-bold text-text">Scan kode QR di atas</p>
                  <p className="text-xs text-secondary mt-1">Gunakan aplikasi e-wallet Anda untuk memindai pembayaran simulasi Rp 149.000.</p>
                </div>
              </>
            ) : (
              <div className="w-full space-y-3 font-mono">
                <div className="flex justify-between text-xs text-secondary">
                  <span>BANK TUJUAN:</span>
                  <span className="text-text font-bold">BANK MANDIRI</span>
                </div>
                <div className="flex justify-between text-xs text-secondary">
                  <span>NOMOR VIRTUAL ACCOUNT:</span>
                  <span className="text-text font-bold tracking-wider text-sm select-all">8989 1234 5678 9012</span>
                </div>
                <div className="flex justify-between text-xs text-secondary">
                  <span>ATAS NAMA:</span>
                  <span className="text-text font-bold">HAMBOO STOCK AGENT</span>
                </div>
                <div className="flex justify-between text-xs text-secondary">
                  <span>NOMINAL TRANSFER:</span>
                  <span className="text-accent font-bold">Rp 149.000</span>
                </div>
              </div>
            )}
          </div>

          <div className="bg-white/5 border border-border rounded-2xl p-4 flex gap-3 text-xs text-secondary">
            <InfoCircledIcon className="w-6 h-6 text-accent flex-shrink-0" />
            <p className="leading-relaxed">Ini adalah gateway pembayaran simulasi. Klik tombol konfirmasi di bawah untuk mensimulasikan persetujuan pembayaran real-time dari bank/mitra kami.</p>
          </div>

          <button
            onClick={handleUpgrade}
            disabled={loading}
            className="w-full py-3.5 bg-accent text-black font-extrabold rounded-xl transition text-sm shadow-lg shadow-accent/20 flex items-center justify-center gap-2 hover:scale-[1.01]"
          >
            {loading ? 'Memverifikasi...' : 'Konfirmasi Pembayaran (Simulate Upgrade)'}
          </button>
        </div>
      )}
    </div>
  );
}
