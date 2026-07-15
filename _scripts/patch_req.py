import re

with open('/home/hamboo/my-product/stock-agent-idx/web-backend/requirements.txt', 'r') as f:
    content = f.read()

content = content.replace("pydanticpyjwt", "pydantic\nPyJWT")

with open('/home/hamboo/my-product/stock-agent-idx/web-backend/requirements.txt', 'w') as f:
    f.write(content)
