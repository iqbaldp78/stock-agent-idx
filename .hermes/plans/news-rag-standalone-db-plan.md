# News RAG (Standalone Vector DB) Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Build a Retrieval-Augmented Generation (RAG) pipeline to ingest Stockbit news using a **completely separate and isolated** Vector Database to guarantee zero disruption to the existing system.

**Architecture:** 
- New Vector DB: A separate container `vector_postgres` running `pgvector/pgvector:pg16` on port `5122`.
- Main DB: Untouched (`stock_postgres` on port `5121`).
- Ingestion: Standalone python script hitting Stockbit API, generating summary & embeddings via `9router` (local LLM proxy at `172.18.0.1:20128`), and saving to `vector_postgres`.
- Retrieval: Dedicated python module that queries `vector_postgres` to fetch context for the LLM during stock evaluation.

**Tech Stack:** `pgvector`, SQLAlchemy / psycopg2, requests, `9router` (Local AI Gateway).

---

### Task 1: Add Standalone Vector DB to Docker Compose

**Objective:** Add a new `vector_postgres` service and its associated volume without modifying any existing services.

**Files:**
- Modify: `docker-compose.yml`

**Step 1: Write modification**
Append the following service and volume to `docker-compose.yml`:
```yaml
  vector_postgres:
    image: pgvector/pgvector:pg16
    container_name: vector_postgres
    restart: always
    environment:
      POSTGRES_DB: vectoragent
      POSTGRES_USER: vectoruser
      POSTGRES_PASSWORD: vectorpassword
    ports:
      - "5122:5432"
    volumes:
      - vector_postgres_data:/var/lib/postgresql/data
      - ./db/vector_migrations:/docker-entrypoint-initdb.d
    networks:
      - stock_net

# Inside volumes section, add:
  vector_postgres_data:
```

**Step 2: Apply and verify**
Run: `mkdir -p ./db/vector_migrations`
Run: `docker compose up -d vector_postgres` (this only spins up the new container)
Run: `docker ps | grep vector_postgres`
Expected: Container `vector_postgres` is running on port 5122.

**Step 3: Commit**
```bash
git add docker-compose.yml
git commit -m "feat(infra): add standalone vector_postgres container for RAG"
```

---

### Task 2: Create Vector Database Schema

**Objective:** Create a new table `news_signals` inside the new `vector_postgres` database.

**Files:**
- Create: `db/vector_migrations/001_init.sql`

**Step 1: Write schema SQL**

```sql
-- Enable vector extension
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS news_signals (
    id SERIAL PRIMARY KEY,
    stream_id BIGINT UNIQUE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    content TEXT NOT NULL,
    summary TEXT,
    sentiment VARCHAR(50),
    impact_scope VARCHAR(50),
    tickers JSONB,
    embedding vector(1536) -- Matches OpenAI text-embedding-3-small dimension
);

-- Index for faster cosine distance similarity search
CREATE INDEX ON news_signals USING hnsw (embedding vector_cosine_ops);
```

**Step 2: Run migration**
Because we mounted `./db/vector_migrations` to `/docker-entrypoint-initdb.d`, it will auto-run on first startup. To apply manually if already started:
Run: `cat db/vector_migrations/001_init.sql | docker exec -i vector_postgres psql -U vectoruser -d vectoragent`
Expected: `CREATE EXTENSION`, `CREATE TABLE` and `CREATE INDEX` success messages.

**Step 3: Commit**
```bash
git add db/vector_migrations/001_init.sql
git commit -m "feat(db): schema for news_signals in vector database"
```

---

### Task 3: Build the Stockbit Ingestion & Embedding Script

**Objective:** Create a script that fetches data, calls `9router` for LLM summary + embedding, and inserts strictly into the new DB.

**Files:**
- Create: `scripts/news_ingester.py`

**Step 1: Write the script**

```python
import os
import requests
import psycopg2
import json
from datetime import datetime

STOCKBIT_URL = "https://exodus.stockbit.com/stream/v3/user/Stockbit"
# Ensure we have the token in our env
STOCKBIT_TOKEN = os.getenv("STOCKBIT_TOKEN", "")
NINE_ROUTER_URL = "http://172.18.0.1:20128/v1"

def fetch_stockbit_news():
    headers = {
        'Authorization': f'Bearer {STOCKBIT_TOKEN}',
        'User-Agent': 'Mozilla/5.0'
    }
    resp = requests.post(STOCKBIT_URL, headers=headers, data='')
    return resp.json().get('data', {}).get('stream', []) if resp.status_code == 200 else []

def get_analysis_and_embedding(text):
    # 1. Summary & Sentiment Extraction
    chat_payload = {
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "system", "content": "You are a financial analyst."},
            {"role": "user", "content": f"Extract JSON (summary, sentiment: POSITIVE/NEGATIVE/NEUTRAL, tickers: list) from: {text}"}
        ],
        "temperature": 0.1
    }
    chat_resp = requests.post(f"{NINE_ROUTER_URL}/chat/completions", json=chat_payload).json()
    
    # Safely parse JSON from LLM response (simplified here)
    clean_json = chat_resp['choices'][0]['message']['content'].replace("```json", "").replace("```", "").strip()
    analysis = json.loads(clean_json)

    # 2. Generate Embedding
    embed_payload = {
        "model": "text-embedding-3-small", 
        "input": analysis['summary']
    }
    embed_resp = requests.post(f"{NINE_ROUTER_URL}/embeddings", json=embed_payload).json()
    embedding = embed_resp['data'][0]['embedding']
    
    return analysis, embedding

def save_to_vector_db(stream_id, content, analysis, embedding):
    # Connects EXCLUSIVELY to the new vector DB (port 5122)
    conn = psycopg2.connect(
        dbname="vectoragent", user="vectoruser", password="vectorpassword", host="localhost", port=5122
    )
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO news_signals (stream_id, content, summary, sentiment, tickers, embedding)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (stream_id) DO NOTHING
    """, (stream_id, content, analysis.get('summary'), analysis.get('sentiment'), json.dumps(analysis.get('tickers', [])), embedding))
    conn.commit()
    cur.close()
    conn.close()

if __name__ == "__main__":
    news = fetch_stockbit_news()
    for item in news[:5]: # Process 5 at a time
        try:
            analysis, emb = get_analysis_and_embedding(item['content'])
            save_to_vector_db(item['stream_id'], item['content'], analysis, emb)
            print(f"Ingested {item['stream_id']}")
        except Exception as e:
            print(f"Error processing {item['stream_id']}: {e}")
```

**Step 2: Test script logic**
Run: Execute script manually with dummy token to verify it doesn't crash.

**Step 3: Commit**
```bash
git add scripts/news_ingester.py
git commit -m "feat(rag): add news ingestion script pointing to vector DB"
```

---

### Task 4: Create Retrieval Module

**Objective:** Write the vector similarity search function that connects to the new DB to fetch context.

**Files:**
- Create: `src/rag_retriever.py`

**Step 1: Write retrieval function**

```python
import psycopg2

def get_relevant_news(query_embedding, limit=3):
    """Fetch top K news related to the query vector from vector_postgres."""
    # Read-only connection to vector_postgres (port 5122)
    conn = psycopg2.connect(
        dbname="vectoragent", user="vectoruser", password="vectorpassword", host="localhost", port=5122
    )
    cur = conn.cursor()
    # <=> is the cosine distance operator in pgvector
    cur.execute("""
        SELECT summary, sentiment, tickers, created_at 
        FROM news_signals 
        ORDER BY embedding <=> %s::vector 
        LIMIT %s
    """, (query_embedding, limit))
    
    results = cur.fetchall()
    cur.close()
    conn.close()
    
    return [
        {"summary": r[0], "sentiment": r[1], "tickers": r[2], "date": r[3]} 
        for r in results
    ]
```

**Step 2: Commit**
```bash
git add src/rag_retriever.py
git commit -m "feat(rag): vector similarity search retriever"
```

---

### Task 5: Integrate Context into Existing Pipeline (Safe Read-Only)

**Objective:** Safely inject the retrieved news context into the agent's prompt during evaluation, wrapping it in try-except so if it fails, the old logic still runs.

**Files:**
- Modify: `src/agent_evaluator.py` (or existing LLM logic)

**Step 1: Write integration code**

```python
# In your existing evaluation logic, import the retriever
try:
    from src.rag_retriever import get_relevant_news
    import requests
    NINE_ROUTER_URL = "http://172.18.0.1:20128/v1"
    
    # 1. Get embedding for the query
    embed_payload = {"model": "text-embedding-3-small", "input": f"News about {ticker}"}
    query_embedding = requests.post(f"{NINE_ROUTER_URL}/embeddings", json=embed_payload).json()['data'][0]['embedding']
    
    # 2. Retrieve from vector_postgres
    news_context = get_relevant_news(query_embedding)
    context_str = "\n".join([f"- {n['summary']} (Sentiment: {n['sentiment']})" for n in news_context])
except Exception as e:
    print(f"RAG fetch failed, proceeding without news: {e}")
    context_str = "No recent news found."

# Append to existing prompt
prompt = f"""
{existing_prompt}

Recent Market Catalysts (News):
{context_str}
"""
```

**Step 2: Commit**
```bash
git add src/agent_evaluator.py
git commit -m "feat(agent): safe read-only injection of news context"
```
