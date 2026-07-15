import re
with open("web-backend/main.py", "r") as f:
    content = f.read()

# Check if app is passed correctly
# The indentation might be off for the @app decorator, let's fix that.
content = content.replace('\ndef get_ai_performance', '\n@app.get("/api/ai/performance-metrics")\ndef get_ai_performance')

# Clean up duplicate decorators if they exist
content = content.replace('@app.get("/api/ai/performance-metrics")\n@app.get("/api/ai/performance-metrics")', '@app.get("/api/ai/performance-metrics")')

with open("web-backend/main.py", "w") as f:
    f.write(content)
