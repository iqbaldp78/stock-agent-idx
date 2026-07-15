"use client";
import React, { useState } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useApp } from '../context/AppContext';

const navItems = [
  { href: "/", label: "Home Dashboard", icon: "🏠", id: "dashboard" },
  { href: "/top-picks", label: "AI Top Picks", icon: "🎯", id: "top-picks" },
  { href: "/trading", label: "Trading Engine", icon: "💹", id: "trading" },
  { href: "/bandarmologi", label: "Bandarmologi", icon: "🏛️", id: "bandarmologi" },
  { href: "/ihsg", label: "IHSG Predictor", icon: "📈", id: "ihsg" },
  { href: "/history", label: "AI Performance", icon: "📊", id: "history" },
  { href: "/portfolio", label: "Portfolio Management", icon: "💼", id: "portfolio" },
  { href: "/settings", label: "Preferences", icon: "⚙️", id: "settings" },
];

export default function AppShellLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const { wallet, toasts, dismissToast, isPro, setIsPro, logout, currentUser } = useApp();
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const isActive = (href: string) => {
    if (href === "/") return pathname === "/";
    return pathname.startsWith(href);
  };

  return (
    <div className="min-h-screen bg-background text-text font-sans relative overflow-x-hidden overflow-y-auto w-full h-full pb-20">
      {/* Background Orbs */}
      <div className="fixed top-[-10%] left-[-10%] w-[50vw] h-[50vw] rounded-full bg-[radial-gradient(circle,rgba(99,102,241,0.15)_0%,rgba(0,0,0,0)_70%)] z-0 pointer-events-none"></div>
      <div className="fixed bottom-[-10%] right-[-10%] w-[60vw] h-[60vw] rounded-full bg-[radial-gradient(circle,rgba(168,85,247,0.15)_0%,rgba(0,0,0,0)_70%)] z-0 pointer-events-none"></div>

      {/* Sidebar Overlay */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-black/60 backdrop-blur-sm z-[60] transition-opacity"
          onClick={() => setSidebarOpen(false)}
        ></div>
      )}

      {/* Sidebar */}
      <aside className={`fixed top-0 left-0 h-full w-64 bg-background/95 backdrop-blur-2xl border-r border-border z-[70] transform transition-transform duration-300 ease-in-out ${sidebarOpen ? 'translate-x-0' : '-translate-x-full'}`}>
        <div className="p-6 flex flex-col h-full">
          <div className="flex items-center justify-between mb-10">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-full bg-accent flex items-center justify-center shadow-lg shadow-accent/20 text-text font-bold text-sm">
                H
              </div>
              <h1 className="font-bold text-xl tracking-wide">
                Hamboo<span className="text-accent">.ai</span>
              </h1>
            </div>
            <button onClick={() => setSidebarOpen(false)} className="text-secondary hover:text-text transition">
              ✕
            </button>
          </div>

          <nav className="space-y-2">
            {navItems.map((item) => (
              <Link
                key={item.id}
                href={item.href}
                onClick={() => setSidebarOpen(false)}
                className={`w-full flex items-center gap-4 px-4 py-3 rounded-xl font-medium transition ${
                  isActive(item.href)
                    ? 'bg-white/10 text-text border border-border shadow-[0_0_15px_rgba(255,255,255,0.05)]'
                    : 'text-secondary hover:text-text hover:bg-white/5'
                }`}
              >
                <span className="text-lg">{item.icon}</span> {item.label}
              </Link>
            ))}
            <a href="https://admin.hamboo.me" target="_blank" className="flex items-center gap-4 px-4 py-3 text-secondary hover:text-text hover:bg-white/5 rounded-xl transition font-medium">
              <span className="text-lg">👨‍💻</span> Admin Panel
            </a>
          </nav>

          <div className="mt-auto pt-6 border-t border-border">
            <div className="bg-accent/10 border border-accent/20 rounded-xl p-4 mb-4">
              <p className="text-xs text-accent font-bold mb-1">PRO ACCOUNT AKTIF</p>
              <p className="text-[10px] text-secondary">Akses sinyal unlimited dan AI reasoning detail menyala.</p>
            </div>
            <button
              onClick={() => {
                localStorage.removeItem("token");
                localStorage.removeItem("tier");
                window.location.href = "/login";
              }}
              className="flex items-center gap-4 px-4 py-3 text-loss hover:text-red-300 hover:bg-loss/10 rounded-xl transition font-medium w-full"
            >
              <span>🚪</span> Sign Out
            </button>
          </div>
        </div>
      </aside>

      {/* Navbar */}
      <nav className="sticky top-0 z-50 bg-background/70 backdrop-blur-xl border-b border-border">
        <div className="max-w-5xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <button onClick={() => setSidebarOpen(true)} className="mr-2 p-2 rounded-lg text-secondary hover:text-text hover:bg-white/10 transition">
              <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="3" y1="12" x2="21" y2="12"></line><line x1="3" y1="6" x2="21" y2="6"></line><line x1="3" y1="18" x2="21" y2="18"></line></svg>
            </button>
            <div className="w-8 h-8 rounded-full bg-accent flex items-center justify-center shadow-lg shadow-accent/20 text-text font-bold text-sm">
              H
            </div>
            <h1 className="font-bold text-xl tracking-wide">
              Hamboo<span className="text-accent">.ai</span>
            </h1>
          </div>

          <div className="flex items-center gap-4 text-sm font-medium">
            <div className="bg-background p-1 rounded-full border border-border flex text-xs">
              <button
                className={`px-4 py-1.5 rounded-full transition ${isPro ? 'text-secondary hover:text-text' : 'bg-accent text-text shadow-lg shadow-indigo-500/20'}`}
                onClick={() => setIsPro(false)}
              >Free</button>
              <button
                className={`px-4 py-1.5 rounded-full transition flex items-center gap-1 ${isPro ? 'bg-accent text-text shadow-lg shadow-accent/20' : 'text-secondary hover:text-text'}`}
                onClick={() => setIsPro(localStorage?.getItem("tier") === "pro")}
              >
                Pro <span className="text-[10px] bg-white/20 px-1.5 rounded-md">✨</span>
              </button>
              
              {/* Logout Button */}
              {currentUser && (
                <div className="flex items-center gap-2 mr-2">
                  <span className="text-secondary text-sm hidden sm:inline-block">Hi, <strong className="text-text">{currentUser}</strong></span>
                </div>
              )}
              <button
                onClick={logout}
                className="px-3 py-1.5 rounded-full bg-loss/10 border border-loss/20 text-loss hover:bg-loss/20 transition flex items-center gap-1 font-semibold text-sm"
              >
                Logout
              </button>
            </div>
            <span className="px-3 py-1 rounded-full bg-white/5 border border-border text-profit font-mono">
              Cash: Rp {(wallet.cash || 0).toLocaleString('id-ID')}
            </span>
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <main className="max-w-5xl mx-auto px-6 py-10 space-y-10 relative z-10">
        {children}
      </main>

      {/* Floating Toast Container */}
      <div className="fixed top-6 right-6 z-[9999] space-y-3 pointer-events-none max-w-sm w-full font-sans">
        {toasts.map(toast => (
          <div
            key={toast.id}
            className={`p-4 rounded-2xl border shadow-2xl flex items-start gap-3 pointer-events-auto transition-all duration-300 bg-card/95 backdrop-blur-md ${
              toast.type === 'success' ? 'border-profit/20 text-profit' :
              toast.type === 'error' ? 'border-loss/20 text-loss' :
              'border-accent/20 text-accent'
            }`}
          >
            <span className="text-lg">
              {toast.type === 'success' ? '🟢' : toast.type === 'error' ? '🔴' : '🔵'}
            </span>
            <div className="flex-1 text-xs font-bold leading-snug">{toast.message}</div>
            <button
              onClick={() => dismissToast(toast.id)}
              className="text-secondary hover:text-text transition text-xs font-mono px-1 cursor-pointer"
            >✕</button>
          </div>
        ))}
      </div>
    </div>
  );
}
