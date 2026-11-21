"""Plan data structure helpers: validation, splicing revised sub-tasks in, ordering."""
from __future__ import annotations

import itertools
import re

_uid = itertools.count(1)


def _agent_name(raw: str, agents: list[str]) -> str:
    raw = (raw or "").strip().lower()
    if raw in agents:
        return raw
    for a in agents:
        if a.split("_")[0] in raw:
            return a
    return "commonsense_agent" if "commonsense_agent" in agents else agents[0]


def normalize(subtasks: list[dict], agents: list[str], max_subtasks: int = 8) -> list[dict]:
    """Coerce an LLM-produced plan into a valid DAG with ids 1..n in execution order."""
    clean = []
    for i, s in enumerate(subtasks or []):
        if not isinstance(s, dict) or not str(s.get("task", "")).strip():
            continue
        try:
            sid = int(s.get("id", i + 1))
        except (TypeError, ValueError):
            sid = i + 1
        deps = []
        for d in s.get("depends_on") or []:
            try:
                deps.append(int(d))
            except (TypeError, ValueError):
                pass
        clean.append({"id": sid, "task": str(s["task"]).strip(),
                      "agent": _agent_name(str(s.get("agent", "")), agents),
                      "reason": str(s.get("reason", "")), "depends_on": deps,
                      "uid": s.get("uid") or next(_uid),
                      **{k: v for k, v in s.items() if k.startswith("_")}})
    # de-duplicate ids, keep order of appearance
    seen, uniq = set(), []
    for s in clean:
        if s["id"] in seen:
            s["id"] = max(seen) + 1
        seen.add(s["id"])
        uniq.append(s)
    uniq = uniq[:max_subtasks]
    # a task that says "the result of sub-task 3" must depend on 3, even if the LLM forgot it
    ids = {s["id"] for s in uniq}
    for s in uniq:
        for m in _REF_RE.finditer(s["task"]):
            for n in re.findall(r"\d+", m.group(2)):
                if int(n) in ids and int(n) != s["id"] and int(n) not in s["depends_on"]:
                    s["depends_on"].append(int(n))
    return renumber(topo_sort(uniq))


def topo_sort(plan: list[dict]) -> list[dict]:
    """Order by dependencies; edges that would create a cycle are dropped."""
    ids = {s["id"] for s in plan}
    for s in plan:
        s["depends_on"] = sorted({d for d in s["depends_on"] if d in ids and d != s["id"]})
    done, order, remaining = set(), [], list(plan)
    while remaining:
        ready = [s for s in remaining if all(d in done for d in s["depends_on"])]
        if not ready:                      # cycle: break it at the first remaining node
            s = remaining[0]
            s["depends_on"] = [d for d in s["depends_on"] if d in done]
            ready = [s]
        for s in ready:
            done.add(s["id"])
            order.append(s)
            remaining.remove(s)
    return order


_REF_RE = re.compile(r"((?:sub-?tasks?|steps?)\s*(?:#\s*)?)(\d+(?:\s*(?:,|and|&|or)\s*\d+)*)", re.I)


def remap_text(text: str, mapping: dict[int, int]) -> str:
    """Rewrite references like 'sub-task 2' / 'sub-tasks 1 and 3' after ids change."""
    def fix(m):
        nums = re.sub(r"\d+", lambda n: str(mapping.get(int(n.group()), int(n.group()))), m.group(2))
        return m.group(1) + nums
    return _REF_RE.sub(fix, text)


def renumber(plan: list[dict]) -> list[dict]:
    mapping = {s["id"]: i for i, s in enumerate(plan, 1)}
    for s in plan:
        s["id"] = mapping[s["id"]]
        s["depends_on"] = [mapping[d] for d in s["depends_on"] if d in mapping]
        s["task"] = remap_text(s["task"], mapping)
    return plan


def splice(plan: list[dict], target_id: int, new: list[dict], agents: list[str],
           max_subtasks: int = 8) -> list[dict]:
    """Replace sub-task ``target_id`` with the sub-plan ``new`` (ids local to ``new``).

    * new sub-tasks without local deps inherit the target's dependencies;
    * sub-tasks that depended on the target now depend on the new sub-plan's sinks.
    """
    target = next(s for s in plan if s["id"] == target_id)
    new = normalize(new, agents, max_subtasks)
    if not new:
        return plan
    budget_left = max_subtasks - (len(plan) - 1)
    new = new[:max(1, budget_left)]
    offset = max(s["id"] for s in plan) + 1000
    local_ids = {s["id"] for s in new}
    local_map = {i: i + offset for i in local_ids}
    for s in new:
        s["depends_on"] = [d + offset for d in s["depends_on"] if d in local_ids] or list(target["depends_on"])
        s["id"] += offset
        s["task"] = remap_text(s["task"], local_map)
    # drop new sub-tasks that duplicate an existing one (the LLM re-planned other work):
    # same wording (ignoring reference ids) AND the same inputs after mapping earlier duplicates
    others = [s for s in plan if s["id"] != target_id]
    dup: dict[int, int] = {}
    for s in new:                                   # new is in dependency order
        deps = sorted({dup.get(d, d) for d in s["depends_on"]})
        match = next((o for o in others if _norm(o["task"]) == _norm(s["task"])
                      and sorted(o["depends_on"]) == deps), None)
        if match:
            dup[s["id"]] = match["id"]
    if dup:
        new = [s for s in new if s["id"] not in dup]
        if not new:
            return plan
        for s in new:
            s["depends_on"] = sorted({dup.get(d, d) for d in s["depends_on"]})
            s["task"] = remap_text(s["task"], dup)
    referenced = {d for s in new for d in s["depends_on"]}
    sinks = [s["id"] for s in new if s["id"] not in referenced]
    out = []
    for s in plan:
        if s["id"] == target_id:
            out.extend(new)
            continue
        if target_id in s["depends_on"]:
            s["depends_on"] = [d for d in s["depends_on"] if d != target_id] + sinks
            s["task"] = remap_text(s["task"], {target_id: sinks[-1]})
        out.append(s)
    return renumber(topo_sort(out))


def _norm(text: str) -> str:
    """Text for duplicate detection: sub-task references removed (their ids differ between
    the old plan and a revision's local numbering), everything else kept."""
    text = _REF_RE.sub(lambda m: m.group(1), text)
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def public(plan: list[dict]) -> list[dict]:
    """Plan as shown to LLMs (no internal fields)."""
    return [{k: s[k] for k in ("id", "task", "agent", "depends_on")} for s in plan]
