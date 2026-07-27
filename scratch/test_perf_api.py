import urllib.request
import json

req = urllib.request.Request("http://127.0.0.1:8000/api/trading/performance")
try:
    with urllib.request.urlopen(req) as response:
        print(response.read().decode())
except Exception as e:
    print("Error:", e)
