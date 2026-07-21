import logging
import json
from datetime import datetime
from db import SessionLocal
from db.models import Universe
from agents.bandarmologi import analyze as analyze_bandar
from agents.technical import analyze as analyze_technical
from agents.ihsg_predictor import predict_ihsg
from agents.llm_client import invoke_json_im
from config import LLM_MODEL_INVESTMENT_MANAGER, LLM_ENABLED

logger = logging.getLogger(__name__)

def run_konglo_screen():
    db = SessionLocal()
    tickers = db.query(Universe.ticker).filter_by(is_konglo=True, active=True).all()
    db.close()
    
    tickers = [t[0] for t in tickers]
    
    if not tickers:
        return {"status": "error", "message": "No active Konglo Play tickers found in universe."}
    
    # 1. Analyze IHSG
    try:
        ihsg_res = predict_ihsg()
        market_direction = ihsg_res.get("direction", "SIDEWAYS")
    except Exception as e:
        logger.error(f"Error fetching IHSG: {e}")
        market_direction = "SIDEWAYS"
    market_is_bearish = (market_direction == "BEARISH")
    
    results = []
    
    for ticker in tickers:
        logger.info(f"[Konglo Screener] Analyzing {ticker}")
        try:
            # 2. Gather data for ticker
            tech_res = analyze_technical(ticker)
            bandar_res = analyze_bandar(ticker)
            fund_res = {"score": 5.0, "status": "skipped", "analysis": "Fundamental diabaikan untuk Konglo Play."}
            
            # Fetch news from local RAG database
            try:
                from scripts.rag_retriever import search_by_ticker, format_for_prompt
                raw_news = search_by_ticker(ticker, limit=5)
                news_res = {
                    "news_count": len(raw_news),
                    "formatted_news": format_for_prompt(raw_news)
                }
            except Exception as e:
                logger.error(f"Error fetching local RAG news for {ticker}: {e}")
                news_res = {
                    "news_count": 0,
                    "formatted_news": "No news available due to error."
                }
            
            # 3. Score weighting
            # Konglo weights: Tech 45%, Bandar 45%, Fund 10%
            tech_score = tech_res.get("score", 5.0)
            bandar_score = bandar_res.get("score", 5.0)
            fund_score = fund_res.get("score", 5.0)
            
            base_score = (tech_score * 0.45) + (bandar_score * 0.45) + (fund_score * 0.10)
            
            # 4. Bearish penalty
            final_score = base_score
            if market_is_bearish:
                final_score = max(0.0, final_score - 1.5) # Penalty
                
            # 5. Generate LLM Narrative & Thesis
            narrative = "LLM disabled or error."
            thesis = ""
            if LLM_ENABLED:
                system_prompt = "You are a highly aggressive 'Konglo Play' stock screener focusing on fast-gains. Write all responses (narrative and thesis) strictly in Indonesian (Bahasa Indonesia)."
                user_prompt = f"""
                Evaluate the ticker {ticker} strictly focusing on Technical Setup, Bandarmology (Flow of Funds), and recent News.
                Fundamental data is provided but should be heavily discounted in favor of momentum.
                The broader market (IHSG) is currently {market_direction}.
                
                Data:
                Technical: {json.dumps(tech_res, default=str)}
                Bandarmology: {json.dumps(bandar_res, default=str)}
                News: {json.dumps(news_res, default=str)}
                Fundamentals: {json.dumps(fund_res, default=str)}
                Final Weighted Score: {final_score:.2f}
                
                Return JSON with:
                "narrative": "A punchy, 2-sentence narrative on why this stock is moving or might move fast. Must be in Indonesian.",
                "thesis": "A bulleted list (string) of the core thesis focusing on breakout setups and broker accumulation. Must be in Indonesian.",
                "confidence": "HIGH", "MEDIUM", or "LOW" based on the data and market direction.
                """
                
                llm_res = invoke_json_im(LLM_MODEL_INVESTMENT_MANAGER, system_prompt, user_prompt)
                if llm_res and isinstance(llm_res, dict):
                    narrative = llm_res.get("narrative", narrative)
                    thesis = llm_res.get("thesis", thesis)
                    confidence = llm_res.get("confidence", "LOW")
                else:
                    confidence = "LOW"
            else:
                confidence = "LOW" if final_score < 5 else "MEDIUM"
                
            results.append({
                "ticker": ticker,
                "score": final_score,
                "tech_score": tech_score,
                "bandar_score": bandar_score,
                "fund_score": fund_score,
                "narrative": narrative,
                "thesis": thesis,
                "confidence": confidence,
                "ihsg_status": market_direction
            })
            
        except Exception as e:
            logger.error(f"Error screening {ticker} for Konglo Play: {e}")
            results.append({
                "ticker": ticker,
                "score": 0,
                "error": str(e)
            })
            
    # Sort by highest score
    results = sorted(results, key=lambda x: x.get("score", 0), reverse=True)
    
    return {
        "status": "success",
        "market_direction": market_direction,
        "results": results
    }
