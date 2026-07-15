import re
with open("/home/hamboo/my-product/stock-agent-idx/web-frontend/src/app/(app)/history/page.tsx", "r") as f:
    content = f.read()

# Fix the hardcoded localhost which causes issues when accessed from outside the network/via Nginx
# Using relative URL /api/... so Nginx can proxy it properly.
content = content.replace("fetch('http://localhost:8000/api/ai/performance-metrics'", "fetch('/api/ai/performance-metrics'")

with open("/home/hamboo/my-product/stock-agent-idx/web-frontend/src/app/(app)/history/page.tsx", "w") as f:
    f.write(content)
