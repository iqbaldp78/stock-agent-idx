import re

with open('/home/hamboo/my-product/stock-agent-idx/agents/ihsg_predictor.py', 'r') as f:
    content = f.read()

# I see it failed with: name 'invoke_json_im' is not defined. It means it wasn't imported properly or llm_client doesn't have it.
# Let's check what's in llm_client first, but I will write this quick fix.
