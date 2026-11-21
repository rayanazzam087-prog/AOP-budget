"""Per-query cost accounting.

Every LLM call is recorded with the pipeline *stage* that made it. Stages are
grouped so we can separate fixed costs (planning, execution, aggregation) from
the *coordination* calls that the budget B limits (plan checking, revision).
"""
from __future__ import annotations

import threading
from dataclasses import dataclass, field, asdict

# Stages whose LLM calls count against the coordination budget B.
CHECK_STAGES = {"detector"}
REVISION_STAGES = {"replan", "redescribe", "plan_in_detail"}
COORDINATION_STAGES = CHECK_STAGES | REVISION_STAGES


@dataclass
class CallRecord:
    stage: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    latency_s: float
    cached: bool = False


@dataclass
class Ledger:
    records: list[CallRecord] = field(default_factory=list)
    tool_calls: dict[str, int] = field(default_factory=dict)
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def add(self, rec: CallRecord) -> None:
        with self._lock:
            self.records.append(rec)

    def add_tool(self, name: str) -> None:
        with self._lock:
            self.tool_calls[name] = self.tool_calls.get(name, 0) + 1

    # ---- aggregates -------------------------------------------------------
    def calls(self, stages: set[str] | None = None) -> int:
        return sum(1 for r in self.records if stages is None or r.stage in stages)

    def coordination_calls(self) -> int:
        return self.calls(COORDINATION_STAGES)

    def summary(self) -> dict:
        by_stage: dict[str, dict] = {}
        for r in self.records:
            s = by_stage.setdefault(r.stage, {"calls": 0, "prompt_tokens": 0,
                                              "completion_tokens": 0, "latency_s": 0.0})
            s["calls"] += 1
            s["prompt_tokens"] += r.prompt_tokens
            s["completion_tokens"] += r.completion_tokens
            s["latency_s"] += r.latency_s
        return {
            "llm_calls": len(self.records),
            "coordination_calls": self.coordination_calls(),
            "check_calls": self.calls(CHECK_STAGES),
            "revision_calls": self.calls(REVISION_STAGES),
            "prompt_tokens": sum(r.prompt_tokens for r in self.records),
            "completion_tokens": sum(r.completion_tokens for r in self.records),
            # Sum of call latencies = sequential wall-clock estimate (calls in one
            # query run sequentially in this implementation).
            "llm_latency_s": round(sum(r.latency_s for r in self.records), 3),
            "cached_calls": sum(1 for r in self.records if r.cached),
            "tool_calls": dict(self.tool_calls),
            "by_stage": by_stage,
        }

    def to_list(self) -> list[dict]:
        return [asdict(r) for r in self.records]
