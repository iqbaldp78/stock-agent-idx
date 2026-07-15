import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from agents.investment_manager import _build_pick_rule_based

scores = {"TEST": {"fundamental": {"score": 10}, "technical": {"score": 10}, "bandarm": {"score": 10}}}
composites = {"TEST": {"ticker": "TEST", "final_score": 10}}
ml_predictions = {"TEST": {"signal": "STRONG BUY", "confidence": "HIGH"}}
macro_data = {"ihsg_trend": "UP", "ihsg_price": 7000}

pick = _build_pick_rule_based(
    rank=1,
    ticker="TEST",
    finalist={"ticker": "TEST", "final_score": 10},
    scores=scores,
    composites=composites,
    macro_data=macro_data,
    ml_predictions=ml_predictions,
)
print("price_prediction in pick:", "price_prediction" in pick)
if "price_prediction" in pick:
    print("price_prediction:", pick["price_prediction"])
