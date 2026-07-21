import json
import sys

def load_json(filepath):
    try:
        with open(filepath, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Failed to load {filepath}: {e}")
        return {}

before = load_json('models/checkpoints/lgbm_multiday_meta_before.json')
after = load_json('models/checkpoints/lgbm_multiday_meta.json')

if not before or not after:
    print("Missing one of the multiday result files.")
    sys.exit(1)

tickers_before = {t['ticker']: t for t in before.get('tickers', [])}
tickers_after = {t['ticker']: t for t in after.get('tickers', [])}

common_tickers = set(tickers_before.keys()).intersection(set(tickers_after.keys()))

print(f"Comparing common tickers: {list(common_tickers)}")
horizons = ['1d', '3d', '5d', '7d']
metrics = ['accuracy', 'buy_precision', 'buy_recall']

for ticker in common_tickers:
    print(f"\n================ Ticker: {ticker} ================")
    t_before = tickers_before[ticker]['metrics']
    t_after = tickers_after[ticker]['metrics']
    
    for h in horizons:
        print(f"\n--- Horizon: {h} ---")
        h_before = t_before.get(h, {})
        h_after = t_after.get(h, {})
        
        for metric in metrics:
            val_before = h_before.get(metric, 0)
            val_after = h_after.get(metric, 0)
            diff = val_after - val_before
            print(f"{metric.ljust(15)}: {val_before:.2f}% -> {val_after:.2f}% (Diff: {diff:+.2f}%)")
