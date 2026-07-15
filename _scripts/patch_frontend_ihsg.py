import re

with open('/home/hamboo/my-product/stock-agent-idx/web-frontend/src/app/page.tsx', 'r') as f:
    content = f.read()

# Add accuracy UI to the IHSG page
frontend_snippet = """
                  {/* Accuracy Track Record */}
                  {ihsgData.accuracy && ihsgData.accuracy.total > 0 && (
                    <div className="bg-indigo-500/10 border border-indigo-500/20 rounded-2xl p-4 mt-6 flex items-center gap-4">
                      <div className="w-12 h-12 bg-indigo-500/20 rounded-full flex items-center justify-center text-xl">🎯</div>
                      <div>
                        <h4 className="text-sm font-bold text-indigo-300 tracking-wider uppercase mb-1">Track Record Akurasi</h4>
                        <p className="text-white font-medium">Akurasi Arah (Historical): <span className="text-emerald-400 font-bold">{ihsgData.accuracy.percentage}%</span> ({ihsgData.accuracy.correct}/{ihsgData.accuracy.total} hari prediksi tepat)</p>
                      </div>
                    </div>
                  )}

                  {/* Header Metrics */}
"""

if "Track Record Akurasi" not in content:
    content = content.replace("{/* Header Metrics */}", frontend_snippet)

with open('/home/hamboo/my-product/stock-agent-idx/web-frontend/src/app/page.tsx', 'w') as f:
    f.write(content)
