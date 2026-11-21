"""Step 2 of the reward model: train the MLP and build the representative works.

    python scripts/train_reward_model.py

Also prints how many sub-tasks the default thresholds would flag, so you can tune
--tau-high / --tau-low before running experiments (AOP does not report its values).
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aop.prompts import AGENT_DESCRIPTIONS                       # noqa: E402
from aop.reward_model import RewardModel, RepresentativeWorks    # noqa: E402
from aop.system import add_common_args, load_dotenv, pick_embedder  # noqa: E402
from aop.llm import LLMConfig                                    # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    add_common_args(ap)
    ap.add_argument("--data", default="data/rm/rm_data.jsonl")
    ap.add_argument("--epochs", type=int, default=50)
    ap.add_argument("--batch", type=int, default=32)
    ap.add_argument("--lr", type=float, default=1e-3)
    ap.add_argument("--val-frac", type=float, default=0.15)
    ap.add_argument("--weight-decay", type=float, default=1e-2, help="0 = paper setting")
    ap.add_argument("--patience", type=int, default=8, help="early-stopping patience in epochs (0 = off)")
    ap.add_argument("--rep-min-score", type=float, default=4.0, help="score needed to become a representative work")
    ap.add_argument("--flag-rate", type=float, default=0.3, help="share of sub-tasks to flag for revision")
    ap.add_argument("--replan-rate", type=float, default=0.05, help="share of sub-tasks to replan")
    ap.add_argument("--thresholds", default="models/thresholds.json")
    args = ap.parse_args()
    load_dotenv()
    provider = args.provider or LLMConfig.from_env().provider

    rows = [json.loads(x) for x in Path(args.data).read_text(encoding="utf-8").splitlines() if x.strip()]
    print(f"{len(rows)} labelled (sub-task, agent) pairs from {len({r['qid'] for r in rows})} queries")
    emb = pick_embedder(args, provider)
    rm = RewardModel(emb)

    # split by query so no query leaks between train and validation
    qids = sorted({r["qid"] for r in rows})
    rng = np.random.default_rng(0)
    val_q = set(rng.choice(qids, max(1, int(len(qids) * args.val_frac)), replace=False)) if len(qids) > 1 else set()
    tr = [r for r in rows if r["qid"] not in val_q]
    va = [r for r in rows if r["qid"] in val_q]

    def xy(rs):
        X = rm.features([r["task"] for r in rs], [AGENT_DESCRIPTIONS[r["agent"]] for r in rs])
        return X, np.array([r["score"] for r in rs], dtype=np.float32)

    Xtr, ytr = xy(tr)
    val = xy(va) if va else None
    print(f"score distribution (train): " + ", ".join(f"{k}: {int(np.sum(ytr == k))}" for k in range(6)))
    hist = rm.mlp.fit(Xtr, ytr, epochs=args.epochs, batch=args.batch, lr=args.lr, val=val,
                      weight_decay=args.weight_decay, patience=args.patience or None)
    rm.save(args.reward_model)
    print("saved reward model ->", args.reward_model)
    if val:
        baseline = float(np.mean((ytr.mean() - val[1]) ** 2))
        v = float(np.mean((rm.mlp.forward(val[0]) - val[1]) ** 2))
        print(f"validation MSE = {v:.3f} | predict-the-mean baseline = {baseline:.3f} | "
              f"{'BETTER than' if v < baseline else 'NOT better than'} the baseline")

    # representative works: sub-tasks each agent solved well (training data only)
    rw = RepresentativeWorks(emb)
    for r in tr:
        if r["score"] >= args.rep_min_score:
            rw.add(r["task"], r["agent"])
    rw.save(args.rep_works)
    print("representative works per agent:", {a: len(w) for a, w in rw.works.items()}, "->", args.rep_works)

    # ---- calibrate thresholds on held-out sub-tasks (AOP does not report its values) ----
    held = va or tr
    by_task = {}
    for r in held:
        by_task.setdefault(r["task"], []).append(r)
    tasks = sorted(by_task)
    best = np.array([max(rm.score_all(t, AGENT_DESCRIPTIONS).values()) for t in tasks])
    true_best = np.array([max(r["score"] for r in by_task[t]) for t in tasks])
    tau_high = float(np.quantile(best, args.flag_rate))
    tau_low = float(np.quantile(best, args.replan_rate))
    sims = np.array([rw.similarity(t, by_task[t][0]["agent"])[0] for t in tasks])
    tau_sim = float(np.median(sims))
    print(f"\nbest-agent RM score on {len(tasks)} held-out sub-tasks: "
          f"p10={np.percentile(best,10):.2f} p50={np.percentile(best,50):.2f} p90={np.percentile(best,90):.2f}")
    flagged = best < tau_high
    print(f"calibrated: tau_high={tau_high:.3f} (flags {flagged.mean():.0%}), tau_low={tau_low:.3f} "
          f"(replans {np.mean(best < tau_low):.0%}), tau_sim={tau_sim:.3f} (half re-describe, half plan-in-detail)")
    if flagged.any() and (~flagged).any():
        print(f"sanity check - true best score of flagged sub-tasks {true_best[flagged].mean():.2f} "
              f"vs. not flagged {true_best[~flagged].mean():.2f} (flagged should be LOWER)")
    thr = {"tau_high": round(tau_high, 4), "tau_low": round(tau_low, 4), "tau_sim": round(tau_sim, 4),
           "flag_rate": args.flag_rate, "replan_rate": args.replan_rate, "n_heldout_subtasks": len(tasks)}
    Path(args.thresholds).write_text(json.dumps(thr, indent=1), encoding="utf-8")
    print("saved thresholds ->", args.thresholds, "(run_experiment.py uses them automatically)")
    if va:
        agree = []
        for t, rs in by_task.items():
            if len(rs) > 1 and len({r["score"] for r in rs}) > 1:
                pred = rm.score_all(t, {r["agent"]: AGENT_DESCRIPTIONS[r["agent"]] for r in rs})
                agree.append(max(pred, key=pred.get) == max(rs, key=lambda r: r["score"])["agent"])
        if agree:
            print(f"RM picks the better agent on {np.mean(agree):.0%} of {len(agree)} held-out sub-tasks "
                  f"where the two agents' scores differ (50% = chance)")

if __name__ == "__main__":
    main()
