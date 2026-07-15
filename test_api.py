from fastapi import FastAPI, Depends
from fastapi.testclient import TestClient

import sys
sys.path.append("web-backend")
from main import app, get_current_user

print("Registered Routes:")
for route in app.routes:
    print(route.path)

