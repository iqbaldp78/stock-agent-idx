import os
import sys
import httpx
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))

def main():
    refresh_token = os.getenv("STOCKBIT_REFRESH_TOKEN")
    url = "https://exodus.stockbit.com/login/refresh"
    base_headers = {
        "User-Agent": "Stockbit/5.6.8 (Android; 10; Scale/2.00)"
    }
    player_id = "c260c141-f3e3-4470-af3a-02ca57204d50"

    # Test 4: Refresh token in header, player_id in body
    print("\n--- Test 4: Header=refresh_token, body={'player_id': ...} ---")
    try:
        h4 = base_headers.copy()
        h4["Authorization"] = f"Bearer {refresh_token}"
        resp4 = httpx.post(url, headers=h4, json={"player_id": player_id}, timeout=10.0)
        print(f"Status: {resp4.status_code}")
        print(f"Response: {resp4.text[:200]}")
    except Exception as e:
        print(f"Error: {e}")

    # Test 5: No Auth header, refresh_token in body
    print("\n--- Test 5: No Auth header, body={'refresh_token': ...} ---")
    try:
        resp5 = httpx.post(url, headers=base_headers, json={"refresh_token": refresh_token}, timeout=10.0)
        print(f"Status: {resp5.status_code}")
        print(f"Response: {resp5.text[:200]}")
    except Exception as e:
        print(f"Error: {e}")

    # Test 6: Auth header = access_token (expired), refresh_token in body
    # Let's see if we can use the current STOCKBIT_API_KEY as the expired access token
    access_token = os.getenv("STOCKBIT_API_KEY")
    print("\n--- Test 6: Header=access_token, body={'refresh_token': ...} ---")
    try:
        h6 = base_headers.copy()
        h6["Authorization"] = f"Bearer {access_token}"
        resp6 = httpx.post(url, headers=h6, json={"refresh_token": refresh_token}, timeout=10.0)
        print(f"Status: {resp6.status_code}")
        print(f"Response: {resp6.text[:200]}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
