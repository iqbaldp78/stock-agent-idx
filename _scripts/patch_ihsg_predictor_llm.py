import re

with open('/home/hamboo/my-product/stock-agent-idx/agents/ihsg_predictor.py', 'r') as f:
    content = f.read()

# 1. Add imports at the top
import_block = """from config import LLM_ENABLED
from agents.macro import analyze as macro_analyze"""

new_import_block = """from config import LLM_ENABLED
from agents.macro import analyze as macro_analyze
from agents.llm_client import invoke_json_im
from config import LLM_MODEL_INVESTMENT_MANAGER, LLM_MODEL_IM_FALLBACK
from agents.debate.personas import IM_SYSTEM_PROMPT
import json"""

content = content.replace(import_block, new_import_block)

# 2. Add LLM generation function before predict_ihsg
llm_func = """
def _generate_narrative_with_llm(direction: str, confidence: str, combined_score: float, 
                               momentum: float, breadth: float, macro: float, sector: float, 
                               d1_pct: float, current_price: float, usdidr: float, 
                               recent_news: list) -> dict:
    \"\"\"Call LLM to generate reasoning, drivers, and risks based on calculated scores.\"\"\"
    if not LLM_ENABLED:
        return None
        
    try:
        # Build News String
        news_text = ""
        if recent_news:
            news_items = []
            for n in recent_news:
                title = n.get('summary', '').replace('\\n', ' ')
                sent = n.get('sentiment', 'Neutral')
                news_items.append(f"- [{sent}] {title}")
            news_text = "Berita Terbaru:\\n" + "\\n".join(news_items)
            
        context = {
            "prediksi_arah": direction,
            "tingkat_keyakinan": confidence,
            "skor_gabungan": round(combined_score, 2),
            "target_besok": f"{d1_pct:+.2f}%",
            "metrik": {
                "market_breadth_score": round(breadth, 2),
                "momentum_score": round(momentum, 2),
                "macro_score": round(macro, 2),
                "sector_score": round(sector, 2)
            },
            "data_tambahan": {
                "ihsg_sekarang": current_price,
                "usd_idr": usdidr
            }
        }
        
        user_prompt = f\"\"\"Tugas: Buat analisis pergerakan IHSG untuk 1 minggu ke depan berdasarkan metrik matematis berikut.
Kamu harus menjelaskan MENGAPA algoritma memprediksi arah {direction} dengan meninjau skor komponennya (Breadth paling dominan 60%, Momentum 25%).
Gunakan bahasa analis profesional dalam Bahasa Indonesia (Investment Manager).

Data Sistem:
{json.dumps(context, indent=2)}

{news_text}

Output dalam JSON format saja (tanpa markdown blok):
{{
    "reasoning": "Opini analis singkat (2-3 kalimat max) menjelaskan sentimen teknikal dan makro IHSG.",
    "key_drivers": ["poin katalis 1", "poin katalis 2"],
    "risks": ["poin risiko 1", "poin risiko 2"]
}}
\"\"\"
        
        raw = invoke_json_im(
            LLM_MODEL_INVESTMENT_MANAGER,
            IM_SYSTEM_PROMPT,
            user_prompt,
            fallback_model=LLM_MODEL_IM_FALLBACK
        )
        return raw
    except Exception as e:
        logger.warning(f"Failed to generate LLM narrative: {e}")
        return None
"""

# Insert right before predict_ihsg
content = content.replace("def predict_ihsg() -> dict:", llm_func + "\ndef predict_ihsg() -> dict:")

# 3. Modify the result building block to include LLM call
old_result_block = """        usdidr_for_display = macro_data.get("usdidr")
        if usdidr_for_display is None:
            usdidr_for_display = 15800.0

        # Build result
        result = {
            "current_price": round(current_price, 0),
            "confidence": confidence,
            "direction": direction,
            "volatility_level": "HIGH" if abs(daily_move_pct) > 1.5 else "MEDIUM" if abs(daily_move_pct) > 0.5 else "LOW",
            "component_scores": {
                "momentum": round(momentum_score, 2),
                "breadth": round(breadth_score, 2),
                "macro": round(macro_score, 2),
                "sectors": round(sector_score, 2),
                "combined": round(combined_score, 2),
                "news": round(news_sentiment_score, 2),
            },
            "reasoning": f"IHSG {direction}: Combined score {combined_score:.2f} ({confidence} confidence). "
                        f"Momentum={momentum_score:.2f}, Breadth={breadth_score:.2f}, "
                        f"Macro={macro_score:.2f}, Sectors={sector_score:.2f}",
            "key_drivers": _extract_drivers(momentum_score, breadth_score, macro_score, sector_score),
            "risks": _extract_risks(momentum_score, breadth_score, macro_score),
            "data_used": ["""

# Make sure we add "news" to component_scores safely since I patched the combined block earlier, 
# I'll just rewrite the whole dictionary construction to be safe.

new_result_block = """        usdidr_for_display = macro_data.get("usdidr")
        if usdidr_for_display is None:
            usdidr_for_display = 15800.0
            
        # Call LLM
        llm_narrative = _generate_narrative_with_llm(
            direction, confidence, combined_score,
            momentum_score, breadth_score, macro_score, sector_score,
            float(daily_move_pct), float(current_price), float(usdidr_for_display),
            recent_news if 'recent_news' in locals() else []
        )
        
        reasoning_text = f"IHSG {direction}: Combined score {combined_score:.2f} ({confidence} confidence). Momentum={momentum_score:.2f}, Breadth={breadth_score:.2f}"
        drivers_list = _extract_drivers(momentum_score, breadth_score, macro_score, sector_score)
        risks_list = _extract_risks(momentum_score, breadth_score, macro_score)
        
        if llm_narrative:
            reasoning_text = llm_narrative.get("reasoning", reasoning_text)
            drivers_list = llm_narrative.get("key_drivers", drivers_list)
            risks_list = llm_narrative.get("risks", risks_list)

        # Build result
        result = {
            "current_price": round(current_price, 0),
            "confidence": confidence,
            "direction": direction,
            "volatility_level": "HIGH" if abs(daily_move_pct) > 1.5 else "MEDIUM" if abs(daily_move_pct) > 0.5 else "LOW",
            "component_scores": {
                "momentum": round(momentum_score, 2),
                "breadth": round(breadth_score, 2),
                "macro": round(macro_score, 2),
                "sectors": round(sector_score, 2),
                "combined": round(combined_score, 2),
                "news": round(news_sentiment_score, 2) if 'news_sentiment_score' in locals() else 0.5,
            },
            "reasoning": reasoning_text,
            "key_drivers": drivers_list,
            "risks": risks_list,
            "data_used": ["""

content = content.replace(old_result_block, new_result_block)

# Sometimes old code block might be slightly different due to previous patch, so let's fallback to regex if plain replace fails
if new_result_block not in content:
    # Use regex to find the result dict and replace the reasoning fields
    pattern = re.compile(r'(\s*"reasoning"\s*:\s*f".*?",\s*"key_drivers"\s*:\s*_extract_drivers\(.*?\),\s*"risks"\s*:\s*_extract_risks\(.*?\),)', re.DOTALL)
    
    inject = """
            "reasoning": reasoning_text,
            "key_drivers": drivers_list,
            "risks": risks_list,"""
            
    # Also need to insert the LLM call before the result dict
    pattern_before_result = re.compile(r'(\s*result = {)')
    
    llm_call = """
        # Call LLM
        llm_narrative = _generate_narrative_with_llm(
            direction, confidence, combined_score,
            momentum_score, breadth_score, macro_score, sector_score,
            float(daily_move_pct), float(current_price), float(usdidr_for_display),
            recent_news if 'recent_news' in locals() else []
        )
        
        reasoning_text = f"IHSG {direction}: Combined score {combined_score:.2f} ({confidence} confidence)."
        drivers_list = _extract_drivers(momentum_score, breadth_score, macro_score, sector_score)
        risks_list = _extract_risks(momentum_score, breadth_score, macro_score)
        
        if llm_narrative:
            reasoning_text = llm_narrative.get("reasoning", reasoning_text)
            drivers_list = llm_narrative.get("key_drivers", drivers_list)
            risks_list = llm_narrative.get("risks", risks_list)
        \\1"""
        
    content = pattern_before_result.sub(llm_call, content)
    content = pattern.sub(inject, content)


with open('/home/hamboo/my-product/stock-agent-idx/agents/ihsg_predictor.py', 'w') as f:
    f.write(content)

