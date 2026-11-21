"""Run one condition (policy + budget) over a dataset split and save per-query results.

    python scripts/run_experiment.py --policy full --limit 50
    python scripts/run_experiment.py --policy check --budget 2

Results go to results/<dataset>_<split>/<condition>.jsonl (one line per query, with
answer, correctness, plan trace and the cost ledger). Re-running resumes where it stopped.
"""
import argparse
import json
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aop.data import load_split                         # noqa: E402
from aop.evaluate import grade                          # noqa: E402
from aop.ledger import Ledger                           # noqa: E402
from aop.pipeline import AOP, AOPConfig, POLICIES, result_to_dict  # noqa: E402
from aop.system import add_common_args, build           # noqa: E402


def add_run_args(ap):
    ap.add_argument("--dataset", default="huskyqa")
    ap.add_argument("--split", default="test")
    ap.add_argument("--limit", type=int, default=None, help="fixed random subset of N queries")
    ap.add_argument("--workers", type=int, default=8, help="queries processed in parallel")
    ap.add_argument("--tau-high", type=float, default=None, help="default: models/thresholds.json, else 3.5")
    ap.add_argument("--tau-low", type=float, default=None, help="default: models/thresholds.json, else 1.5")
    ap.add_argument("--tau-sim", type=float, default=None, help="default: models/thresholds.json, else 0.6")
    ap.add_argument("--thresholds", default="models/thresholds.json")
    ap.add_argument("--reassign-margin", type=float, default=0.5,
                    help="RM must prefer another agent by this much before re-assigning")
    ap.add_argument("--no-judge", action="store_true", help="skip the LLM judge (rule-based grading only)")
    ap.add_argument("--results-dir", default="results")
    ap.add_argument("--tag", default="", help="suffix for the output file (e.g. model name)")


def run_condition(args, policy: str, budget: int, system=None) -> Path:
    llm, judge_llm, agents, rm, rw = system or build(args, need_rm=policy != "meta")
    thr = {"tau_high": 3.5, "tau_low": 1.5, "tau_sim": 0.6}
    if Path(args.thresholds).exists():
        thr.update({k: v for k, v in json.loads(Path(args.thresholds).read_text(encoding="utf-8")).items() if k in thr})
    for k in thr:
        if getattr(args, k) is not None:
            thr[k] = getattr(args, k)
    thr["reassign_margin"] = args.reassign_margin
    cfg = AOPConfig(policy=policy, budget=budget, seed=args.seed or 0, **thr)
    aop = AOP(llm, agents, cfg, rm, rw)
    rows = load_split(args.dataset, args.split, args.data_dir, args.limit)
    out_dir = Path(args.results_dir) / f"{args.dataset}_{args.split}"
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"{cfg.name()}{('_' + args.tag) if args.tag else ''}.jsonl"
    done = set()
    if out.exists():
        done = {json.loads(x)["id"] for x in out.read_text(encoding="utf-8").splitlines() if x.strip()}
    todo = [r for r in rows if r["id"] not in done]
    print(f"== {out.name}: {len(rows)} queries ({len(done)} done, {len(todo)} to run) | thresholds {thr}")
    lock = threading.Lock()

    def work(row):
        ledger = Ledger()
        t0 = time.time()
        try:
            res = aop.run(row["question"], ledger)
            err = None
        except Exception as e:  # never lose the whole run because of one query
            res, err = None, repr(e)
        wall = time.time() - t0
        pred = res.answer if res else ""
        g = grade(row["question"], row["answer"], pred, None if args.no_judge else judge_llm)
        rec = {"id": row["id"], "condition": cfg.name(), "policy": policy, "budget": budget, "thresholds": thr,
               "question": row["question"], "gold": row["answer"], "pred": pred, **g,
               "cost": ledger.summary(), "wall_s": round(wall, 2), "error": err}
        if res:
            rec["trace"] = result_to_dict(res)
        return rec

    n_ok = n = 0
    with ThreadPoolExecutor(args.workers) as ex:
        futs = [ex.submit(work, r) for r in todo]
        for i, f in enumerate(as_completed(futs), 1):
            rec = f.result()
            with lock, out.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(rec, ensure_ascii=False, default=str) + "\n")
            n += 1
            n_ok += rec["correct"]
            if i % 10 == 0 or i == len(futs):
                print(f"  [{i}/{len(futs)}] running accuracy {n_ok / n:.1%}")
    st = agents["search_agent"].search.stats
    print(f"  search: {st}" + ("  <-- WARNING: search errors; run scripts/check_search.py" if st["error"] else ""))
    return out


def main():
    ap = argparse.ArgumentParser()
    add_common_args(ap)
    add_run_args(ap)
    ap.add_argument("--policy", choices=POLICIES, default="full")
    ap.add_argument("--budget", type=int, default=0)
    args = ap.parse_args()
    run_condition(args, args.policy, args.budget)


if __name__ == "__main__":
    main()
