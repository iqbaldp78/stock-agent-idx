import json

with open("data/last_analysis_result.json") as f:
    data = json.load(f)

print("Number of top picks:", len(data.get("top_picks", [])))
for i, pick in enumerate(data.get("top_picks", [])):
    print(f"Pick {i} ({pick.get('ticker')}):")
    print("  Has price_prediction?", "price_prediction" in pick)
    if "price_prediction" in pick:
        print("  keys:", pick["price_prediction"].keys())
