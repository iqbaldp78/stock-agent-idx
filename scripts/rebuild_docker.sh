#!/usr/bin/env bash
# Rebuild images setelah requirements.txt berubah (mis. langchain-openai).
set -euo pipefail
cd "$(dirname "$0")/.."

echo "Building app + streamlit images..."
docker build -f Dockerfile.app -t stock-agent-idx-app .
docker build -f Dockerfile.streamlit -t stock-agent-idx-streamlit .

echo "Recreating containers..."
docker compose up -d --force-recreate app streamlit

echo "Verifying langchain-openai..."
docker exec stock_app python -c "from langchain_openai import ChatOpenAI; print('app: OK')"
docker exec stock_streamlit python -c "from langchain_openai import ChatOpenAI; print('streamlit: OK')"
echo "Done."
