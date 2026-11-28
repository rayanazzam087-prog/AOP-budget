"""Run the full experimental grid (14 conditions by default):

  meta, full, and {check, revise, split, random} x B in {1, 2, 4}

    python scripts/sweep.py --limit 50          # pilot
    python scripts/sweep.py                      # all 292 test queries

Thanks to the LLM cache, conditions share identical calls (same initial plan, same agent
answers when the sub-task is unchanged), which makes the comparison paired and cheaper.
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aop.system import add_common_args, build              # noqa: E402
from run_experiment import add_run_args, run_condition     # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    add_common_args(ap)
    add_run_args(ap)
    ap.add_argument("--budgets", default="1,2,4")
    ap.add_argument("--policies", default="check,revise,split,random")
    ap.add_argument("--skip-baselines", action="store_true")
    args = ap.parse_args()
    system = build(args, need_rm=True)
    if system[3] is None:
        sys.exit("No reward model found. Run collect_rm_data.py and train_reward_model.py first.")
    conds = [] if args.skip_baselines else [("meta", 0), ("routing", 0), ("full", 0)]
    conds += [(p, int(b)) for b in args.budgets.split(",") for p in args.policies.split(",")]
    for policy, budget in conds:
        run_condition(args, policy, budget, system)
    print("\nDone. Now: python scripts/analyze.py")


if __name__ == "__main__":
    main()
