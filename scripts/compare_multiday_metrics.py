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

# Compare macro averages
macro_before = before.get('holdout_metrics_macro_avg', {})
macro_after = after.get('holdout_metrics_macro_avg', {})

print("=== ML Multi-day Macro Average Comparison (Before vs After) ===")
horizons = ['1d', '3d', '5d', '7d']
metrics = ['accuracy', 'buy_precision', 'buy_recall']

for h in horizons:
    print(f"\n--- Horizon: {h} ---")
    h_before = macro_before.get(h, {})
    h_after = macro_after.get(h, {})
    
    for metric in metrics:
        val_before = h_before.get(metric, 0)
        val_after = h_after.get(metric, 0)
        diff = val_after - val_before
        print(f"{metric.ljust(15)}: {val_before:.2f}% -> {val_after:.2f}% (Diff: {diff:+.2f}%)")
