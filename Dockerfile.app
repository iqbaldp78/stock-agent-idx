FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
# Run migrations before starting the scheduler using shell form
CMD ["/bin/sh", "-c", "alembic upgrade head && python scheduler.py"]
