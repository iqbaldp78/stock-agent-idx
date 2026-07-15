import re

with open('/home/hamboo/my-product/stock-agent-idx/agents/ihsg_predictor.py', 'r') as f:
    content = f.read()

if "import json" not in content:
    content = "import json\n" + content
    
with open('/home/hamboo/my-product/stock-agent-idx/agents/ihsg_predictor.py', 'w') as f:
    f.write(content)
