"use client";
import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import authenticatedFetch from '@/lib/apiClient';

// ─── Types ────────────────────────────────────────────────────────────────────
interface Toast { id: number; message: string; type: 'success' | 'error' | 'info'; }

interface AppContextValue {
  // Auth
  tokenStr: string | null;
  isPro: boolean;
  setIsPro: (v: boolean) => void;

  // Core data
  picks: any[];
  batchId: string;
  runDate: string;
  stats: { market_outlook: string; win_rate: number; profit_factor: number };
  wallet: { cash: number; invested: number; pnl: number };
  holdings: any[];
  historyData: any[];
  loading: boolean;
  debateCandidates: any[];

  // Toasts
  toasts: Toast[];
  showToast: (message: string, type?: 'success' | 'error' | 'info') => void;
  dismissToast: (id: number) => void;

  // Actions
  loadData: () => Promise<void>;
  handleTrade: (ticker: string, action: string, price: number) => Promise<void>;
  logout: () => void;
  currentUser: string | null;
}

const AppContext = createContext<AppContextValue | null>(null);

export function AppProvider({ children }: { children: React.ReactNode }) {
  const [tokenStr, setTokenStr] = useState<string | null>(null);
  const [isPro, setIsPro] = useState(false);
  const [picks, setPicks] = useState<any[]>([]);
  const [batchId, setBatchId] = useState("");
  const [runDate, setRunDate] = useState("");
  const [stats, setStats] = useState({ market_outlook: "Loading", win_rate: 0, profit_factor: 0 });
  const [wallet, setWallet] = useState({ cash: 0, invested: 0, pnl: 0 });
  const [holdings, setHoldings] = useState<any[]>([]);
  const [historyData, setHistoryData] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [debateCandidates, setDebateCandidates] = useState<any[]>([]);
  const [toasts, setToasts] = useState<Toast[]>([]);
  const [currentUser, setCurrentUser] = useState<string | null>(null);

  const logout = useCallback(() => {
    localStorage.removeItem("token");
    localStorage.removeItem("tier");
    localStorage.removeItem("username");
    setIsPro(false);
    setCurrentUser(null);
    setHoldings([]);
    setHistoryData([]);
    window.location.replace("/login");
  }, []);

  useEffect(() => {
    const token = localStorage.getItem("token");
    setTokenStr(token);
    setIsPro(localStorage.getItem("tier") === "pro");
    setCurrentUser(localStorage.getItem("username"));
    
    // Cegah redirect loop jika sedang di halaman login
    if (!token && !window.location.pathname.includes('/login')) {
      window.location.href = "/login";
    }
  }, []);

  const showToast = useCallback((message: string, type: 'success' | 'error' | 'info' = 'success') => {
    const id = Date.now();
    setToasts(prev => [...prev, { id, message, type }]);
    setTimeout(() => {
      setToasts(prev => prev.filter(t => t.id !== id));
    }, 4500);
  }, []);

  const dismissToast = useCallback((id: number) => {
    setToasts(prev => prev.filter(t => t.id !== id));
  }, []);

  const loadData = useCallback(async () => {
    const token = localStorage.getItem("token");

    authenticatedFetch('/api/signals/top-picks')
      .then(res => res.json())
      .then(data => {
        if (data.data) {
          setPicks(data.data);
          setBatchId(data.batch_id);
          setRunDate(data.run_date || "");
          setDebateCandidates(data.debate_candidates || []);
        }
      })
      .catch(err => console.error("Error loading picks:", err));

    authenticatedFetch('/api/dashboard/stats')
      .then(res => res.json())
      .then(data => {
        setStats(data);
        setLoading(false);
      })
      .catch(err => {
        console.error("Error loading stats:", err);
        setLoading(false);
      });

    authenticatedFetch('/api/portfolio/paper')
      .then(res => res.json())
      .then(data => {
        if (data.wallet) setWallet(data.wallet);
        if (data.holdings) setHoldings(data.holdings);
      })
      .catch(err => console.error("Error loading portfolio:", err));

    authenticatedFetch('/api/performance/history')
      .then(res => res.json())
      .then(data => {
        if (data.history) setHistoryData(data.history);
      })
      .catch(err => console.error("Error loading history:", err));
  }, []);

  const handleTrade = useCallback(async (ticker: string, action: string, price: number) => {
    if (!price) { showToast("Harga belum tersedia untuk saham ini.", "error"); return; }
    try {
      const res = await fetch('/api/portfolio/trade', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem("token")}`
        },
        body: JSON.stringify({
          ticker,
          action: action === "HOLD" ? "BUY" : action,
          shares: 100,
          price
        })
      });
      const data = await res.json();
      if (res.ok) {
        showToast(`Sukses beli 1 lot ${ticker}!`);
        loadData();
      } else {
        showToast(`Gagal: ${data.detail || 'Error'}`, 'error');
      }
    } catch {
      showToast("Terjadi kesalahan jaringan", 'error');
    }
  }, [loadData, showToast]);

  useEffect(() => {
    if (tokenStr !== null) loadData();
  }, [tokenStr, loadData]);

  return (
    <AppContext.Provider value={{
      tokenStr, isPro, setIsPro,
      picks, batchId, runDate, stats, wallet, holdings, historyData, loading, debateCandidates,
      toasts, showToast, dismissToast,
      loadData, handleTrade, logout, currentUser
    }}>
      {children}
    </AppContext.Provider>
  );
}

export function useApp() {
  const ctx = useContext(AppContext);
  if (!ctx) throw new Error("useApp must be used within AppProvider");
  return ctx;
}
