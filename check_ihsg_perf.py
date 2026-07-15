import re

with open('/home/hamboo/my-product/stock-agent-idx/scheduler.py', 'r') as f:
    content = f.read()

# Let's add a job for IHSG performance tracking specifically if it doesn't exist.
