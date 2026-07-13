"""
Run analysis untuk single ticker untuk testing end-to-end.
"""
import sys
from datetime import date, datetime
from db import SessionLocal
from graph.workflow import run_full_analysis
from db.tracker import save_full_result

def run_single_ticker_analysis(ticker: str = "BBCA"):
    """Run full analysis untuk single ticker."""
    try:
        print(f"\n{'='*60}")
        print(f"Running analysis for ticker: {ticker}")
        print(f"{'='*60}\n")
        
        # Run workflow untuk single ticker
        result = run_full_analysis(universe=[ticker])
        
        if not result:
            print(f"❌ Workflow failed for {ticker}")
            return False
        
        print(f"\n--- Workflow Results ---")
        print(f"Top picks: {len(result.get('top_picks', []))}")
        print(f"Debate logs: {len(result.get('debate_log', []))}")
        print(f"Composites: {len(result.get('composites', {}))}")
        
        # Save hasil ke database
        print(f"\n--- Saving to Database ---")
        save_full_result(result)
        print(f"✓ Data saved successfully")
        
        # Verify data di database
        print(f"\n--- Verifying Database ---")
        db = SessionLocal()
        from db.models import Signal, AgentScore
        
        today = datetime.now()
        signals = db.query(Signal).filter(
            Signal.run_date == today,
            Signal.ticker == ticker
        ).all()
        
        scores = db.query(AgentScore).filter(
            AgentScore.run_date == today,
            AgentScore.ticker == ticker
        ).all()
        
        print(f"Signals saved: {len(signals)}")
        if signals:
            sig = signals[0]
            print(f"  - Ticker: {sig.ticker}")
            print(f"  - Signal: {sig.signal}")
            print(f"  - Target 1: {sig.target_1}")
            print(f"  - Target 2: {sig.target_2}")
            print(f"  - Target 3: {sig.target_3}")  # Test kolom baru
            print(f"  - TP Position Sizing: {sig.tp_position_sizing}")
        
        print(f"Scores saved: {len(scores)}")
        if scores:
            score = scores[0]
            print(f"  - Ticker: {score.ticker}")
            print(f"  - Composite Score: {score.composite_score}")
        
        db.close()
        
        print(f"\n✅ End-to-end test SUCCESSFUL for {ticker}!")
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    ticker = sys.argv[1] if len(sys.argv) > 1 else "BBCA"
    success = run_single_ticker_analysis(ticker)
    sys.exit(0 if success else 1)
