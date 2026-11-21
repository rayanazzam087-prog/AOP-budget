"""Run with:  python -m pytest -q"""
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aop.agents import build_agents, extract_answer, run_python
from aop.evaluate import exact_match, numeric_match
from aop.ledger import Ledger
from aop.llm import LLM, LLMConfig, parse_json
from aop.pipeline import AOP, AOPConfig
from aop.plan import normalize, splice, remap_text
from aop.reward_model import MLP, RewardModel, RepresentativeWorks, CachedEmbedder, HashEmbedder
from aop.search import Search

AGENTS = ["code_agent", "math_agent", "search_agent", "commonsense_agent"]


def test_normalize_orders_and_fixes_refs():
    raw = [{"id": 5, "task": "Add the results of sub-tasks 7 and 9", "agent": "math", "depends_on": [7, 9]},
           {"id": 7, "task": "Find A", "agent": "search_agent", "depends_on": []},
           {"id": 9, "task": "Find B", "agent": "bogus", "depends_on": ["x"]}]
    p = normalize(raw, AGENTS)
    assert [s["id"] for s in p] == [1, 2, 3]
    assert p[-1]["depends_on"] == [1, 2] and p[-1]["task"] == "Add the results of sub-tasks 1 and 2"
    assert p[0]["agent"] == "search_agent" and p[1]["agent"] == "commonsense_agent"
    assert p[-1]["agent"] == "math_agent"


def test_cycle_is_broken():
    p = normalize([{"id": 1, "task": "a", "agent": "math_agent", "depends_on": [2]},
                   {"id": 2, "task": "b", "agent": "math_agent", "depends_on": [1]}], AGENTS)
    assert len(p) == 2 and p[0]["depends_on"] == []


def test_splice_rewires_dependents():
    plan = normalize([{"id": 1, "task": "Find A", "agent": "search_agent", "depends_on": []},
                      {"id": 2, "task": "Hard step", "agent": "math_agent", "depends_on": [1]},
                      {"id": 3, "task": "Use the result of sub-task 2", "agent": "math_agent", "depends_on": [2]}], AGENTS)
    new = [{"id": 1, "task": "Part one", "agent": "search_agent", "depends_on": []},
           {"id": 2, "task": "Part two using sub-task 1", "agent": "code_agent", "depends_on": [1]}]
    out = splice(plan, 2, new, AGENTS)
    assert [s["task"] for s in out] == ["Find A", "Part one", "Part two using sub-task 2", "Use the result of sub-task 3"]
    assert out[1]["depends_on"] == [1]          # inherited the target's dependency
    assert out[3]["depends_on"] == [3]          # now depends on the new sink


def test_remap_text():
    assert remap_text("combine sub-tasks 1, 2 and 3", {1: 4, 2: 5, 3: 6}) == "combine sub-tasks 4, 5 and 6"


def test_parse_json_variants():
    assert parse_json('```json\n{"a": 1}\n```') == {"a": 1}
    assert parse_json('Sure! {"a": [1,2]} done') == {"a": [1, 2]}


def test_grading():
    assert numeric_match("The answer is 1,234.0 people", "1234")
    assert numeric_match("about 50", "100") is False
    assert numeric_match("Paris", "Paris, France, Europe and more") is None
    assert exact_match("The Beatles.", "beatles")
    assert extract_answer("blah\nAnswer: 42") == "42"


def test_python_tool():
    assert run_python("print(6*7)", 5).strip() == "42"
    assert run_python("raise SystemExit(1)", 5).startswith("[error]")


def test_mlp_learns():
    rng = np.random.default_rng(0)
    X = rng.normal(size=(400, 8)).astype(np.float32)
    y = (X[:, 0] * 2 - X[:, 1]).astype(np.float32)
    m = MLP((8, 32, 16, 1))
    hist = m.fit(X, y, epochs=40, lr=3e-3, verbose=False)
    assert hist[-1]["train_mse"] < 0.2 * float(np.var(y))


def test_rm_save_load_and_rep_works(tmp_path):
    emb = CachedEmbedder(HashEmbedder())
    rm = RewardModel(emb)
    s1 = rm.score("compute 3+4", "math agent")
    rm.save(str(tmp_path / "rm.npz"))
    rm2 = RewardModel.load(str(tmp_path / "rm.npz"), emb)
    assert abs(rm2.score("compute 3+4", "math agent") - s1) < 1e-6
    rw = RepresentativeWorks(emb)
    assert rw.add("find the population of France", "search_agent")
    assert not rw.add("find the population of France", "search_agent")   # not novel
    sim, ex = rw.similarity("find the population of France", "search_agent")
    assert sim > 0.99 and ex


def _system(tmp_path):
    llm = LLM(LLMConfig(provider="mock", cache_path=str(tmp_path / "c.sqlite")))
    agents = build_agents(llm, Search("mock", cache_path=None))
    emb = CachedEmbedder(HashEmbedder())
    rw = RepresentativeWorks(emb)
    rw.add("Calculate the answer from the results", "math_agent")
    return llm, agents, RewardModel(emb), rw


def test_budget_is_respected(tmp_path):
    llm, agents, rm, rw = _system(tmp_path)
    q = "How many years passed between 1969 and 1990?"
    for policy in ("check", "revise", "split", "random"):
        for B in (0, 1, 2, 4):
            led = Ledger()
            # tau_high=99 -> everything is flagged, so revision always has work
            res = AOP(llm, agents, AOPConfig(policy=policy, budget=B, tau_high=99, tau_low=-99), rm, rw).run(q, led)
            assert led.coordination_calls() <= B, (policy, B)
            assert led.coordination_calls() + res.unused_budget == B
            if policy == "check":
                assert led.summary()["revision_calls"] == 0
            if policy == "revise":
                assert led.summary()["check_calls"] == 0
                assert led.coordination_calls() == min(B, 8) or res.unused_budget >= 0


def test_meta_and_full_run(tmp_path):
    llm, agents, rm, rw = _system(tmp_path)
    led = Ledger()
    r = AOP(llm, agents, AOPConfig(policy="meta"), None, None).run("What is 2+2?", led)
    assert led.coordination_calls() == 0 and r.answer
    led = Ledger()
    r = AOP(llm, agents, AOPConfig(policy="full", tau_high=99, tau_low=-99), rm, rw).run("What is 2+2?", led)
    assert led.summary()["check_calls"] >= 1 and r.final_plan
    json.dumps(r.__dict__, default=str)


def test_text_refs_become_dependencies():
    p = normalize([{"id": 1, "task": "Find A", "agent": "search_agent", "depends_on": []},
                   {"id": 2, "task": "Double the result of sub-task 1", "agent": "math_agent", "depends_on": []}], AGENTS)
    assert p[1]["depends_on"] == [1]


def test_splice_drops_duplicates_of_other_subtasks():
    plan = normalize([{"id": 1, "task": "Find chapters of Book A", "agent": "search_agent", "depends_on": []},
                      {"id": 2, "task": "Find chapters of Book B", "agent": "search_agent", "depends_on": []},
                      {"id": 3, "task": "Add the results of sub-tasks 1 and 2", "agent": "math_agent", "depends_on": [1, 2]}], AGENTS)
    new = [{"id": 1, "task": "Search for Book A", "agent": "search_agent", "depends_on": []},
           {"id": 2, "task": "Find chapters of Book B", "agent": "search_agent", "depends_on": []},
           {"id": 3, "task": "Count chapters using sub-task 1", "agent": "code_agent", "depends_on": [1]}]
    out = splice(plan, 1, new, AGENTS)
    tasks = [s["task"] for s in out]
    assert tasks.count("Find chapters of Book B") == 1 and len(out) == 4
    assert out[-1]["depends_on"] == sorted(out[-1]["depends_on"]) and len(out[-1]["depends_on"]) == 2


def test_splice_dedupes_even_when_reference_ids_differ():
    plan = normalize([{"id": 1, "task": "Find area A", "agent": "search_agent", "depends_on": []},
                      {"id": 2, "task": "Find area B", "agent": "search_agent", "depends_on": []},
                      {"id": 3, "task": "Divide the result of sub-task 2 by 500", "agent": "code_agent", "depends_on": [2]},
                      {"id": 4, "task": "Subtract the result of sub-task 3 from the result of sub-task 1", "agent": "math_agent", "depends_on": [1, 3]}], AGENTS)
    new = [{"id": 1, "task": "Search area A in square miles", "agent": "search_agent", "depends_on": []},
           {"id": 2, "task": "Divide the result of sub-task 1 by 500", "agent": "code_agent", "depends_on": [1]}]
    out = splice(plan, 1, new, AGENTS)
    # same wording but it divides A, not B (different input) -> must be kept
    assert sum("Divide" in s["task"] for s in out) == 2
    # a true duplicate: same wording AND same input (B) -> dropped
    new2 = [{"id": 1, "task": "Search area A", "agent": "search_agent", "depends_on": []},
            {"id": 2, "task": "Find area B", "agent": "search_agent", "depends_on": []},
            {"id": 3, "task": "Divide the result of sub-task 2 by 500", "agent": "code_agent", "depends_on": [2]}]
    plan2 = normalize([dict(x) for x in [
        {"id": 1, "task": "Find area A", "agent": "search_agent", "depends_on": []},
        {"id": 2, "task": "Find area B", "agent": "search_agent", "depends_on": []},
        {"id": 3, "task": "Divide the result of sub-task 2 by 500", "agent": "code_agent", "depends_on": [2]},
        {"id": 4, "task": "Subtract the result of sub-task 3 from the result of sub-task 1", "agent": "math_agent", "depends_on": [1, 3]}]], AGENTS)
    out2 = splice(plan2, 1, new2, AGENTS)
    assert sum("Divide" in s["task"] for s in out2) == 1 and sum("area B" in s["task"] for s in out2) == 1
