import re

with open('/home/hamboo/my-product/stock-agent-idx/agents/ihsg_predictor.py', 'r') as f:
    content = f.read()

# Add to top of file
if "from agents.llm_client import invoke_json_im" not in content:
    content = "from agents.llm_client import invoke_json_im\n" + content
    
with open('/home/hamboo/my-product/stock-agent-idx/agents/ihsg_predictor.py', 'w') as f:
    f.write(content)
