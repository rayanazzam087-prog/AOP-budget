"""Step 1 of the reward model (AOP section 4.2): build training data.

For each training query: the meta-agent decomposes it; each sub-task is given to
l = |agents|/2 agents (the assigned one + random others); a scorer LLM grades each answer
0-5. Output: one JSONL row per (sub-task, agent, score).

    python scripts/collect_rm_data.py --limit 200 --workers 8
"""
import argparse
import json
import random
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aop import prompts as P                                    # noqa: E402
from aop.data import load_split                                  # noqa: E402
from aop.ledger import Ledger                                    # noqa: E402
from aop.pipeline import AOP, AOPConfig                          # noqa: E402
from aop.system import add_common_args, build                    # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    add_common_args(ap)
    ap.add_argument("--dataset", default="rm_train", help="training pool (HuskyQA train is not public)")
    ap.add_argument("--split", default="train")
    ap.add_argument("--limit", type=int, default=None, help="number of training queries (paper: 1,440)")
    ap.add_argument("--l", type=int, default=None, help="agents per sub-task (paper: half the agents = 2)")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--out", default="data/rm/rm_data.jsonl")
    args = ap.parse_args()

    llm, judge_llm, agents, _, _ = build(args, need_rm=False)
    aop = AOP(llm, agents, AOPConfig(policy="meta"))
    rows = load_split(args.dataset, args.split, args.data_dir, args.limit)
    l = args.l or max(1, len(agents) // 2)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    done = set()
    if out.exists():
        done = {json.loads(x)["qid"] for x in out.read_text(encoding="utf-8").splitlines() if x.strip()}
    todo = [r for r in rows if r["id"] not in done]
    print(f"{len(rows)} queries, {len(done)} already done, l={l}")
    lock = threading.Lock()
    total = Ledger()

    def work(row):
        ledger = Ledger()
        plan = aop.decompose(row["question"], ledger)
        rng = random.Random(row["id"])
        recs = []
        answers = {}   # results of the assigned agent, passed to dependent sub-tasks
        for s in plan:
            others = [a for a in agents if a != s["agent"]]
            chosen = [s["agent"]] + rng.sample(others, min(l - 1, len(others)))
            deps = {d: answers.get(d, "") for d in s["depends_on"]}
            for name in chosen:
                try:
                    r = agents[name].run(s["task"], deps, ledger)
                    resp = r["response"]
                    if name == s["agent"]:
                        answers[s["id"]] = r["answer"] or resp[:500]
                except Exception as e:
                    resp = f"[agent error: {e}]"
                try:
                    g = judge_llm.chat_json(
                        [{"role": "system", "content": P.SCORER_SYSTEM},
                         {"role": "user", "content": P.SCORER_USER.format(task=s["task"], agent=name, agent_desc=P.AGENT_DESCRIPTIONS[name], response=resp[:3000])}],
                        stage="scorer", ledger=ledger, meta={"task": s["task"], "agent": name})
                    score = float(g.get("score", 0))
                except Exception:
                    continue
                recs.append({"qid": row["id"], "task": s["task"], "agent": name,
                             "assigned": name == s["agent"], "score": max(0.0, min(5.0, score)),
                             "response": resp[:1500]})
        return recs, ledger

    with ThreadPoolExecutor(args.workers) as ex:
        futs = [ex.submit(work, r) for r in todo]
        for i, f in enumerate(as_completed(futs), 1):
            recs, ledger = f.result()
            with lock, out.open("a", encoding="utf-8") as fh:
                for rec in recs:
                    fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
                total.records.extend(ledger.records)
            if i % 10 == 0 or i == len(futs):
                s = total.summary()
                print(f"[{i}/{len(futs)}] calls={s['llm_calls']} tokens={s['prompt_tokens']}+{s['completion_tokens']}")
    st = agents["search_agent"].search.stats
    print("search:", st, "<-- WARNING: search errors; run scripts/check_search.py" if st["error"] else "")
    print("saved ->", out)


if __name__ == "__main__":
    main()
