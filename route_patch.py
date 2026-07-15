import re
with open("web-backend/main.py", "r") as f:
    content = f.read()

# Make sure it's mounted!
content = content.replace('@app.get("/api/ai/performance-metrics")', 'app.include_router(performance_router)\n@app.get("/api/ai/performance-metrics")')

with open("web-backend/main.py", "w") as f:
    f.write(content)
