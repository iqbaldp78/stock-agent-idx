import sys
import re

with open("web-backend/main.py", "r") as f:
    content = f.read()

if "@app.get(\"/api/trading/performance\")" in content:
    print("Endpoint already exists")
    sys.exit(0)

# Find where get_equity_history is defined
search_pattern = r"@app.get\(\"/api/trading/equity-history\"\)"
match = re.search(search_pattern, content)

if not match:
    print("Could not find insertion point")
    sys.exit(1)

new_endpoint = """@app.get("/api/trading/performance")
def get_trading_performance(current_user: dict = Depends(get_current_user)):
    service = PaperTradingService()
    service.user_id = current_user.get("user_id")
    try:
        res = service.get_performance_metrics()
        return {"status": "success", "data": res}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        service.session.close()

"""

content = content[:match.start()] + new_endpoint + content[match.start():]

with open("web-backend/main.py", "w") as f:
    f.write(content)

print("Endpoint added to web-backend/main.py")
