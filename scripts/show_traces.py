"""Print readable traces from a results file: question, plan, coordination events, answer, cost.

    python scripts/show_traces.py results/sample_test/meta.jsonl
    python scripts/show_traces.py results/huskyqa_test/full.jsonl --n 5 --wrong
"""
import argparse
import json
import sys

sys.stdout.reconfigure(errors="replace")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("file")
    ap.add_argument("--n", type=int, default=10, help="how many queries to show")
    ap.add_argument("--wrong", action="store_true", help="only show wrong answers")
    args = ap.parse_args()
    shown = 0
    for line in open(args.file, encoding="utf-8"):
        r = json.loads(line)
        if args.wrong and r["correct"]:
            continue
        t = r.get("trace") or {}
        print("=" * 80)
        print("Q:   ", r["question"])
        print("GOLD:", r["gold"], "| PRED:", r["pred"], "| correct:", r["correct"])
        planned = {s["task"]: s["agent"] for s in t.get("initial_plan", [])}
        print("PLAN:  (* = agent changed by the reward model; planner's choice in brackets)")
        for s in t.get("final_plan", []):
            if planned.get(s["task"], s["agent"]) != s["agent"]:
                s = dict(s, agent=f"{s['agent']}* <{planned[s['task']]}>")
            deps = f"  (needs {s['depends_on']})" if s["depends_on"] else ""
            print(f"  {s['id']}. [{s['agent']}] {s['task']}{deps}")
        events = [e for e in t.get("events", []) if e["step"] != "reassign"]
        if events:
            print("COORDINATION:", events)
        print("RESULTS:")
        for s in t.get("subtask_results", []):
            print(f"  {s['id']}. {str(s['answer'])[:150]}")
        c = r["cost"]
        print(f"COST: {c['llm_calls']} calls, {c['prompt_tokens']}+{c['completion_tokens']} tokens")
        if r.get("error"):
            print("ERROR:", r["error"])
        shown += 1
        if shown >= args.n:
            break


if __name__ == "__main__":
    main()
