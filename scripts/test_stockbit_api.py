import sys
import os
import httpx
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import dotenv
dotenv.load_dotenv()

from data.fetcher_stockbit import _get_api_key

api_key = _get_api_key()
url = "https://exodus.stockbit.com/company-price-feed/historical/summary/BBCA"
params = {
    "period": "HS_PERIOD_DAILY",
    "start_date": "2024-01-01",
    "end_date": "2024-01-05",
    "limit": "5",
    "page": "1",
}
headers = {
    "Authorization": f"Bearer {api_key}",
    "User-Agent": "Stockbit/5.6.8 (Android; 10; Scale/2.00)"
}
response = httpx.get(url, params=params, headers=headers)
print(response.json())
