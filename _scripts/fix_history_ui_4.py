import re

with open('/home/hamboo/my-product/stock-agent-idx/web-frontend/src/app/page.tsx', 'r') as f:
    content = f.read()

td_pattern = r'''(                              <td className="py-3\.5 px-6 text-center">\s*<span className={`px-2\.5 py-0\.5 rounded text-\[11px\] font-sans font-bold uppercase tracking-wider \${\s*row\.confidence === 'HIGH' \? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' :\s*row\.confidence === 'MEDIUM' \? 'bg-amber-500/10 text-amber-400 border border-amber-500/20' :\s*'bg-red-500/10 text-red-400 border border-red-500/20'\s*}\`>\s*\{row\.confidence\}\s*</span>\s*</td>)'''

td_replacement = r'''\1
                              <td className="py-3.5 px-6 text-center font-sans">
                                {row.is_correct === true && <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-bold bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">Benar ✅</span>}
                                {row.is_correct === false && <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-bold bg-red-500/20 text-red-400 border border-red-500/30">Salah ❌</span>}
                                {row.is_correct === null && <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-bold bg-gray-500/20 text-gray-400 border border-gray-500/30">Pending ⏳</span>}
                              </td>'''

content = re.sub(td_pattern, td_replacement, content)

with open('/home/hamboo/my-product/stock-agent-idx/web-frontend/src/app/page.tsx', 'w') as f:
    f.write(content)
