# MoodRoute

AI travel workspace: turn screenshots, article links, and place names into a structured knowledge base and explainable multi-agent itineraries.

## Stack

- **Frontend:** TanStack Start + React (`frontend/`)
- **Backend:** FastAPI + LangGraph + SQLite + ChromaDB + FastEmbed (`backend/`)
- **Ingest (local):** Ollama vision + text models (screenshots, articles, place lookup)
- **Polish (optional):** GigaChat text — place cards and route narrative
- **Search:** Tavily (optional — place lookup and verification)
- **Map:** Leaflet + OpenStreetMap

## Quick start

### 1. Backend

```bash
cd backend
python3 -m pip install -r requirements.txt
cp .env.example .env
# Add GIGACHAT_CREDENTIALS and TAVILY_API_KEY if available

python3 -m uvicorn app.main:app --reload --port 8000
```

Seed runs automatically on startup (Japan Autumn / Tokyo demo data).

### 2. Ollama (recommended for ingest)

```bash
docker compose up -d ollama
docker exec -it $(docker compose ps -q ollama) ollama pull llama3.2-vision:11b
docker exec -it $(docker compose ps -q ollama) ollama pull qwen2.5:7b
```

Requires ~8GB VRAM for `llama3.2-vision:11b`. On weaker hardware, set `OLLAMA_VISION_MODEL=moondream` in `.env`.

### 3. Frontend

```bash
cd frontend
cp .env.example .env
npm install --legacy-peer-deps
npm run dev
```

Open http://localhost:5173

Set `VITE_USE_MOCK=true` in `.env` to run UI without backend.

## Demo script (defense)

1. **Inbox** — paste article URL + upload café screenshot + type place name (e.g. Fuglen Tokyo)
2. **Agent Activity** — Curator → Researcher → Verifier timeline
3. **Review Queue** — Confirm / Merge duplicate / Edit low-confidence
4. **Places** — filter Coffee Culture, semantic search in topbar
5. **Trip Builder** — 4 days, Aesthetic, Relaxed → Generate Itinerary
6. **Route Planner** — day tabs + Leaflet map + Sources Used (Aesthetic Mode ON)

## Architecture

```
User → TanStack UI → REST API → LangGraph Supervisor
                              → Curator (Ollama ingest)
                              → GigaChat text (place cards)
                              → Researcher (Tavily + Nominatim + RAG)
                              → Planner (geo clustering + GigaChat narrative)
                              → Verifier (duplicates + HITL queue)
```

## API docs

http://localhost:8000/docs
