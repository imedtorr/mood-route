# MoodRoute — Demo Script

## Prerequisites

- Backend on `:8000`, frontend on `:5173`
- Workspace: **Japan Autumn** (seeded with 12 Tokyo places)

## Flow (5–7 minutes)

### 1. Inspiration Inbox

- Paste URL: `https://en.wikipedia.org/wiki/Yanaka,_Tokyo`
- Note: "hidden neighborhood walk"
- Upload a café screenshot (drag-drop)
- Show **Agent Activity**: Supervisor → Curator → Researcher

### 2. Review Queue (HITL)

- **Merge Duplicate**: Blue Bottle pair
- **Confirm** or **Edit** a low-confidence item
- Explain: Verifier Agent keeps KB clean

### 3. Places Knowledge Base

- Filter: **Coffee Culture**, **Verified**
- Topbar search: `minimal café`
- Show RAG semantic match (not just keywords)

### 4. Trip Builder

- 4 days, **Aesthetic**, moods: Minimal + Slow Travel
- **Relaxed** intensity
- Toggle **Aesthetic Mode** ON
- Click **Generate Itinerary** → Supervisor orchestrates Planner + Verifier

### 5. Route Planner

- Day tabs with themes (Slow Morning, Neon Evening…)
- **Leaflet map** with numbered pins + route line
- **Sources used**: saved / RAG / verified / review counts
- Each stop: reason + verification badge + mood label

## Fallback demo (no API keys)

- Without GigaChat/Tavily: heuristic extraction + Unverified flags still work
- Without Ollama: screenshot → Review Queue with low confidence
- Agent Activity shows **Fallback** status explicitly
