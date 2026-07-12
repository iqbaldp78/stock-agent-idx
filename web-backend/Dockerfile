FROM python:3.11-slim

WORKDIR /app

# Install standard dependencies first
COPY requirements.txt ./root_requirements.txt
COPY web-backend/requirements.txt ./web_requirements.txt
RUN pip install --no-cache-dir -r root_requirements.txt -r web_requirements.txt

# Copy source folders
COPY config.py .
COPY agents/ ./agents/
COPY data/ ./data/
COPY db/ ./db/
COPY graph/ ./graph/
COPY portfolio/ ./portfolio/
COPY services/ ./services/

# Copy web-backend source files
COPY web-backend/main.py .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
