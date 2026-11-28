import copy
import importlib.util
import json
from pathlib import Path

import pytest

from aop.ledger import Ledger
from aop.llm import LLM, LLMConfig, parse_json
from aop.pipeline import AOP, AOPConfig
from aop.plan import normalize, public
from test_core import _system, AGENTS


@pytest.mark.parametrize("dependency", [1, "1", [1]])
def test_scalar_dependencies(dependency):
    plan = normalize([{"id": 1, "task": "Lookup", "agent": "search_agent"},
                      {"id": 2, "task": "Compute", "agent": "math_agent", "depends_on": dependency}], AGENTS)
    assert plan[1]["depends_on"] == [1]


@pytest.mark.parametrize("change", ["agent", "dependency"])
def test_detector_accepts_structural_correction(tmp_path, change):
    llm, agents, rm, rw = _system(tmp_path)
    aop = AOP(llm, agents, AOPConfig(policy="check", budget=1), rm, rw)
    aop._plan = normalize([{"id": 1, "task": "Lookup", "agent": "search_agent"},
                           {"id": 2, "task": "Compute", "agent": "math_agent"}], AGENTS)
    new = copy.deepcopy(public(aop._plan))
    if change == "agent":
        new[1]["agent"] = "code_agent"
    else:
        new[1]["depends_on"] = [1]
    llm._call = lambda *args: (json.dumps({"ok": False, "revised_plan": {"subtasks": new}}), 1, 1)
    assert aop.check("question", Ledger(), [])
    assert public(aop._plan) == new


def test_routing_baseline_has_no_coordination(tmp_path):
    llm, agents, rm, rw = _system(tmp_path)
    cfg = AOPConfig(policy="routing", budget=99, tau_high=99)
    led = Ledger()
    res = AOP(llm, agents, cfg, rm, rw).run("What is 2+2?", led)
    assert cfg.name() == "routing"
    assert res.answer and led.coordination_calls() == 0
    assert all(e["step"] == "reassign" for e in res.events)


def test_invalid_coordination_json_does_not_exceed_budget(tmp_path):
    llm, agents, rm, rw = _system(tmp_path)
    original = llm._call
    def malformed(messages, json_mode, max_tokens, stage, meta):
        if stage == "detector":
            return "not JSON", 1, 1
        return original(messages, json_mode, max_tokens, stage, meta)
    llm._call = malformed
    led = Ledger()
    AOP(llm, agents, AOPConfig(policy="check", budget=1), rm, rw).run("What is 2+2?", led)
    assert led.coordination_calls() == 1


def test_non_object_json_rejected():
    with pytest.raises(ValueError):
        parse_json('[{"task": "example"}]')


def test_resume_guard(tmp_path):
    path = Path(__file__).resolve().parents[1] / "scripts" / "run_experiment.py"
    spec = importlib.util.spec_from_file_location("run_review", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    out = tmp_path / "meta.jsonl"
    mod.ensure_manifest(out, {"model": "a"})
    mod.ensure_manifest(out, {"model": "a"})
    with pytest.raises(ValueError, match="provenance changed"):
        mod.ensure_manifest(out, {"model": "b"})
    legacy = tmp_path / "old.jsonl"
    legacy.write_text('{}\n')
    with pytest.raises(ValueError, match="Legacy results"):
        mod.ensure_manifest(legacy, {})


def test_paired_statistics_and_duplicate_guard(tmp_path):
    path = Path(__file__).resolve().parents[1] / "scripts" / "compare_policies.py"
    spec = importlib.util.spec_from_file_location("compare_review", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    def row(correct):
        return {"id": "1", "question": "Q", "gold": "A", "correct": correct,
                "cost": {"prompt_tokens": 10, "completion_tokens": 2, "coordination_calls": 1}}
    r = mod.compare({"1": row(True)}, {"1": row(False)}, "mock", "check", "revise", resamples=10)
    assert r["a_only_correct"] == 1 and r["b_only_correct"] == 0
    assert r["difference_pp"] == 100 and r["p"] == 1
    rows = [{"p": .01}, {"p": .04}, {"p": .03}]
    mod.holm(rows)
    assert [r["p_holm"] for r in rows] == [.03, .06, .06]
    with pytest.raises(ValueError, match="Question IDs differ"):
        mod.compare({"1": row(True)}, {}, "mock", "a", "b")
    f = tmp_path / "duplicate.jsonl"
    f.write_text((json.dumps(row(True)) + "\n") * 2)
    with pytest.raises(ValueError, match="Duplicate ID"):
        mod.load(f)
