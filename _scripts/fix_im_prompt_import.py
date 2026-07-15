import re

with open('/home/hamboo/my-product/stock-agent-idx/agents/ihsg_predictor.py', 'r') as f:
    content = f.read()

# Already imported LLM_ENABLED, LLM_MODEL_INVESTMENT_MANAGER
if "from agents.debate.personas import IM_SYSTEM_PROMPT" not in content:
    old = "from config import LLM_ENABLED, LLM_MODEL_INVESTMENT_MANAGER, LLM_MODEL_IM_FALLBACK"
    new = "from config import LLM_ENABLED, LLM_MODEL_INVESTMENT_MANAGER, LLM_MODEL_IM_FALLBACK\nfrom agents.debate.personas import IM_SYSTEM_PROMPT"
    content = content.replace(old, new)
    
with open('/home/hamboo/my-product/stock-agent-idx/agents/ihsg_predictor.py', 'w') as f:
    f.write(content)
