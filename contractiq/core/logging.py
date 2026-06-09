"""Lightweight structured logging + per-run latency/token tracing (SRS 4.6).

A real deployment would route this to LangSmith; here we provide an
always-available local tracer that records latency and token usage per agent
run so the observability requirement is satisfied without external services.
"""
from __future__ import annotations

import logging
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Iterator

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-7s %(name)s :: %(message)s",
)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


@dataclass
class RunTrace:
    """Single traced unit of work (agent node, tool call, retrieval, …)."""

    name: str
    latency_ms: float = 0.0
    tokens_in: int = 0
    tokens_out: int = 0
    metadata: dict = field(default_factory=dict)


# In-memory trace buffer — inspected by the /traces endpoint and evals.
TRACES: list[RunTrace] = []


@contextmanager
def trace(name: str, **metadata) -> Iterator[RunTrace]:
    """Context manager recording wall-clock latency for ``name``.

    Example::

        with trace("risk_scorer", clause_type="Termination") as t:
            ...
            t.tokens_in, t.tokens_out = 1200, 80
    """
    rec = RunTrace(name=name, metadata=dict(metadata))
    start = time.perf_counter()
    try:
        yield rec
    finally:
        rec.latency_ms = round((time.perf_counter() - start) * 1000, 2)
        TRACES.append(rec)
        get_logger("trace").info(
            "%s latency=%.1fms tokens_in=%d tokens_out=%d %s",
            rec.name,
            rec.latency_ms,
            rec.tokens_in,
            rec.tokens_out,
            rec.metadata or "",
        )
