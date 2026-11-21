"""A deterministic fake LLM so the whole pipeline runs offline with no API key.

It returns well-formed outputs for every stage, so every code path (planning, detector,
revision, agents, scorer, judge) can be exercised and tested. Its *answers are
meaningless*: never report numbers produced with the mock provider.
"""
from __future__ import annotations

import hashlib
import json
import re


def _h(*parts) -> int:
    return int(hashlib.md5("|".join(map(str, parts)).encode()).hexdigest(), 16)


_AFFINITY = {
    "code_agent": ("calculate", "compute", "count", "subtract", "difference", "sum", "multiply", "divide"),
    "math_agent": ("calculate", "percent", "ratio", "subtract", "add", "average", "difference", "how many"),
    "search_agent": ("find", "year", "who", "when", "population", "founded", "born", "name"),
    "commonsense_agent": ("which", "why", "usually", "common", "is it"),
}


def _pick_agent(text: str, salt: int = 0) -> str:
    t = text.lower()
    scores = {a: sum(k in t for k in kws) for a, kws in _AFFINITY.items()}
    best = max(scores.values())
    cands = [a for a, s in scores.items() if s == best]
    return cands[_h(text, salt) % len(cands)]


class MockModel:
    def respond(self, messages, *, stage: str, meta: dict) -> str:
        fn = getattr(self, f"_{stage}", None)
        if fn is None and stage.startswith("agent_"):
            fn = self._agent_text
        if fn is None:
            return "Answer: unknown"
        return fn(messages, meta)

    # ---- meta-agent -----------------------------------------------------
    def _decompose(self, messages, meta):
        q = meta.get("query", messages[-1]["content"])
        n = 2 + _h(q) % 2
        subs = []
        for i in range(1, n + 1):
            if i < n:
                task = f"Find fact {i} needed for: {q[:60]}"
                agent = "search_agent"
                deps = []
            else:
                task = f"Calculate the answer from the results of sub-tasks {list(range(1, n))}."
                agent = "math_agent" if _h(q, "a") % 2 else "code_agent"
                deps = list(range(1, n))
            subs.append({"id": i, "task": task, "agent": agent, "reason": "mock", "depends_on": deps})
        return json.dumps({"subtasks": subs})

    def _detector(self, messages, meta):
        plan = meta.get("plan", [])
        ok = _h(meta.get("query", ""), len(plan)) % 3 != 0
        out = {"key_elements": ["mock"], "missing": [] if ok else ["a missing element"],
               "redundant_ids": [], "dependency_issues": [], "ok": ok, "revised_plan": None}
        if not ok and plan:
            new = [dict(s) for s in plan]
            new.insert(0, {"id": 0, "task": "Find the missing element of the query.",
                           "agent": "search_agent", "reason": "detector", "depends_on": []})
            for i, s in enumerate(new, 1):
                s["id"] = i
            new[-1]["depends_on"] = list(range(1, len(new)))
            out["revised_plan"] = {"subtasks": new}
        return json.dumps(out)

    def _replan(self, messages, meta):
        t = meta.get("task", "task")
        return json.dumps({"subtasks": [{"id": 1, "task": f"Look up: {t}", "agent": "search_agent",
                                         "reason": "replan", "depends_on": []}]})

    def _redescribe(self, messages, meta):
        return json.dumps({"task": "Precisely: " + meta.get("task", "task")})

    def _plan_in_detail(self, messages, meta):
        t = meta.get("task", "task")
        return json.dumps({"subtasks": [
            {"id": 1, "task": f"Find the inputs of: {t}", "agent": "search_agent", "reason": "split", "depends_on": []},
            {"id": 2, "task": f"Calculate using the result of sub-task 1: {t}", "agent": "code_agent",
             "reason": "split", "depends_on": [1]}]})

    def _aggregate(self, messages, meta):
        return json.dumps({"reasoning": "mock", "answer": str(_h(meta.get("query", "")) % 100)})

    # ---- agents ---------------------------------------------------------
    def _agent_code(self, messages, meta):
        return f"```python\nprint({_h(meta.get('task', '')) % 1000})\n```"

    def _agent_search_query(self, messages, meta):
        return json.dumps({"query": meta.get("task", "")[:60]})

    def _agent_text(self, messages, meta):
        return f"Reasoning (mock).\nAnswer: {_h(meta.get('task', '')) % 1000}"

    # ---- scorer / judge -------------------------------------------------
    def _scorer(self, messages, meta):
        task, agent = meta.get("task", ""), meta.get("agent", "")
        aff = sum(k in task.lower() for k in _AFFINITY.get(agent, ()))
        score = min(5, 1 + 2 * aff + _h(task, agent) % 2)
        return json.dumps({"score": score, "reason": "mock affinity"})

    def _judge(self, messages, meta):
        norm = lambda s: re.sub(r"[^a-z0-9.]", "", str(s).lower())
        same = norm(meta.get("pred")) == norm(meta.get("gold"))
        return json.dumps({"correct": same or _h(meta.get("question", ""), meta.get("pred")) % 3 == 0})
