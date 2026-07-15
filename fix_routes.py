import re
with open("web-backend/main.py", "r") as f:
    content = f.read()

# FastAPI routers in this file might be mounted incorrectly. Let's see if the file ends with app.include_router
print("Does it have include_router at the bottom?", "app.include_router" in content)
