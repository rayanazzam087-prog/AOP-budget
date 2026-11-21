"""Make the figure used in the README, paper and slides from the saved results.

    python scripts/make_figures.py
"""
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

PAPER_AOP = 43.7          # AOP (Li et al., ICLR 2025), Table 1, GPT-4o
PAPER_META = 30.0         # their Meta-Agent baseline
RUNS = [("GPT-4o", "results_gpt4o/huskyqa_test"), ("GPT-4o-mini", "results/huskyqa_test")]
POLICIES = [("check", "Check-only", "#2C5C8A", "o"), ("revise", "Revise-only", "#C2552B", "s"),
            ("random", "Random (control)", "#8A8A8A", "^")]


def acc(path: Path):
    if not path.exists():
        return None
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    return 100 * np.mean([r["correct"] for r in rows])


def main():
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.6), sharey=False)
    for ax, (model, d) in zip(axes, RUNS):
        d = Path(d)
        if not d.exists():
            ax.set_visible(False)
            continue
        for key, label, color, marker in POLICIES:
            xs, ys = [], []
            for b in (1, 2, 4):
                a = acc(d / f"{key}_B{b}.jsonl")
                if a is not None:
                    xs.append(b)
                    ys.append(a)
            if xs:
                ax.plot(xs, ys, marker=marker, color=color, label=label, lw=2)
        meta, full = acc(d / "meta.jsonl"), acc(d / "full.jsonl")
        if meta is not None and full is not None and abs(meta - full) < 0.05:
            ax.axhline(meta, color="black", ls="--", lw=1.5,
                       label=f"No coordination = Full AOP ({meta:.1f}%)")
        else:
            if meta is not None:
                ax.axhline(meta, color="black", ls=":", lw=1.5, label=f"No coordination (meta) {meta:.1f}%")
            if full is not None:
                ax.axhline(full, color="black", ls="--", lw=1.5, label=f"Full AOP (unlimited) {full:.1f}%")
        if model == "GPT-4o":
            ax.axhline(PAPER_AOP, color="#2E7D32", ls="-.", lw=1.5, label=f"AOP paper, reported {PAPER_AOP}%")
        mid = meta if meta is not None else 40
        ax.set_ylim(mid - 8, mid + 8)
        ax.set_xticks([1, 2, 4])
        ax.set_xlabel("Coordination budget B (extra LLM calls per question)")
        ax.set_ylabel("Accuracy on HuskyQA test (%)")
        ax.set_title(f"{model} (292 questions)")
        ax.grid(alpha=0.3)
        ax.legend(frameon=False, fontsize=8.5, loc="lower right")
    fig.tight_layout()
    out = Path("figures")
    out.mkdir(exist_ok=True)
    fig.savefig(out / "accuracy_vs_budget.png", dpi=160)
    print("saved figures/accuracy_vs_budget.png")


if __name__ == "__main__":
    sys.exit(main())
