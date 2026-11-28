"""Summarize all runs: accuracy with 95% bootstrap CI, paired McNemar tests, costs,
and process statistics. Writes results/<run>/summary.md, summary.csv and plots.

    python scripts/analyze.py --run huskyqa_test
"""
import argparse
import csv
import json
import math
import re
from collections import Counter
from pathlib import Path

import numpy as np


def load(run_dir: Path) -> dict[str, dict[str, dict]]:
    conds = {}
    for f in sorted(run_dir.glob("*.jsonl")):
        recs = {}
        for line in f.read_text(encoding="utf-8").splitlines():
            if line.strip():
                r = json.loads(line)
                recs[r["id"]] = r
        if recs:
            conds[f.stem] = recs
    return conds


_NUM = re.compile(r"-?\d[\d,]*\.?\d*")


def near(pred, gold, tol=0.05) -> bool:
    """Secondary metric: first number in pred within 5% of gold's first number. Separates
    reasoning failures from facts that changed since HuskyQA's answers were written."""
    def first(x):
        m = _NUM.findall(str(x))
        try:
            return float(m[0].replace(",", "")) if m else None
        except ValueError:
            return None
    g, p = first(gold), first(pred)
    if g is None or p is None:
        return False
    return abs(p - g) <= tol * max(abs(g), 1e-9)


def bootstrap_ci(x: np.ndarray, n=2000, seed=0):
    rng = np.random.default_rng(seed)
    means = rng.choice(x, (n, len(x)), replace=True).mean(1)
    return np.percentile(means, 2.5), np.percentile(means, 97.5)


def mcnemar_p(a: list[bool], b: list[bool]) -> tuple[int, int, float]:
    """Exact two-sided McNemar test. Returns (#a-only correct, #b-only correct, p)."""
    n01 = sum(x and not y for x, y in zip(a, b))
    n10 = sum(y and not x for x, y in zip(a, b))
    n = n01 + n10
    if n == 0:
        return n01, n10, 1.0
    k = min(n01, n10)
    p = sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n * 2
    return n01, n10, min(1.0, p)


def sort_key(name: str):
    m = re.match(r"([a-z]+)(?:_B(\d+))?", name)
    order = {"meta": 0, "routing": 1, "full": 2, "check": 3, "revise": 4, "split": 5, "random": 6}
    return (int(m.group(2) or 0), order.get(m.group(1), 9), name)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", default="huskyqa_test")
    ap.add_argument("--results-dir", default="results")
    ap.add_argument("--common-only", action="store_true", default=True,
                    help="restrict every condition to the queries all conditions finished")
    args = ap.parse_args()
    run_dir = Path(args.results_dir) / args.run
    conds = load(run_dir)
    if not conds:
        raise SystemExit(f"no results in {run_dir}")
    ids = set.intersection(*(set(c) for c in conds.values())) if args.common_only else None
    names = sorted(conds, key=sort_key)
    print(f"{len(names)} conditions, {len(ids) if ids else 'all'} common queries\n")

    rows = []
    for name in names:
        recs = [r for i, r in conds[name].items() if ids is None or i in ids]
        acc = np.array([r["correct"] for r in recs], dtype=float)
        lo, hi = bootstrap_ci(acc)
        c = [r["cost"] for r in recs]
        events = [e for r in recs for e in (r.get("trace") or {}).get("events", [])]
        checks = [e for e in events if e["step"] == "check"]
        revs = Counter(e["action"] for e in events if e["step"] == "revise")
        row = {
            "condition": name, "n": len(recs), "acc": acc.mean(), "ci_lo": lo, "ci_hi": hi,
            "acc_5pct": np.mean([r["correct"] or near(r["pred"], r["gold"]) for r in recs]),
            "llm_calls": np.mean([x["llm_calls"] for x in c]),
            "coord_calls": np.mean([x["coordination_calls"] for x in c]),
            "check_calls": np.mean([x["check_calls"] for x in c]),
            "revision_calls": np.mean([x["revision_calls"] for x in c]),
            "prompt_tok": np.mean([x["prompt_tokens"] for x in c]),
            "compl_tok": np.mean([x["completion_tokens"] for x in c]),
            "latency_s": np.mean([x["llm_latency_s"] for x in c]),
            "checks_changed_plan": (np.mean([e["changed"] for e in checks]) if checks else float("nan")),
            "redescribe": revs["redescribe"], "plan_in_detail": revs["plan_in_detail"], "replan": revs["replan"],
            "reassign_per_q": sum(e["step"] == "reassign" for e in events) / len(recs),
            "errors": sum(bool(r.get("error")) for r in recs),
        }
        for ref in ("meta", "full"):
            if ref in conds and ref != name:
                common = sorted(i for i in conds[name] if i in conds[ref] and (ids is None or i in ids))
                a = [conds[name][i]["correct"] for i in common]
                b = [conds[ref][i]["correct"] for i in common]
                win, loss, p = mcnemar_p(a, b)
                row[f"vs_{ref}"] = f"+{win}/-{loss} (p={p:.3f})"
        rows.append(row)

    # ---------- markdown
    hdr = ["condition", "n", "acc", "95% CI", "acc ±5%", "LLM calls", "coord", "check", "revise",
           "prompt tok", "compl tok", "latency s", "vs meta", "vs full"]
    md = ["| " + " | ".join(hdr) + " |", "|" + "---|" * len(hdr)]
    for r in rows:
        md.append("| " + " | ".join([
            r["condition"], str(r["n"]), f"{r['acc']:.1%}", f"[{r['ci_lo']:.1%}, {r['ci_hi']:.1%}]", f"{r['acc_5pct']:.1%}",
            f"{r['llm_calls']:.1f}", f"{r['coord_calls']:.2f}", f"{r['check_calls']:.2f}", f"{r['revision_calls']:.2f}",
            f"{r['prompt_tok']:.0f}", f"{r['compl_tok']:.0f}", f"{r['latency_s']:.1f}",
            r.get("vs_meta", "-"), r.get("vs_full", "-")]) + " |")
    proc = ["", "### Process statistics", "",
            "| condition | checks that changed plan | re-describe | plan-in-detail | replan | RM reassignments / query | errors |",
            "|---|---|---|---|---|---|---|"]
    for r in rows:
        ccp = "-" if math.isnan(r["checks_changed_plan"]) else f"{r['checks_changed_plan']:.0%}"
        proc.append(f"| {r['condition']} | {ccp} | {r['redescribe']} | {r['plan_in_detail']} | {r['replan']} | "
                    f"{r['reassign_per_q']:.2f} | {r['errors']} |")
    # how many final answers / plans each condition changed relative to meta
    if "meta" in conds:
        chg = ["", "### Effect of coordination relative to meta", "",
               "| condition | plans changed | answers changed | wrong->right | right->wrong |", "|---|---|---|---|---|"]
        for name in names:
            if name == "meta":
                continue
            common = [i for i in conds[name] if i in conds["meta"] and (ids is None or i in ids)]
            a, b = conds[name], conds["meta"]
            pc = sum(1 for i in common if [s["task"] for s in (a[i].get("trace") or {}).get("final_plan", [])]
                     != [s["task"] for s in (b[i].get("trace") or {}).get("final_plan", [])])
            ac = sum(1 for i in common if a[i]["pred"] != b[i]["pred"])
            up = sum(1 for i in common if a[i]["correct"] and not b[i]["correct"])
            dn = sum(1 for i in common if b[i]["correct"] and not a[i]["correct"])
            chg.append(f"| {name} | {pc}/{len(common)} | {ac} | {up} | {dn} |")
        proc += chg
    note = ["", "_acc ±5% counts numeric answers within 5% of gold (facts drift over time); vs X = +queries only this condition got right / -queries only X got right, "
                "exact McNemar p-value on the same queries. Costs are means per query; "
                "latency = sum of LLM call latencies (cached calls keep their original latency)._"]
    text = "\n".join([f"## Results: {args.run}", ""] + md + proc + note)
    (run_dir / "summary.md").write_text(text, encoding="utf-8")
    print(text)

    with (run_dir / "summary.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()) + ["vs_meta", "vs_full"], extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)

    # ---------- plots
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("\n(matplotlib not installed: skipping plots)")
        return
    by = {r["condition"]: r for r in rows}
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))
    for pol, color in [("check", "#2C5C8A"), ("revise", "#C2552B"), ("split", "#6B7280"), ("random", "#A3A3A3")]:
        pts = sorted((int(k.split("_B")[1]), v) for k, v in by.items() if re.fullmatch(f"{pol}_B\\d+", k))
        if pts:
            axes[0].errorbar([b for b, _ in pts], [v["acc"] * 100 for _, v in pts],
                             yerr=[[(v["acc"] - v["ci_lo"]) * 100 for _, v in pts], [(v["ci_hi"] - v["acc"]) * 100 for _, v in pts]],
                             marker="o", capsize=3, label=pol, color=color)
            axes[1].plot([v["prompt_tok"] + v["compl_tok"] for _, v in pts], [v["acc"] * 100 for _, v in pts],
                         marker="o", label=pol, color=color)
    for ref, ls in (("meta", ":"), ("full", "--")):
        if ref in by:
            axes[0].axhline(by[ref]["acc"] * 100, ls=ls, color="k", lw=1, label=ref)
            axes[1].scatter([by[ref]["prompt_tok"] + by[ref]["compl_tok"]], [by[ref]["acc"] * 100], color="k", marker="x")
            axes[1].annotate(ref, (by[ref]["prompt_tok"] + by[ref]["compl_tok"], by[ref]["acc"] * 100))
    axes[0].set(xlabel="coordination budget B (extra LLM calls / query)", ylabel="accuracy (%)", title="Accuracy vs. budget")
    axes[1].set(xlabel="tokens per query", ylabel="accuracy (%)", title="Accuracy vs. token cost")
    for ax in axes:
        ax.legend(frameon=False)
        ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(run_dir / "accuracy_vs_budget.png", dpi=160)
    print(f"\nplots -> {run_dir / 'accuracy_vs_budget.png'}")


if __name__ == "__main__":
    main()
