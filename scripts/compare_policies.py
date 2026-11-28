"""Offline paired comparisons; never calls a model or changes saved predictions."""
import argparse
import csv
import json
import math
from pathlib import Path

import numpy as np


def load(path):
    records = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            row = json.loads(line)
            key = str(row["id"])
            if key in records:
                raise ValueError(f"Duplicate ID {key} in {path}")
            if not isinstance(row["correct"], bool):
                raise ValueError(f"Non-boolean correctness in {path}: {key}")
            records[key] = row
    if not records:
        raise ValueError(f"Empty results: {path}")
    return records


def compare(left, right, model, condition_a, condition_b, resamples=10000):
    if set(left) != set(right):
        raise ValueError(f"Question IDs differ: {model} {condition_a} vs {condition_b}")
    ids = sorted(left)
    for key in ids:
        if (left[key]["question"], left[key]["gold"]) != (right[key]["question"], right[key]["gold"]):
            raise ValueError(f"Question/gold mismatch: {key}")
    a = np.array([left[i]["correct"] for i in ids], dtype=int)
    b = np.array([right[i]["correct"] for i in ids], dtype=int)
    wins = int(np.sum((a == 1) & (b == 0)))
    losses = int(np.sum((a == 0) & (b == 1)))
    n = wins + losses
    p = min(1.0, 2 * sum(math.comb(n, k) for k in range(min(wins, losses) + 1)) / 2**n) if n else 1.0
    delta = a - b
    draws = np.random.default_rng(0).choice(delta, (resamples, len(ids)), replace=True).mean(axis=1)
    lo, hi = np.percentile(draws * 100, [2.5, 97.5])
    def mean_cost(rows, key):
        return sum(rows[i]["cost"][key] for i in ids) / len(ids)
    def tokens(rows):
        return mean_cost(rows, "prompt_tokens") + mean_cost(rows, "completion_tokens")
    return dict(model=model, a=condition_a, b=condition_b, n=len(ids),
                a_correct=int(a.sum()), b_correct=int(b.sum()),
                difference_pp=float(delta.mean() * 100), ci_lo_pp=float(lo), ci_hi_pp=float(hi),
                a_only_correct=wins, b_only_correct=losses, p=p,
                a_tokens=tokens(left), b_tokens=tokens(right),
                a_coord_calls=mean_cost(left, "coordination_calls"),
                b_coord_calls=mean_cost(right, "coordination_calls"),
                a_errors=sum(bool(left[i].get("error")) for i in ids),
                b_errors=sum(bool(right[i].get("error")) for i in ids))


def holm(rows):
    """Adjust across exactly the comparisons supplied; no independence assumption."""
    ordered = sorted(range(len(rows)), key=lambda i: rows[i]["p"])
    previous = 0.0
    for rank, i in enumerate(ordered):
        previous = max(previous, min(1.0, (len(rows) - rank) * rows[i]["p"]))
        rows[i]["p_holm"] = previous


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--gpt4o-dir", default="results_gpt4o/huskyqa_test")
    ap.add_argument("--mini-dir", default="results/huskyqa_test")
    ap.add_argument("--out", default="analysis_paired")
    args = ap.parse_args()
    direct, secondary = [], []
    for label, directory in [("GPT-4o", args.gpt4o_dir), ("GPT-4o-mini", args.mini_dir)]:
        folder = Path(directory)
        conds = {f.stem: load(f) for f in folder.glob("*.jsonl")}
        for budget in (1, 2, 4):
            a, b = f"check_B{budget}", f"revise_B{budget}"
            if a not in conds or b not in conds:
                raise ValueError(f"Missing {a} or {b} in {folder}")
            direct.append(compare(conds[a], conds[b], label, a, b))
        if "routing" in conds:
            for name in sorted(conds):
                if name == "full" or name.startswith(("check_B", "revise_B", "split_B", "random_B")):
                    secondary.append(compare(conds[name], conds["routing"], label, name, "routing"))
    holm(direct)
    holm(secondary)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    for name, rows in [("check_vs_revise", direct), ("vs_routing_exploratory", secondary)]:
        if not rows:
            continue
        with (out / f"{name}.csv").open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
        lines = [f"# {name}", "",
                 "| Model | A vs B | Correct A / B | Difference pp [paired 95% CI] | A-only / B-only | p / Holm p | Tokens A / B |",
                 "|---|---|---|---|---|---|---|"]
        for r in rows:
            lines.append(f"| {r['model']} | {r['a']} vs {r['b']} | {r['a_correct']} / {r['b_correct']} | "
                         f"{r['difference_pp']:+.2f} [{r['ci_lo_pp']:+.2f}, {r['ci_hi_pp']:+.2f}] | "
                         f"{r['a_only_correct']} / {r['b_only_correct']} | {r['p']:.4f} / {r['p_holm']:.4f} | "
                         f"{r['a_tokens']:.1f} / {r['b_tokens']:.1f} |")
        lines += ["", f"Holm correction covers {len(rows)} comparisons in this table. "
                  "Intervals are pointwise paired percentile bootstrap intervals (10,000 resamples, seed 0). "
                  "Failures remain in the denominator. Non-significance does not establish equivalence. "
                  "Analysis performed after outcomes were available; no preregistration is claimed."]
        (out / f"{name}.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
        print("\n".join(lines))
    if not secondary:
        print("No routing-only baseline found. No coordination-vs-routing comparison was calculated.")


if __name__ == "__main__":
    main()
