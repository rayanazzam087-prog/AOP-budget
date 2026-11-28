"""AOP pipeline with a coordination-budget controller.

Fixed costs (not budgeted): decompose (1 call), agent execution, aggregate (1 call).
Coordination calls (budgeted by B):
  * CHECK  - one detector call: checks completeness / redundancy and may rewrite the plan.
  * REVISE - one call that fixes one flagged sub-task: replan | re-describe | plan-in-detail.
The reward model's re-assignment uses CPU computation but no LLM call
and is applied in every condition except the plain Meta-Agent baseline.

Policies
  meta    - Meta-Agent baseline: decompose -> execute -> aggregate. No RM, no checks.
  routing - Same RM routing as coordinated policies, with no checking or revision.
  full    - AOP as in the paper: detector rounds, then revise every flagged sub-task. No cap.
  check   - Check-only(B): spend the budget on detector calls only.
  revise  - Revise-only(B): spend it on revisions only, riskiest (lowest score) sub-task first.
  split   - Split(B): alternate check, revise, check, ... (falls back to the other if one runs out).
  random  - Random(B): pick check or revise at random each step (seeded per query).
"""
from __future__ import annotations

import copy
import hashlib
import random
from dataclasses import dataclass, asdict, field

from . import prompts as P
from .agents import Agent
from .ledger import Ledger
from .llm import LLM
from .plan import normalize, splice, public
from .reward_model import RewardModel, RepresentativeWorks

POLICIES = ("meta", "routing", "full", "check", "revise", "split", "random")


@dataclass
class AOPConfig:
    policy: str = "full"
    budget: int = 0                 # B: max coordination calls (ignored for meta/full)
    tau_high: float = 3.5           # accept the assignment if RM score >= tau_high
    tau_low: float = 1.5            # best score < tau_low  -> replan
    tau_sim: float = 0.6            # similarity >= tau_sim -> re-describe, else plan-in-detail
    reassign_margin: float = 0.5    # move to another agent only if the RM prefers it by this much
    max_detector_rounds: int = 2    # for policy=full
    max_subtasks: int = 8
    seed: int = 0

    def name(self) -> str:
        return self.policy if self.policy in ("meta", "routing", "full") else f"{self.policy}_B{self.budget}"


@dataclass
class QueryResult:
    answer: str
    initial_plan: list
    final_plan: list
    subtask_results: list
    events: list = field(default_factory=list)
    unused_budget: int = 0


class AOP:
    def __init__(self, llm: LLM, agents: dict[str, Agent], cfg: AOPConfig,
                 reward_model: RewardModel | None = None,
                 rep_works: RepresentativeWorks | None = None):
        if cfg.policy not in POLICIES:
            raise ValueError(f"policy must be one of {POLICIES}")
        if cfg.policy != "meta" and reward_model is None:
            raise ValueError("this policy needs a trained reward model (scripts/train_reward_model.py)")
        self.llm, self.agents, self.cfg = llm, agents, cfg
        self.rm, self.rw = reward_model, rep_works
        self.agent_desc = {n: a.description for n, a in agents.items()}
        self.agents_block = P.agents_block(self.agent_desc)

    # =================================================================== main
    def run(self, query: str, ledger: Ledger) -> QueryResult:
        cfg = self.cfg
        plan = self.decompose(query, ledger)
        initial = public(plan)
        events: list[dict] = []
        unused = 0
        if cfg.policy != "meta":
            budget = (10 ** 6 if cfg.policy == "full" else
                      0 if cfg.policy == "routing" else cfg.budget)
            worker = copy.copy(self)          # per-query state (_plan) -> thread-safe
            unused = worker.coordinate(query, plan, budget, ledger, events)
            plan = worker._plan
        results = self.execute(plan, ledger)
        answer = self.aggregate(query, plan, results, ledger)
        return QueryResult(answer, initial, public(plan), results, events, unused)

    # =================================================================== coordination
    def coordinate(self, query, plan, budget, ledger, events) -> int:
        """Spend up to ``budget`` coordination calls; returns the unused part."""
        cfg = self.cfg
        rng = random.Random(int(hashlib.sha256(f"{cfg.seed}|{query}".encode()).hexdigest(), 16))
        self._plan = plan
        self.route(events)
        check_done, detector_rounds, revised_uids = False, 0, set()
        spent, step = 0, 0
        while spent < budget:
            flagged = [s for s in self._plan if s["_flag"] and s["uid"] not in revised_uids]
            can_check = not check_done and (cfg.policy != "full" or detector_rounds < cfg.max_detector_rounds)
            can_revise = bool(flagged)
            if cfg.policy == "check":
                action = "check" if can_check else None
            elif cfg.policy == "revise":
                action = "revise" if can_revise else None
            elif cfg.policy == "full":
                action = "check" if can_check else ("revise" if can_revise else None)
            elif cfg.policy == "split":
                pref = "check" if step % 2 == 0 else "revise"
                avail = {"check": can_check, "revise": can_revise}
                action = pref if avail[pref] else next((a for a, ok in avail.items() if ok), None)
            else:  # random
                opts = [a for a, ok in (("check", can_check), ("revise", can_revise)) if ok]
                action = rng.choice(opts) if opts else None
            if action is None:
                break
            if action == "check":
                detector_rounds += 1
                changed = self.check(query, ledger, events)
                if not changed:
                    check_done = True
            else:
                target = min(flagged, key=lambda s: s["_best"])
                new_uids = self.revise(query, target, ledger, events)
                revised_uids.add(target["uid"])
                revised_uids.update(new_uids)   # new pieces are not revised again
            self.route(events)
            spent += 1
            step += 1
        return 0 if cfg.policy == "full" else budget - spent

    def route(self, events):
        """CPU-only RM step: score every sub-task, move it to the best agent if its score is
        below tau_high AND the best agent is clearly better (reassign_margin), and flag it
        for revision if even the best agent scores < tau_high."""
        for s in self._plan:
            if s.get("_scored_task") == s["task"]:
                continue
            scores = self.rm.score_all(s["task"], self.agent_desc)
            best = max(scores, key=scores.get)
            if (scores[s["agent"]] < self.cfg.tau_high and best != s["agent"]
                    and scores[best] - scores[s["agent"]] >= self.cfg.reassign_margin):
                events.append({"step": "reassign", "id": s["id"], "from": s["agent"], "to": best,
                               "score_from": round(scores[s["agent"]], 2), "score_to": round(scores[best], 2)})
                s["agent"] = best
            s["_score"], s["_best"] = scores[s["agent"]], scores[best]
            s["_flag"] = scores[best] < self.cfg.tau_high
            s["_scored_task"] = s["task"]

    def check(self, query, ledger, events) -> bool:
        """One detector call. Returns True if it changed the plan."""
        system = P.DETECTOR_SYSTEM.format(agents=self.agents_block, schema=P.PLAN_SCHEMA)
        user = P.DETECTOR_USER.format(query=query, plan=P.plan_text(public(self._plan)))
        try:
            out = self.llm.chat_json([{"role": "system", "content": system},
                                      {"role": "user", "content": user}], stage="detector",
                                     ledger=ledger, meta={"query": query, "plan": public(self._plan)},
                                     repair_attempts=0)
        except ValueError:
            events.append({"step": "check", "ok": None, "changed": False, "error": "bad json"})
            return False
        new = (out.get("revised_plan") or {}).get("subtasks") if isinstance(out.get("revised_plan"), dict) else None
        changed = bool(new) and not out.get("ok", False)
        if changed:
            # Preserve identities, but normalize and re-score accepted revisions.
            old = {s["task"]: s for s in self._plan}
            new = normalize(new, list(self.agents), self.cfg.max_subtasks)
            for s in new:
                if s["task"] in old:
                    s["uid"] = old[s["task"]]["uid"]
            changed = public(new) != public(self._plan)
            if changed:
                self._plan = new
        events.append({"step": "check", "ok": out.get("ok"), "missing": out.get("missing", []),
                       "redundant_ids": out.get("redundant_ids", []), "changed": bool(changed),
                       "n_subtasks": len(self._plan)})
        return bool(changed)

    def revise(self, query, target, ledger, events) -> set:
        """One revision call on ``target``. Returns uids of the sub-tasks it created."""
        cfg = self.cfg
        others = "\n".join(f"{s['id']}. [{s['agent']}] {s['task']}" for s in self._plan if s is not target) or "(none)"
        user = P.SUBTASK_USER.format(query=query, others=others, task=target["task"])
        meta = {"query": query, "task": target["task"], "agent": target["agent"]}
        if target["_best"] < cfg.tau_low:
            action = "replan"
            system = P.REPLAN_SYSTEM.format(agents=self.agents_block, schema=P.PLAN_SCHEMA)
        else:
            sim, examples = self.rw.similarity(target["task"], target["agent"]) if self.rw else (0.0, [])
            if sim >= cfg.tau_sim:
                action = "redescribe"
                system = P.REDESCRIBE_SYSTEM.format(
                    agent=target["agent"], agent_desc=self.agent_desc[target["agent"]],
                    examples="\n".join(f"- {e}" for e in examples))
            else:
                action = "plan_in_detail"
                system = P.PLAN_IN_DETAIL_SYSTEM.format(agents=self.agents_block, schema=P.PLAN_SCHEMA)
        before = len(self._plan)
        try:
            out = self.llm.chat_json([{"role": "system", "content": system},
                                      {"role": "user", "content": user}],
                                     stage=action, ledger=ledger, meta=meta, repair_attempts=0)
        except ValueError:
            events.append({"step": "revise", "action": action, "id": target["id"], "error": "bad json"})
            return set()
        new_uids = set()
        if action == "redescribe" and out.get("task"):
            target["task"] = str(out["task"]).strip()
            new_uids.add(target["uid"])
        elif action != "redescribe" and out.get("subtasks"):
            old_uids = {s["uid"] for s in self._plan}
            self._plan = splice(self._plan, target["id"], out["subtasks"], list(self.agents), cfg.max_subtasks)
            new_uids = {s["uid"] for s in self._plan} - old_uids
        events.append({"step": "revise", "action": action, "id": target["id"],
                       "best_score": round(target["_best"], 2),
                       "n_subtasks": f"{before}->{len(self._plan)}"})
        return new_uids

    # =================================================================== plan / execute / aggregate
    def decompose(self, query, ledger) -> list[dict]:
        system = P.DECOMPOSE_SYSTEM.format(agents=self.agents_block, schema=P.PLAN_SCHEMA)
        try:
            out = self.llm.chat_json([{"role": "system", "content": system},
                                      {"role": "user", "content": P.DECOMPOSE_USER.format(query=query)}],
                                     stage="decompose", ledger=ledger, meta={"query": query})
            plan = normalize(out.get("subtasks", []), list(self.agents), self.cfg.max_subtasks)
        except ValueError:
            plan = []
        if not plan:  # fall back to a single sub-task
            plan = normalize([{"id": 1, "task": query, "agent": "commonsense_agent", "depends_on": []}],
                             list(self.agents))
        return plan

    def execute(self, plan, ledger) -> list[dict]:
        answers: dict[int, str] = {}
        results = []
        for s in plan:  # plan is topologically ordered
            deps = {d: answers.get(d, "") for d in s["depends_on"]}
            try:
                r = self.agents[s["agent"]].run(s["task"], deps, ledger)
            except Exception as e:
                r = {"answer": "", "response": f"[agent error: {e}]"}
            # downstream agents see the value AND which sub-task produced it
            answers[s["id"]] = f"{r['answer'] or r['response'][:500]}  (from: {s['task'][:120]})"
            results.append({"id": s["id"], "agent": s["agent"], "task": s["task"],
                            "answer": r["answer"], "response": r["response"][:3000]})
        return results

    def aggregate(self, query, plan, results, ledger) -> str:
        lines = "\n".join(f"Sub-task {r['id']} ({r['agent']}): {r['task']}\nResult: {r['answer'] or r['response'][:500]}"
                          for r in results)
        try:
            out = self.llm.chat_json([{"role": "system", "content": P.AGGREGATE_SYSTEM},
                                      {"role": "user", "content": P.AGGREGATE_USER.format(query=query, results=lines)}],
                                     stage="aggregate", ledger=ledger, meta={"query": query})
            return str(out.get("answer", "")).strip()
        except ValueError:
            return results[-1]["answer"] if results else ""


def result_to_dict(r: QueryResult) -> dict:
    return asdict(r)
