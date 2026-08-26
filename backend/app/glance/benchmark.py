"""Reusable latency measurement primitives for the Care Glance endpoint."""

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from math import ceil
from time import perf_counter_ns
from typing import Protocol


class ResponseLike(Protocol):
    def raise_for_status(self) -> None: ...


class ClientLike(Protocol):
    def get(self, url: str, *, headers: dict[str, str]) -> ResponseLike: ...


@dataclass(frozen=True)
class BenchmarkResult:
    warmups: int
    samples: int
    p50_ms: float
    p95_ms: float
    max_ms: float
    target_p95_ms: float

    @property
    def meets_target(self) -> bool:
        return self.p95_ms <= self.target_p95_ms


def percentile(samples: Sequence[float], quantile: float) -> float:
    """Return the nearest-rank percentile for a non-empty sample."""
    if not samples:
        raise ValueError("samples must not be empty")
    if not 0 < quantile <= 1:
        raise ValueError("quantile must be in the interval (0, 1]")
    ordered = sorted(samples)
    rank = ceil(quantile * len(ordered))
    return ordered[rank - 1]


def benchmark_endpoint(
    client: ClientLike,
    endpoint: str,
    *,
    headers: dict[str, str],
    warmups: int = 20,
    measured: int = 200,
    target_p95_ms: float = 300.0,
    timer: Callable[[], int] = perf_counter_ns,
) -> BenchmarkResult:
    """Warm the endpoint, then measure successful request latency in milliseconds."""
    if warmups < 0:
        raise ValueError("warmups must be zero or greater")
    if measured <= 0:
        raise ValueError("measured must be greater than zero")
    if target_p95_ms <= 0:
        raise ValueError("target_p95_ms must be greater than zero")

    for _ in range(warmups):
        client.get(endpoint, headers=headers).raise_for_status()

    samples_ms: list[float] = []
    for _ in range(measured):
        started = timer()
        client.get(endpoint, headers=headers).raise_for_status()
        samples_ms.append((timer() - started) / 1_000_000)

    return BenchmarkResult(
        warmups=warmups,
        samples=measured,
        p50_ms=percentile(samples_ms, 0.50),
        p95_ms=percentile(samples_ms, 0.95),
        max_ms=max(samples_ms),
        target_p95_ms=target_p95_ms,
    )
