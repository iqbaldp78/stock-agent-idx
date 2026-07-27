import urllib.request
import json
import os

# Create a test token bypassing normal flow for local debug 
# (we assume testkopong is user_id 4)
import jwt
from datetime import datetime, timedelta

SECRET_KEY = os.environ.get("SECRET_KEY", "supersecret-jwt-key")
ALGORITHM = "HS256"
payload = {
    "sub": "testkopong",
    "user_id": 4,
    "exp": datetime.utcnow() + timedelta(days=1)
}
token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

req = urllib.request.Request("http://127.0.0.1:8000/api/trading/performance")
req.add_header("Authorization", f"Bearer {token}")
try:
    with urllib.request.urlopen(req) as response:
        print(response.read().decode())
except Exception as e:
    print("Error:", e)
