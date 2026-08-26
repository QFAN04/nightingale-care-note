from collections.abc import Iterator

import pytest

from app.glance.benchmark import benchmark_endpoint, percentile


class FakeResponse:
    def __init__(self, status_code: int = 200) -> None:
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


class FakeClient:
    def __init__(self, statuses: list[int]) -> None:
        self._statuses = iter(statuses)
        self.calls = 0

    def get(self, _url: str, *, headers: dict[str, str]) -> FakeResponse:
        assert headers == {"X-Demo-User-ID": "clinician-id"}
        self.calls += 1
        return FakeResponse(next(self._statuses))


def clock(values: list[int]) -> Iterator[int]:
    yield from values


def test_percentile_uses_nearest_rank_for_latency_samples() -> None:
    samples = [1.0, 2.0, 3.0, 4.0, 10.0]

    assert percentile(samples, 0.50) == 3.0
    assert percentile(samples, 0.95) == 10.0


def test_benchmark_excludes_warmups_and_reports_target() -> None:
    client = FakeClient([200, 200, 200, 200, 200])
    timer = clock([0, 10_000_000, 10_000_000, 30_000_000, 30_000_000, 330_000_000])

    result = benchmark_endpoint(
        client,
        "/api/v1/patients/patient-id/glance",
        headers={"X-Demo-User-ID": "clinician-id"},
        warmups=2,
        measured=3,
        target_p95_ms=300.0,
        timer=lambda: next(timer),
    )

    assert client.calls == 5
    assert result.samples == 3
    assert result.p50_ms == pytest.approx(20.0)
    assert result.p95_ms == pytest.approx(300.0)
    assert result.max_ms == pytest.approx(300.0)
    assert result.meets_target is True


def test_benchmark_stops_on_failed_response() -> None:
    client = FakeClient([200, 500])

    with pytest.raises(RuntimeError, match="HTTP 500"):
        benchmark_endpoint(
            client,
            "/api/v1/patients/patient-id/glance",
            headers={"X-Demo-User-ID": "clinician-id"},
            warmups=1,
            measured=1,
        )
