"""Benchmark the Care Glance API against the fixed synthetic Sarah Lim story."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = PROJECT_ROOT / "backend"
sys.path.insert(0, str(BACKEND_ROOT))

from app.dependencies import get_db_session  # noqa: E402
from app.glance.benchmark import benchmark_endpoint  # noqa: E402
from app.main import app  # noqa: E402
from app.models.base import Base  # noqa: E402
from app.seed.sarah_lim import seed_sarah_lim  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--warmups", type=int, default=20)
    parser.add_argument("--requests", type=int, default=200)
    parser.add_argument("--target-p95-ms", type=float, default=300.0)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def enable_sqlite_foreign_keys(dbapi_connection, _connection_record) -> None:
        dbapi_connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    session = Session(engine)
    story = seed_sarah_lim(session)

    def override_session():
        yield session

    app.dependency_overrides[get_db_session] = override_session
    try:
        with TestClient(app) as client:
            result = benchmark_endpoint(
                client,
                f"/api/v1/patients/{story.patient.id}/glance",
                headers={"X-Demo-User-ID": str(story.clinician_user.id)},
                warmups=args.warmups,
                measured=args.requests,
                target_p95_ms=args.target_p95_ms,
            )
    finally:
        app.dependency_overrides.clear()
        session.close()
        engine.dispose()

    status = "PASS" if result.meets_target else "FAIL"
    print("Care Glance local synthetic benchmark")
    print(f"Warmups: {result.warmups}")
    print(f"Measured requests: {result.samples}")
    print(f"P50: {result.p50_ms:.2f} ms")
    print(f"P95: {result.p95_ms:.2f} ms")
    print(f"Max: {result.max_ms:.2f} ms")
    print(f"Target: P95 <= {result.target_p95_ms:.2f} ms [{status}]")
    return 0 if result.meets_target else 1


if __name__ == "__main__":
    raise SystemExit(main())
