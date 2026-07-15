import re

with open('/home/hamboo/my-product/stock-agent-idx/web-frontend/src/app/page.tsx', 'r') as f:
    content = f.read()

# Let's find the table row mapping for IHSG history
# Look for: <td className="py-3 px-4">{item.confidence}</td>
ui_pattern = r'(<td className="py-3 px-4">{item\.confidence}</td>)'

replacement = r'''\1
                          <td className="py-3 px-4">
                            {item.is_correct === true && <span className="inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"><span className="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>Benar</span>}
                            {item.is_correct === false && <span className="inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium bg-red-500/10 text-red-400 border border-red-500/20"><span className="w-1.5 h-1.5 rounded-full bg-red-400"></span>Salah</span>}
                            {item.is_correct === null && <span className="inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium bg-gray-500/10 text-gray-400 border border-gray-500/20">⏳ Pending</span>}
                          </td>'''

content = re.sub(ui_pattern, replacement, content)

# Also add the table header
th_pattern = r'(<th className="text-left py-3 px-4 font-semibold">Confidence</th>)'
th_replacement = r'''\1
                        <th className="text-left py-3 px-4 font-semibold">Validasi Aktual</th>'''
                        
content = re.sub(th_pattern, th_replacement, content)

with open('/home/hamboo/my-product/stock-agent-idx/web-frontend/src/app/page.tsx', 'w') as f:
    f.write(content)
