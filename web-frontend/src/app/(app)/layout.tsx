"use client";
import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useApp } from '../context/AppContext';
import {
  HomeIcon,
  TargetIcon,
  LightningBoltIcon,
  PieChartIcon,
  ClockIcon,
  RocketIcon,
  CardStackIcon,
  GearIcon,
  ExitIcon,
  CrossCircledIcon,
  CheckCircledIcon,
  InfoCircledIcon,
  HamburgerMenuIcon,
  IdCardIcon
} from '@radix-ui/react-icons';
import { Button } from '@/components/ui/button';

const navItems = [
  { href: "/", label: "Home Dashboard", icon: HomeIcon, id: "dashboard" },
  { href: "/top-picks", label: "AI Top Picks", icon: TargetIcon, id: "top-picks" },
  { href: "/trading", label: "Trading Engine", icon: LightningBoltIcon, id: "trading" },
  { href: "/bandarmologi", label: "Bandarmologi", icon: PieChartIcon, id: "bandarmologi" },
  { href: "/ihsg", label: "IHSG Predictor", icon: ClockIcon, id: "ihsg" },
  { href: "/performance", label: "AI Performance", icon: RocketIcon, id: "history" },
  { href: "/portfolio", label: "Portfolio Management", icon: CardStackIcon, id: "portfolio" },
  { href: "/billing", label: "Billing & Upgrade", icon: IdCardIcon, id: "billing" },
  { href: "/settings", label: "Preferences", icon: GearIcon, id: "settings" },
];

export default function AppShellLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const { wallet, toasts, dismissToast, isPro, setIsPro, logout, currentUser } = useApp();
  const [sidebarOpen, setSidebarOpen] = useState(false);

  useEffect(() => {
    const token = localStorage.getItem("token");
    if (!token && pathname !== "/login") {
      window.location.replace("/login");
    }
  }, [pathname]);

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
              <CrossCircledIcon className="w-5 h-5" />
            </button>
          </div>

          <nav className="space-y-2">
            {navItems.map((item) => {
              const IconComponent = item.icon;
              return (
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
                  <IconComponent className="w-5 h-5" /> {item.label}
                </Link>
              );
            })}
          </nav>

                    <div className="mt-auto pt-6 border-t border-border">
            <div className="bg-background border border-border rounded-xl p-1 mb-4 flex text-xs font-medium">
              <button
                className={`flex-1 py-2 rounded-lg transition ${isPro ? 'text-secondary hover:text-text' : 'bg-accent text-text shadow-md'}`}
                onClick={() => setIsPro(false)}
              >Free</button>
              <button
                className={`flex-1 py-2 rounded-lg transition flex items-center justify-center gap-1 ${isPro ? 'bg-accent text-text shadow-md' : 'text-secondary hover:text-text'}`}
                onClick={() => setIsPro(localStorage?.getItem("tier") === "pro")}
              >
                Pro <span className="text-[10px] bg-white/20 px-1 rounded-md">✨</span>
              </button>
            </div>
            <button
              onClick={logout}
              className="flex items-center gap-4 px-4 py-3 text-loss hover:text-red-300 hover:bg-loss/10 rounded-xl transition font-medium w-full"
            >
              <ExitIcon className="w-5 h-5" /> Sign Out
            </button>
          </div>
        </div>
      </aside>

            {/* Navbar */}
      <nav className="sticky top-0 z-50 bg-background/80 backdrop-blur-xl border-b border-border">
        <div className="max-w-5xl mx-auto px-4 md:px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <button onClick={() => setSidebarOpen(true)} className="p-2 -ml-2 rounded-lg text-secondary hover:text-text hover:bg-white/10 transition">
              <HamburgerMenuIcon className="w-6 h-6" />
            </button>
            <div className="w-8 h-8 rounded-full bg-accent flex items-center justify-center shadow-lg shadow-accent/20 text-text font-bold text-sm hidden sm:flex">
              H
            </div>
            <h1 className="font-bold text-lg md:text-xl tracking-wide">
              Hamboo<span className="text-accent">.ai</span>
            </h1>
          </div>

          <div className="flex items-center gap-3 text-sm font-medium">
            {/* Desktop Only Actions */}
            <div className="hidden md:flex bg-background p-1 rounded-full border border-border items-center shrink-0 text-xs">
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
              
              {currentUser && (
                <div className="flex items-center gap-2 mx-2 pl-2 border-l border-border">
                  <span className="text-secondary text-sm">Hi, <strong className="text-text">{currentUser}</strong></span>
                </div>
              )}
              <button
                onClick={logout}
                className="px-3 py-1.5 rounded-full bg-loss/10 border border-loss/20 text-loss hover:bg-loss/20 transition flex items-center gap-1 font-semibold text-sm ml-1"
              >
                Logout
              </button>
            </div>

            {/* Always Visible: Cash */}
            <span className="px-3 py-1.5 rounded-full bg-white/5 border border-border text-profit font-mono text-xs sm:text-sm shrink-0">
              <span className="hidden sm:inline">Cash: </span>Rp {(wallet.cash || 0).toLocaleString('id-ID')}
            </span>
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <main className="max-w-5xl mx-auto px-4 md:px-6 py-10 space-y-10 relative z-10">
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
            <div className="text-lg flex-shrink-0">
              {toast.type === 'success' ? (
                <CheckCircledIcon className="w-5 h-5" />
              ) : toast.type === 'error' ? (
                <CrossCircledIcon className="w-5 h-5" />
              ) : (
                <InfoCircledIcon className="w-5 h-5" />
              )}
            </div>
            <div className="flex-1 text-xs font-bold leading-snug">{toast.message}</div>
            <button
              onClick={() => dismissToast(toast.id)}
              className="text-secondary hover:text-text transition text-xs font-mono px-1 cursor-pointer flex-shrink-0"
            >
              <CrossCircledIcon className="w-4 h-4" />
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
