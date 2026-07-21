import json
import sys

def load_json(filepath):
    try:
        with open(filepath, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Failed to load {filepath}: {e}")
        return {}

before = load_json('validate_ml_result_before.json')
after = load_json('validate_ml_result.json')

if not before or not after:
    print("Missing one of the result files.")
    sys.exit(1)

tickers_before = before.get('tickers', {})
tickers_after = after.get('tickers', {})

print("=== ML Accuracy Comparison (Before vs After) ===")
common_tickers = set(tickers_before.keys()).intersection(set(tickers_after.keys()))

metrics = ['directional_accuracy', 'mae_pct', 'buy_precision', 'buy_recall']

def avg_metric(data_dict, metric):
    vals = [data_dict[t].get('aggregate', {}).get(metric, 0) for t in common_tickers if t in data_dict]
    return sum(vals) / len(vals) if vals else 0

for metric in metrics:
    val_before = avg_metric(tickers_before, metric)
    val_after = avg_metric(tickers_after, metric)
    diff = val_after - val_before
    print(f"{metric.ljust(25)}: {val_before:.2f}% -> {val_after:.2f}% (Diff: {diff:+.2f}%)")
