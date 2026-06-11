# 🗺️ MoodRoute

**An aesthetic-first AI workspace for travelers.**  
Turns Instagram screenshots, article links, and place names into a structured knowledge base — and builds an explainable itinerary from it using a multi-agent system.

> *"Saved 47 coffee shop screenshots in Tokyo — but how do I turn them into a proper 4-day route?"*  
> MoodRoute solves exactly that.

---

## 💡 Why It Matters

Trip planning today looks like this: dozens of tabs, screenshots in your camera roll, notes scattered across apps, duplicate recommendations for the same places, and zero clarity on *where* a suggestion came from. It's especially painful when you care about more than logistics — **mood** matters: minimalism, slow travel, architecture, coffee culture.

**MoodRoute closes this gap:**

| Problem | MoodRoute Solution |
|---|---|
| Inspiration scattered across screenshots and links | **Inbox** — one entry point: photo, article, or place name |
| AI "invents" places that don't exist | **Verifier Agent** + HITL queue: confirm, merge duplicates, edit |
| Keyword search can't understand "cozy minimalist café" | **RAG** on ChromaDB — semantic search by aesthetic tags |
| Itinerary ignores neighborhoods and mood | **Planner Agent** — geo-clustering + styles (Aesthetic, Coffee Crawl…) + **Aesthetic Mode** |
| Unclear what the AI is doing under the hood | **Agent Activity** — transparent timeline: Curator → Researcher → Verifier → Planner |

---

## 🌍 Language

The **UI, API, and documentation are in English**. The ingest pipeline still understands **multilingual inspiration** — screenshots and articles with Russian, Chinese, or English overlay text are parsed and normalized into English place cards. Cyrillic location aliases (e.g. «Токио» → Tokyo) are kept in the backend for input normalization, not for UI display.

---

## ✨ Features

### 📥 Inspiration Inbox
Upload a coffee shop screenshot, paste an article link (Wikipedia, blog), or simply type *"Fuglen Tokyo"*. Agents process everything in the background — you see progress in real time.

### 🏛️ Places — Living Knowledge Base
Place cards with categories, aesthetic tags, verification level, and notes. Filters, drag-and-drop sorting, semantic search in the top bar. Every place knows where it came from: screenshot, article, RAG, or manual input.

### ✅ Review Queue (Human-in-the-Loop)
Low confidence? Duplicate Blue Bottle? The Verifier agent sends the card for your review: **Confirm**, **Merge**, **Edit**, or **Reject**. The database stays clean without full manual entry.

### 🛠️ Trip Builder
Set duration, style (*Efficient*, *Aesthetic*, *Hidden Gems*, *Coffee Crawl*…), moods (*Minimal*, *Slow Travel*, *Neon*…), and intensity. The Supervisor Agent coordinates Planner and Verifier — the route is built from *your* saved places, not thin air.

### 🧭 Route Planner
Days with LLM-generated themes, numbered stops, a Leaflet map with route lines, source and verification badges. In **Aesthetic Mode** — poetic mood labels like *"Slow Morning Coffee → Golden Hour Walk"*.

### 🤖 Agent Activity
Side panel with a full timeline: which agent did what, with what confidence, which tools were used. Fallback statuses are shown explicitly — no black box.

---

## 🎨 Design

The interface follows an **editorial travel aesthetic**: warm cream palette, terracotta accent, **Fraunces** for headings and **Inter** for UI. Components built with **shadcn/ui** + **Radix**, animations via **tw-animate-css**.

- **Aesthetic Mode** toggle in the top bar — changes the atmosphere across the app
- Color-coded agents (Supervisor, Curator, Researcher, Planner, Verifier)
- Responsive layout: sidebar + agent panel on desktop, drawer on mobile
- Maps: **Leaflet** + OpenStreetMap

---

## 🏗️ Architecture

```
User
    │
    ▼
TanStack Start UI  ──REST──▶  FastAPI
                                  │
                    ┌─────────────┼─────────────┐
                    ▼             ▼             ▼
              Ingest Pipeline  Trip Graph   RAG Search
              (LangGraph)      (LangGraph)  (ChromaDB)
                    │             │
         Curator ───┤             ├── Planner
         Researcher ┤             └── Verifier
         Verifier ──┘
                    │
         Ollama (vision + text)  ·  GigaChat (cards, narrative)
         Tavily (search)          ·  Nominatim (geocoding)
         EasyOCR (fallback OCR)  ·  SQLite (data)
```

**Ingest pipeline** (each upload):  
`Supervisor → Curator → Researcher → Verifier → Review Queue / Places`

**Trip generation**:  
`Supervisor → Planner → Verifier → Route Planner`

---

## 🧰 Stack

| Layer | Technologies |
|---|---|
| **Frontend** | TanStack Start · React 19 · TanStack Router · TanStack Query · Tailwind CSS 4 · shadcn/ui · Leaflet · dnd-kit |
| **Backend** | FastAPI · LangGraph · SQLAlchemy · SQLite |
| **RAG** | ChromaDB · FastEmbed |
| **Ingest (local)** | Ollama — vision model for screenshots, text model for articles |
| **Polish (optional)** | GigaChat — place cards and route narrative |
| **Search & verification** | Tavily · Nominatim · EasyOCR |
| **Infra** | Docker Compose (Ollama) |

---

## 🚀 Quick Start

### 1. Backend

```bash
cd backend
python3 -m pip install -r requirements.txt
cp .env.example .env
# If available — add GIGACHAT_CREDENTIALS and TAVILY_API_KEY

python3 -m uvicorn app.main:app --reload --port 8000
```

On startup, a demo workspace **Japan Autumn** is seeded automatically (12 places in Tokyo).

### 2. Ollama (recommended for ingest)

**Option A — Docker (local development)**

```bash
docker compose up -d ollama
docker exec -it $(docker compose ps -q ollama) ollama pull llama3.2-vision:11b
docker exec -it $(docker compose ps -q ollama) ollama pull qwen2.5:7b
```

In `backend/.env` (defaults from `.env.example`):

```env
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_VISION_MODEL=llava:7b
OLLAMA_TEXT_MODEL=qwen2.5:7b
```

`llama3.2-vision:11b` requires ~8 GB VRAM. On weaker hardware: `OLLAMA_VISION_MODEL=moondream`.

**Option B — remote Ollama on LAN**

```env
OLLAMA_BASE_URL=http://192.168.1.248:11434
OLLAMA_VISION_MODEL=gemma4:12b
OLLAMA_TEXT_MODEL=gemma4:e4b
```

On the Ollama host: `OLLAMA_HOST=0.0.0.0`, open port `11434`, pull models from `.env`.

### 3. Frontend

```bash
cd frontend
cp .env.example .env
npm install --legacy-peer-deps
npm run dev
```

Open http://localhost:5173

`VITE_USE_MOCK=true` in `.env` — UI without backend (demo data).

---

## 🎬 Demo Scenario (Project Defense)

1. **Inbox** — article + coffee shop screenshot + place name → watch Agent Activity
2. **Review Queue** — merge duplicate, Confirm / Edit low-confidence items
3. **Places** — Coffee Culture filter, semantic search *"minimal café"*
4. **Trip Builder** — 4 days, Aesthetic, Relaxed → Generate Itinerary
5. **Route Planner** — day tabs, map, Sources Used, Aesthetic Mode ON

### Fallback Without API Keys

| Missing | What Happens |
|---|---|
| GigaChat | Heuristic cards and default day themes |
| Tavily | Place search → Unverified status |
| Ollama | Screenshots/articles → Review Queue with low confidence |

Agent Activity shows **Fallback** status explicitly.

---

## 📡 API

Interactive documentation: http://localhost:8000/docs

---

## 📁 Project Structure

```
mood-route/
├── backend/          # FastAPI, agents, RAG, ingest pipeline
│   ├── app/agents/   # Curator, Researcher, Verifier, Planner, graph
│   ├── app/rag/      # ChromaDB + embeddings
│   └── scripts/      # seed_japan.py — demo data
├── frontend/         # TanStack Start + React UI
│   └── src/routes/   # Inbox, Places, Trip Builder, Route Planner, Review
└── docker-compose.yml
```

---

*MoodRoute — final course project. From inspiration to itinerary — with transparent AI and aesthetics in every detail.*
