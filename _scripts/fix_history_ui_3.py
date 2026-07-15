import re

with open('/home/hamboo/my-product/stock-agent-idx/web-frontend/src/app/page.tsx', 'r') as f:
    content = f.read()

# I see the problem. I replaced the header but I didn't actually patch the data row (td) correctly in the last step.
# Let's fix the td. The original td is:
# <td className="py-3.5 px-6 text-center font-bold">{row.confidence}</td>

td_pattern = r'(<td className="py-3\.5 px-6 text-center">\s*<span className={`px-2\.5 py-0\.5 rounded text-\[11px\] font-sans font-bold uppercase tracking-wider[^>]*>\s*\{row\.confidence\}\s*</span>\s*</td>)'
# Wait, let's look at the actual row.confidence td in the file.
