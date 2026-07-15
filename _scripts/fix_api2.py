import re

with open('/home/hamboo/my-product/stock-agent-idx/web-backend/main.py', 'r') as f:
    content = f.read()

if "from fastapi import Depends" not in content and "Depends," not in content and ", Depends" not in content:
    content = "from fastapi import Depends\n" + content

# But it's on line 1, wait.
with open('/home/hamboo/my-product/stock-agent-idx/web-backend/main.py', 'w') as f:
    f.write(content.replace("from fastapi import FastAPI, HTTPException", "from fastapi import FastAPI, HTTPException, Depends"))
