import os
import sys
import httpx
from dotenv import load_dotenv

# Load env file
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))

def main():
    refresh_token = os.getenv("STOCKBIT_REFRESH_TOKEN")
    if not refresh_token:
        print("STOCKBIT_REFRESH_TOKEN is empty in .env!")
        return

    print(f"Token loaded (first 30 chars): {refresh_token[:30]}...")

    url = "https://exodus.stockbit.com/login/refresh"
    base_headers = {
        "Authorization": f"Bearer {refresh_token}",
        "User-Agent": "Stockbit/5.6.8 (Android; 10; Scale/2.00)"
    }

    # Test 1: No body
    print("\n--- Test 1: No Body ---")
    try:
        resp1 = httpx.post(url, headers=base_headers, timeout=10.0)
        print(f"Status: {resp1.status_code}")
        print(f"Response: {resp1.text}")
    except Exception as e:
        print(f"Error: {e}")

    # Test 2: json={}
    print("\n--- Test 2: json={} ---")
    try:
        headers2 = base_headers.copy()
        headers2["Content-Type"] = "application/json"
        resp2 = httpx.post(url, headers=headers2, json={}, timeout=10.0)
        print(f"Status: {resp2.status_code}")
        print(f"Response: {resp2.text}")
    except Exception as e:
        print(f"Error: {e}")

    # Test 3: data=""
    print("\n--- Test 3: data='' ---")
    try:
        headers3 = base_headers.copy()
        headers3["Content-Type"] = "application/x-www-form-urlencoded"
        resp3 = httpx.post(url, headers=headers3, data="", timeout=10.0)
        print(f"Status: {resp3.status_code}")
        print(f"Response: {resp3.text}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
