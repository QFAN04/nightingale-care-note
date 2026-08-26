from fastapi import FastAPI

from app.glance.router import router as glance_router
from app.patients.router import router as patients_router

app = FastAPI(title="Nightingale Care Note API", version="0.1.0")
app.include_router(patients_router)
app.include_router(glance_router)


@app.get("/health")
def health() -> dict[str, str]:
    """Return a stable readiness contract for local development."""
    return {"status": "ok", "service": "nightingale-api"}
