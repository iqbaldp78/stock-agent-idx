#!/bin/bash
cd /home/iqbal/my-project/stock-engine-prediction-v2
source venv/bin/activate
cd web-backend
/usr/bin/python3 -m uvicorn main:app --host 0.0.0.0 --port 8000
