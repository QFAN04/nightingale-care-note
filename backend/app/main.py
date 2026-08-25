from fastapi import FastAPI

app = FastAPI(title="Nightingale Care Note API", version="0.1.0")


@app.get("/health")
def health() -> dict[str, str]:
    """Return a stable readiness contract for local development."""
    return {"status": "ok", "service": "nightingale-api"}
