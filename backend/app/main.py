import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
import sys

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.routes import router
from app.config import settings
from app.db.database import SessionLocal, init_db
from app.services.ocr import warm_ocr_reader
from app.services.ollama import close_ollama_client, init_ollama_client

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.seed_japan import seed_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)
    Path(settings.chroma_path).mkdir(parents=True, exist_ok=True)
    Path("data").mkdir(parents=True, exist_ok=True)
    await init_ollama_client()
    await asyncio.to_thread(warm_ocr_reader)
    init_db()
    db = SessionLocal()
    try:
        seed_db(db)
    finally:
        db.close()
    yield
    await close_ollama_client()


app = FastAPI(title="MoodRoute API", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router)

if Path(settings.upload_dir).exists():
    app.mount("/api/uploads", StaticFiles(directory=settings.upload_dir), name="uploads")


@app.get("/")
def root():
    return {"service": "MoodRoute API", "docs": "/docs"}
