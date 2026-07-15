from data.fetcher_stockbit import get_marketdetector_broker_summary

try:
    res = get_marketdetector_broker_summary('BBCA', '2023-01-01', '2023-01-02', limit=1)
    print(res)
except Exception as e:
    print(e)
