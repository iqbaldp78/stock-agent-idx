import re

with open('/home/hamboo/my-product/stock-agent-idx/agents/ihsg_predictor.py', 'r') as f:
    content = f.read()

# Already imported LLM_ENABLED, let's fix the model imports
if "from config import LLM_MODEL_INVESTMENT_MANAGER" not in content:
    old = "from config import LLM_ENABLED"
    new = "from config import LLM_ENABLED, LLM_MODEL_INVESTMENT_MANAGER, LLM_MODEL_IM_FALLBACK"
    content = content.replace(old, new)
    
with open('/home/hamboo/my-product/stock-agent-idx/agents/ihsg_predictor.py', 'w') as f:
    f.write(content)
