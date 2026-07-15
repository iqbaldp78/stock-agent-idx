import re
with open("web-backend/main.py", "r") as f:
    content = f.read()

# FastAPI router mounts in main.py? Let's check how many @app.get there are and where they stop loading
lines = content.split('\n')
for i, line in enumerate(lines):
    if 'def get_ai_performance_metrics_real' in line:
        print(f"Function starts at line {i+1}")
        
