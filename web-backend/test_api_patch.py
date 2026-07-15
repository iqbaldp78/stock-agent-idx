import re
with open("web-backend/main.py", "r") as f:
    content = f.read()

# Replace the previous block we appended
new_content = content.replace('def get_ai_performance_metrics(current_user: dict = Depends(get_current_user)):', 'def get_ai_performance_metrics():')

with open("web-backend/main.py", "w") as f:
    f.write(new_content)
