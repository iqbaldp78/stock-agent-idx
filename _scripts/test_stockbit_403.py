import os
from data.fetcher_stockbit import get_current_price_stockbit, STOCKBIT_ORDERBOOK_URL
import httpx

api_key = os.getenv("STOCKBIT_API_KEY")
url = STOCKBIT_ORDERBOOK_URL.format(ticker="adro")

headers = {
    "Authorization": f"Bearer {api_key}",
    "User-Agent": "Stockbit/5.6.8 (Android; 10; Scale/2.00)"
}
print("Testing with User-Agent...")
with httpx.Client(timeout=15.0) as client:
    response = client.get(url, headers=headers)
    print("Status code:", response.status_code)
    if response.status_code == 200:
        print("Success!", response.json().get("data", {}).get("bid", [])[0].get("price"))
    else:
        print("Response:", response.text)
