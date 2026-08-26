from fastapi import FastAPI

from app.comments.router import router as comments_router
from app.conflicts.router import router as conflicts_router
from app.entries.router import router as entries_router
from app.glance.router import router as glance_router
from app.highlights.router import router as highlights_router
from app.patients.router import router as patients_router

app = FastAPI(title="Nightingale Care Note API", version="0.1.0")
app.include_router(patients_router)
app.include_router(glance_router)
app.include_router(highlights_router)
app.include_router(entries_router)
app.include_router(comments_router)
app.include_router(conflicts_router)


@app.get("/health")
def health() -> dict[str, str]:
    """Return a stable readiness contract for local development."""
    return {"status": "ok", "service": "nightingale-api"}
