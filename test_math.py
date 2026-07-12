import json

with open("data/last_analysis_result.json") as f:
    data = json.load(f)

for pick in data.get("top_picks", []):
    price_pred = pick.get("price_prediction", {})
    cp = price_pred.get('current_price', 1)
    predictions = price_pred.get("predictions", {})
    day_5 = predictions.get("day_5", {})
    day_5_price = day_5.get("price", cp)
    
    try:
        pred_return = ((float(day_5_price) - float(cp)) / float(cp)) * 100
    except (ValueError, TypeError, ZeroDivisionError) as e:
        pred_return = 0.0
        print("Exception:", e)
        
    print(f"{pick.get('ticker')}: cp={cp}, day_5={day_5_price}, ret={pred_return}")
