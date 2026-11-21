"""Re-grade existing reward-model data with the current (strict) scorer prompt.

The agents' answers are already saved in data/rm/rm_data.jsonl, so only the scorer
calls are repeated (~1 call per row, very cheap). Output keeps the old score as
"score_lenient" for comparison.

    python scripts/rescore_rm_data.py
    python scripts/rescore_rm_data.py --judge-model gpt-4o      # stronger grader (costs more)
"""
import argparse
import json
import sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aop import prompts as P                       # noqa: E402
from aop.ledger import Ledger                      # noqa: E402
from aop.system import add_common_args, build      # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    add_common_args(ap)
    ap.add_argument("--data", default="data/rm/rm_data.jsonl")
    ap.add_argument("--out", default="data/rm/rm_data_strict.jsonl",
                    help="use a NEW file name after changing the scorer prompt")
    ap.add_argument("--workers", type=int, default=8)
    args = ap.parse_args()
    _, judge_llm, _, _, _ = build(args, need_rm=False)

    rows = [json.loads(x) for x in Path(args.data).read_text(encoding="utf-8").splitlines() if x.strip()]
    out = Path(args.out)
    done = {}
    if out.exists():
        for x in out.read_text(encoding="utf-8").splitlines():
            if x.strip():
                r = json.loads(x)
                done[(r["qid"], r["task"], r["agent"])] = r
    todo = [r for r in rows if (r["qid"], r["task"], r["agent"]) not in done]
    print(f"{len(rows)} rows, {len(done)} already re-scored, {len(todo)} to go")
    ledger = Ledger()

    def work(r):
        try:
            g = judge_llm.chat_json(
                [{"role": "system", "content": P.SCORER_SYSTEM},
                 {"role": "user", "content": P.SCORER_USER.format(
                     task=r["task"], agent=r["agent"], agent_desc=P.AGENT_DESCRIPTIONS[r["agent"]],
                     response=r["response"][:3000])}],
                stage="scorer", ledger=ledger, meta={"task": r["task"], "agent": r["agent"]})
            new = dict(r, score_lenient=r.get("score_lenient", r["score"]),
                       score=max(0.0, min(5.0, float(g.get("score", 0)))), reason=g.get("reason", ""))
            return new
        except Exception as e:
            print("failed:", e)
            return None

    with ThreadPoolExecutor(args.workers) as ex, out.open("a", encoding="utf-8") as fh:
        for i, new in enumerate(ex.map(work, todo), 1):
            if new:
                fh.write(json.dumps(new, ensure_ascii=False) + "\n")
                done[(new["qid"], new["task"], new["agent"])] = new
            if i % 200 == 0:
                print(f"  {i}/{len(todo)}")
    s = ledger.summary()
    print(f"scorer calls: {s['llm_calls']}, tokens {s['prompt_tokens']}+{s['completion_tokens']}")
    final = list(done.values())
    print("lenient scores:", dict(sorted(Counter(int(r["score_lenient"]) for r in final).items())))
    print("strict scores: ", dict(sorted(Counter(int(r["score"]) for r in final).items())))
    by_agent = {}
    for r in final:
        by_agent.setdefault(r["agent"], []).append(r["score"])
    print("mean strict score by agent:", {a: round(sum(v) / len(v), 2) for a, v in sorted(by_agent.items())})
    print(f"saved -> {out}\nNext: python scripts/train_reward_model.py --data {out.as_posix()}")


if __name__ == "__main__":
    main()
