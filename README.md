# MoodRoute

AI travel workspace: transform Pinterest/Instagram inspiration into a structured knowledge base and explainable multi-agent itineraries.

## Stack

- **Frontend:** TanStack Start + React (`frontend/`)
- **Backend:** FastAPI + LangGraph + SQLite + ChromaDB + FastEmbed (`backend/`)
- **LLM:** GigaChat (optional — heuristic fallback without credentials)
- **Search:** Tavily (optional)
- **Vision/OCR:** Ollama + moondream (optional)
- **Map:** Leaflet + OpenStreetMap

## Quick start

### 1. Backend

```bash
cd backend
python3 -m pip install -r requirements.txt   # requires pip
cp .env.example .env
# Add GIGACHAT_CREDENTIALS and TAVILY_API_KEY if available

python3 -m uvicorn app.main:app --reload --port 8000
```

Seed runs automatically on startup (Japan Autumn / Tokyo demo data).

Optional Ollama:

```bash
docker compose up -d ollama
docker exec -it <ollama-container> ollama pull moondream
```

### 2. Frontend

```bash
cd frontend
cp .env.example .env
npm install --legacy-peer-deps
npm run dev
```

Open http://localhost:5173

Set `VITE_USE_MOCK=true` in `.env` to run UI without backend.

## Demo script (defense)

1. **Inbox** — paste article URL + upload café screenshot → watch pipeline statuses
2. **Agent Activity** — Curator → Researcher → Verifier timeline
3. **Review Queue** — Confirm / Merge duplicate / Edit low-confidence
4. **Places** — filter Coffee Culture, semantic search in topbar
5. **Trip Builder** — 4 days, Aesthetic, Relaxed → Generate Itinerary
6. **Route Planner** — day tabs + Leaflet map + Sources Used (Aesthetic Mode ON)

## Architecture

```
User → TanStack UI → REST API → LangGraph Supervisor
                              → Curator (Ollama + GigaChat)
                              → Researcher (Tavily + Nominatim + RAG)
                              → Planner (geo clustering + preferences)
                              → Verifier (duplicates + HITL queue)
```

## API docs

http://localhost:8000/docs
