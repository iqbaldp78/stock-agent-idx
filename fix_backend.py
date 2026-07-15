import re
with open("web-backend/main.py", "r") as f:
    content = f.read()

# Make it accept current_user properly via auth router instead of globally bypassing it
target = """@app.get("/api/ai/performance-metrics")
def get_ai_performance_metrics():
    user_id = current_user.get("user_id")"""

replacement = """@app.get("/api/ai/performance-metrics")
def get_ai_performance_metrics(current_user: dict = Depends(get_current_user)):
    user_id = current_user.get("user_id")"""

content = content.replace(target, replacement)
content = content.replace('app.include_router(performance_router)\n', '')

with open("web-backend/main.py", "w") as f:
    f.write(content)
