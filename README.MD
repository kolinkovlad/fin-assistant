## 🚀 Quick Start

> **Prerequisites**  
> * Docker + Docker Compose (or Podman) — for Redis  
> * Python 3.10+, Poetry (or pip) — for the app  
> * An OpenAI key with GPT-4o access

# 1 Clone repo
```bash
git clone https://github.com/your-org/fin-assistant.git
cd fin-assistant
```
# 2 Install Python deps
```bash
poetry install                 # or: pip install -r requirements.txt
```
# 3 Environment
```bash
cp .env.example .env           # fill in OPENAI_API_KEY
```
# 4 Start infrastructure (Redis)
```bash
docker compose up -d           # uses docker-compose.yml with redis:7-alpine
```
# …or, if you prefer a one-liner without compose:
```bash
# docker run -d --name redis -p 6379:6379 redis:7-alpine
```
# 5 Run the FastAPI server
```bash
poetry run uvicorn app.server.main:app --reload
```
# 6 Open the interactive API
open http://127.0.0.1:8000/docs

### 🧩 Session-ID & state persistence  
Every chat request must carry a **`session-id`** header (or query param).  
This opaque string keys two Redis namespaces:

| Redis key pattern            | Content                                               |
|------------------------------|-------------------------------------------------------|
| `message:{session-id}`       | Trimmed chat history (system, user, assistant, tool) |
| `tool:{session-id}`          | Last tool-call record (for **why?** / **recap**)      |

> **Postman tip**  Create an environment variable `session_id = {{$uuid}}`; Postman will auto-generate a fresh ID for each request.