import re

with open("web-frontend/src/app/(app)/trading/page.tsx", "r") as f:
    content = f.read()

# Replace the title part to include Tabs
tabs_replacement = """
      <div className="flex flex-col gap-4 mb-6">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <h2 className="text-3xl font-bold text-text mb-2">Trading <span className="text-accent">Engine</span></h2>
            <p className="text-secondary">Virtual Portfolio Validator — Uji strategi trading Anda dengan modal virtual secara real-time.</p>
          </div>
          <div className="flex gap-3">
            <button onClick={handleCheckTpsl} className="px-4 py-2.5 bg-indigo-600 hover:bg-accent text-text font-bold rounded-xl text-sm transition flex items-center gap-2 shadow-lg shadow-indigo-600/20">
              <DoubleArrowUpIcon className="w-4 h-4" /> Cek TP/SL
            </button>
            <button onClick={handleResetPortfolio} className="px-4 py-2.5 bg-loss/10 hover:bg-loss/20 border border-loss/20 text-loss font-semibold rounded-xl text-sm transition flex items-center gap-2">
              <ReloadIcon className="w-4 h-4" /> Reset
            </button>
          </div>
        </div>
        
        {/* Sub-Navigation Tabs */}
        {!tradingLoading && tradingData && tradingData.status !== 'not_setup' && (
          <div className="flex gap-2 p-1 bg-white/5 border border-border rounded-xl w-fit">
            <button
              onClick={() => setActiveTab('desk')}
              className={`px-4 py-2 rounded-lg text-sm font-bold transition-all ${
                activeTab === 'desk' 
                  ? 'bg-accent text-text shadow-md' 
                  : 'text-secondary hover:text-text hover:bg-white/10'
              }`}
            >
              Trading Desk
            </button>
            <button
              onClick={() => setActiveTab('analytics')}
              className={`px-4 py-2 rounded-lg text-sm font-bold transition-all ${
                activeTab === 'analytics' 
                  ? 'bg-accent text-text shadow-md' 
                  : 'text-secondary hover:text-text hover:bg-white/10'
              }`}
            >
              Performance Analytics
            </button>
          </div>
        )}
      </div>
"""

# Find the start of the return statement
pattern = r"<div className=\"flex flex-wrap items-center justify-between gap-4\">\s*<div>\s*<h2 className=\"text-3xl font-bold text-text mb-2\">Trading <span className=\"text-accent\">Engine</span></h2>\s*<p className=\"text-secondary\">Virtual Portfolio Validator — Uji strategi trading Anda dengan modal virtual secara real-time\.</p>\s*</div>\s*<div className=\"flex gap-3\">\s*<button onClick=\{handleCheckTpsl\} className=\"px-4 py-2\.5 bg-indigo-600 hover:bg-accent text-text font-bold rounded-xl text-sm transition flex items-center gap-2 shadow-lg shadow-indigo-600/20\">\s*<DoubleArrowUpIcon className=\"w-4 h-4\" /> Cek TP/SL Sekarang\s*</button>\s*<button onClick=\{handleResetPortfolio\} className=\"px-4 py-2\.5 bg-loss/10 hover:bg-loss/20 border border-loss/20 text-loss font-semibold rounded-xl text-sm transition flex items-center gap-2\">\s*<ReloadIcon className=\"w-4 h-4\" /> Reset Portfolio\s*</button>\s*</div>\s*</div>"

content = re.sub(pattern, tabs_replacement, content)

with open("web-frontend/src/app/(app)/trading/page.tsx", "w") as f:
    f.write(content)

print("Tabs added")
