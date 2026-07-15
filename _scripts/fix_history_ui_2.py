import re

with open('/home/hamboo/my-product/stock-agent-idx/web-frontend/src/app/page.tsx', 'r') as f:
    content = f.read()

# Try matching the exact column for IHSG history in NextJS page.tsx
# In Next.js UI the th for Confidence is:
# <th className="py-3.5 px-6 text-center">Confidence</th>

th_pattern = r'(<th className="py-3\.5 px-6 text-center">Confidence</th>)'
th_replacement = r'\1\n                              <th className="py-3.5 px-6 text-center">Status Validasi</th>'

# And for td:
# <td className="py-3.5 px-6 text-center font-bold">{row.confidence}</td>
td_pattern = r'(<td className="py-3\.5 px-6 text-center font-bold">\{row\.confidence\}</td>)'
td_replacement = r'''\1
                              <td className="py-3.5 px-6 text-center font-sans">
                                {row.is_correct === true && <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-bold bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">Benar ✅</span>}
                                {row.is_correct === false && <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-bold bg-red-500/20 text-red-400 border border-red-500/30">Salah ❌</span>}
                                {row.is_correct === null && <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-bold bg-gray-500/20 text-gray-400 border border-gray-500/30">Pending ⏳</span>}
                              </td>'''

content = re.sub(th_pattern, th_replacement, content)
content = re.sub(td_pattern, td_replacement, content)

with open('/home/hamboo/my-product/stock-agent-idx/web-frontend/src/app/page.tsx', 'w') as f:
    f.write(content)
