import re

with open("web-frontend/src/app/(app)/trading/page.tsx", "r") as f:
    content = f.read()

# Split the content rendering based on activeTab
tab_routing = """
            {/* Conditional Rendering based on Tabs */}
            {activeTab === 'desk' ? (
              <>
                {/* Topup + Equity Chart */}
"""

content = content.replace("{/* Topup + Equity Chart */}", tab_routing)

# Replace the Closed trades section and wrap up desk view, then inject Analytics view
analytics_view = """
              </>
            ) : (
              /* ANALYTICS TAB CONTENT */
              <div className="space-y-6 animate-fade-in">
                {/* Performance Metrics Cards */}
                {performanceLoading ? (
                  <div className="py-10 text-center text-secondary">Memuat metrik analitik...</div>
                ) : performanceData ? (
                  <>
                    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                      <div className="bg-card border border-border rounded-2xl p-5">
                        <p className="text-[11px] text-secondary font-bold uppercase tracking-wider mb-2">Total Trades</p>
                        <p className="text-2xl font-black font-mono text-text">{performanceData.total_trades}</p>
                        <div className="flex gap-2 mt-2 text-xs font-mono">
                          <span className="text-[#22C55E]">{performanceData.winning_trades} Win</span>
                          <span className="text-secondary">/</span>
                          <span className="text-loss">{performanceData.losing_trades} Loss</span>
                        </div>
                      </div>
                      
                      <div className="bg-card border border-border rounded-2xl p-5">
                        <p className="text-[11px] text-secondary font-bold uppercase tracking-wider mb-2">Win Rate</p>
                        <p className={`text-2xl font-black font-mono ${performanceData.win_rate_pct >= 50 ? 'text-[#22C55E]' : 'text-loss'}`}>
                          {performanceData.win_rate_pct?.toFixed(1)}%
                        </p>
                      </div>

                      <div className="bg-card border border-border rounded-2xl p-5">
                        <p className="text-[11px] text-secondary font-bold uppercase tracking-wider mb-2">Profit Factor</p>
                        <p className={`text-2xl font-black font-mono ${performanceData.profit_factor >= 1 ? 'text-[#22C55E]' : 'text-loss'}`}>
                          {performanceData.profit_factor?.toFixed(2)}
                        </p>
                        <p className="text-[10px] text-secondary mt-1">Gross Profit / Gross Loss</p>
                      </div>

                      <div className="bg-card border border-border rounded-2xl p-5">
                        <p className="text-[11px] text-secondary font-bold uppercase tracking-wider mb-2">Avg Return / Trade</p>
                        <p className={`text-2xl font-black font-mono ${performanceData.avg_return_pct >= 0 ? 'text-[#22C55E]' : 'text-loss'}`}>
                          {performanceData.avg_return_pct >= 0 ? '+' : ''}{performanceData.avg_return_pct?.toFixed(2)}%
                        </p>
                      </div>
                    </div>

                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                      <div className="bg-card border border-border rounded-2xl p-5 bg-gradient-to-br from-[#22C55E]/5 to-transparent border-[#22C55E]/20">
                        <p className="text-[11px] text-secondary font-bold uppercase tracking-wider mb-2">Gross Profit (Total Untung)</p>
                        <p className="text-2xl font-black font-mono text-[#22C55E]">Rp {performanceData.total_profit?.toLocaleString('id-ID')}</p>
                      </div>
                      <div className="bg-card border border-border rounded-2xl p-5 bg-gradient-to-br from-loss/5 to-transparent border-loss/20">
                        <p className="text-[11px] text-secondary font-bold uppercase tracking-wider mb-2">Gross Loss (Total Rugi)</p>
                        <p className="text-2xl font-black font-mono text-loss">Rp {performanceData.total_loss?.toLocaleString('id-ID')}</p>
                      </div>
                    </div>
                  </>
                ) : (
                  <div className="py-10 text-center text-secondary">Gagal memuat analitik.</div>
                )}

                {/* Big Equity Curve inside Analytics */}
                <div className="mt-8">
                  <h3 className="text-lg font-bold text-text mb-4">Grafik Pertumbuhan Portfolio (Equity Curve)</h3>
                  <div className="h-[280px]">
                    <CustomEquityChart points={equityData?.points || []} />
                  </div>
                </div>

                {/* Closed Trades History (Full List) */}
                <div className="mt-8">
                  <h3 className="text-lg font-bold text-text mb-4 flex items-center gap-2"><span>📜</span> Trade History Ledger</h3>
                  <div className="overflow-x-auto rounded-2xl border border-border bg-background/40 max-h-[600px] overflow-y-auto">
                    <table className="w-full text-left border-collapse text-sm">
                      <thead className="sticky top-0 bg-background/95 backdrop-blur-sm z-10 shadow-sm">
                        <tr className="border-b border-border text-xs font-bold uppercase tracking-wider text-secondary">
                          <th className="py-3 px-6">Tanggal</th>
                          <th className="py-3 px-6">Ticker</th>
                          <th className="py-3 px-6 text-center">Status</th>
                          <th className="py-3 px-6 text-right">Volume</th>
                          <th className="py-3 px-6 text-right">Buy @</th>
                          <th className="py-3 px-6 text-right">Sell @</th>
                          <th className="py-3 px-6 text-right">Realized P&L</th>
                          <th className="py-3 px-6 text-right">Return</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-white/5 text-secondary font-mono">
                        {closedTrades.map((row: any, idx: number) => {
                          const isProfit = row.realized_pnl >= 0;
                          return (
                            <tr key={idx} className="hover:bg-white/5 transition">
                              <td className="py-3 px-6 font-sans text-secondary">{row.closed_at ? row.closed_at.split('T')[0] : row.opened_at?.split('T')[0]}</td>
                              <td className="py-3 px-6 font-sans font-bold text-text">{row.ticker}</td>
                              <td className="py-3 px-6 text-center">
                                <span className={`px-2 py-1 text-[10px] font-bold rounded-full uppercase tracking-wider ${row.status === 'TP_HIT' ? 'bg-profit/10 text-profit' : row.status === 'SL_HIT' ? 'bg-loss/10 text-loss' : 'bg-slate-500/10 text-secondary'}`}>
                                  {row.status?.replace('_', ' ') || 'CLOSED'}
                                </span>
                              </td>
                              <td className="py-3 px-6 text-right">{row.lot} lot</td>
                              <td className="py-3 px-6 text-right">Rp {row.price?.toLocaleString('id-ID')}</td>
                              <td className="py-3 px-6 text-right">Rp {row.exit_price?.toLocaleString('id-ID') || '-'}</td>
                              <td className={`py-3 px-6 text-right font-bold ${isProfit ? 'text-[#22C55E]' : 'text-loss'}`}>{isProfit ? '+' : ''}{row.realized_pnl?.toLocaleString('id-ID')}</td>
                              <td className={`py-3 px-6 text-right font-bold ${isProfit ? 'text-[#22C55E]' : 'text-loss'}`}>{isProfit ? '+' : ''}{row.realized_pnl_pct?.toFixed(2)}%</td>
                            </tr>
                          );
                        })}
                        {closedTrades.length === 0 && <tr><td colSpan={8} className="py-10 text-center text-secondary font-sans">Belum ada riwayat transaksi ditutup.</td></tr>}
                      </tbody>
                    </table>
                  </div>
                </div>

              </div>
            )}
"""

content = content.replace("{/* Closed Trades */}", analytics_view + "\n            {/* Closed Trades */}")
content = content.replace("export default function TradingPage() {", "import { CalendarIcon } from '@radix-ui/react-icons';\nexport default function TradingPage() {")

# We want to remove the old closed trades section since it's moved inside the analytics tab
pattern_closed = r"\{\/\* Closed Trades \*\/\}.*?<\/div>\s*<\/>"
# this might be too greedy or hard to match exactly, let's use a simpler string replace

with open("web-frontend/src/app/(app)/trading/page.tsx", "w") as f:
    f.write(content)

print("UI content patched")
