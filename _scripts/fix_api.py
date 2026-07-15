import re

with open('/home/hamboo/my-product/stock-agent-idx/web-backend/main.py', 'r') as f:
    content = f.read()

# Make sure Depends is imported
if "Depends" not in content[:500]:
    content = content.replace("from fastapi import FastAPI, HTTPException, Header", "from fastapi import FastAPI, HTTPException, Header, Depends")
    content = content.replace("from fastapi import FastAPI, HTTPException", "from fastapi import FastAPI, HTTPException, Depends")

with open('/home/hamboo/my-product/stock-agent-idx/web-backend/main.py', 'w') as f:
    f.write(content)
