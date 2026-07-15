import httpx
import os
from dotenv import load_dotenv

load_dotenv()

def test_login():
    username = os.getenv("STOCKBIT_USERNAME")
    password = os.getenv("STOCKBIT_PASSWORD")
    
    url = "https://exodus.stockbit.com/login/v6/username"
    payload = {
        "user": username,
        "password": password,
        "player_id": "c260c141-f3e3-4470-af3a-02ca57204d50"
    }
    headers = {
        "User-Agent": "Stockbit/5.6.8 (Android; 10; Scale/2.00)"
    }
    
    response = httpx.post(url, json=payload, headers=headers)
    print("v6 response:", response.status_code, response.text)

if __name__ == "__main__":
    test_login()
