"""Update repository documentation using corrected results.
No paid API calls and no GitHub push.
"""

import csv
import json
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path


def read_rows(file):
    return [
        json.loads(line)
        for line in file.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def accuracy(rows):
    return sum(row["correct"] for row in rows) / len(rows)


def mean_tokens(rows):
    return sum(
        row["cost"]["prompt_tokens"]
        + row["cost"]["completion_tokens"]
        for row in rows
    ) / len(rows)


def transitions(rows, baseline):
    baseline = {str(row["id"]): row for row in baseline}

    fixed = sum(
        row["correct"] and not baseline[str(row["id"])]["correct"]
        for row in rows
    )
    broken = sum(
        not row["correct"] and baseline[str(row["id"])]["correct"]
        for row in rows
    )

    return fixed, broken


def validate_results(root):
    specifications = [
        (
            "GPT-4o",
            "results_corrected_gpt4o",
            ("check", "revise", "random"),
        ),
        (
            "GPT-4o-mini",
            "results_corrected_mini",
            ("check", "revise", "split", "random"),
        ),
    ]

    datasets = {}
    reference = None

    for model, directory, policies in specifications:
        folder = root / directory / "huskyqa_test"
        expected = {"meta", "routing", "full"} | {
            f"{policy}_B{budget}"
            for policy in policies
            for budget in (1, 2, 4)
        }

        files = {
            file.stem: file
            for file in folder.glob("*.jsonl")
        }

        if set(files) != expected:
            raise ValueError(
                f"Missing or unexpected conditions in {folder}"
            )

        datasets[model] = {}

        for condition, file in files.items():
            rows = read_rows(file)

            if len(rows) != 292:
                raise ValueError(f"Expected 292 rows in {file}")

            if len({str(row["id"]) for row in rows}) != 292:
                raise ValueError(f"Duplicate IDs in {file}")

            questions = {
                str(row["id"]): (
                    row["question"],
                    row["gold"],
                )
                for row in rows
            }

            if reference is None:
                reference = questions

            if questions != reference:
                raise ValueError(
                    f"Question or gold-answer mismatch in {file}"
                )

            for row in rows:
                if row.get("error"):
                    raise ValueError(
                        f"Pipeline error in {file}, ID {row['id']}"
                    )

                if not isinstance(row.get("judge"), bool):
                    raise ValueError(
                        f"Missing judge label in {file}, ID {row['id']}"
                    )

                if row["correct"] != row["judge"]:
                    raise ValueError(
                        f"Correctness/judge mismatch in {file}"
                    )

                calls = row["cost"]["coordination_calls"]

                if condition in ("meta", "routing"):
                    if calls != 0:
                        raise ValueError(
                            f"Unexpected coordination calls in {file}"
                        )

                if "_B" in condition:
                    if calls > row["budget"]:
                        raise ValueError(
                            f"Budget violation in {file}, ID {row['id']}"
                        )

            datasets[model][condition] = rows

    return datasets


def run_analysis():
    for directory in (
        "results_corrected_mini",
        "results_corrected_gpt4o",
    ):
        subprocess.run(
            [
                sys.executable,
                "scripts/analyze.py",
                "--run",
                "huskyqa_test",
                "--results-dir",
                directory,
            ],
            check=True,
        )

    subprocess.run(
        [
            sys.executable,
            "scripts/compare_policies.py",
            "--mini-dir",
            "results_corrected_mini/huskyqa_test",
            "--gpt4o-dir",
            "results_corrected_gpt4o/huskyqa_test",
            "--out",
            "analysis_corrected",
        ],
        check=True,
    )


def read_csv(file):
    with file.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def main():
    root = Path.cwd()

    if not (root / "aop/pipeline.py").exists():
        raise ValueError(
            "Run this script from your main project folder."
        )

    datasets = validate_results(root)
    print("Validated 27 conditions with 292 matching questions each.")

    run_analysis()

    analysis = root / "analysis_corrected"
    direct = read_csv(analysis / "check_vs_revise.csv")
    exploratory = read_csv(
        analysis / "vs_routing_exploratory.csv"
    )

    if len(direct) != 6 or len(exploratory) != 23:
        raise ValueError(
            "Unexpected comparison counts. Documentation not replaced."
        )

    if any(
        float(row["p"]) < 0.05
        for row in direct + exploratory
    ):
        raise ValueError(
            "Results differ from the reviewed significance conclusion. "
            "Review before updating documentation."
        )

    if any(
        float(row["a_tokens"]) <= float(row["b_tokens"])
        for row in direct
    ):
        raise ValueError(
            "Token results differ from the reviewed conclusion."
        )

    overview = [
        "| Model | Meta | Routing only | Full implementation | "
        "Full token overhead vs meta |",
        "|---|---|---|---|---|",
    ]

    effects = [
        "| Model | Reference | Full fixes | Full breaks | "
        "Full token overhead |",
        "|---|---|---|---|---|",
    ]

    for model, conditions in datasets.items():
        meta = conditions["meta"]
        routing = conditions["routing"]
        full = conditions["full"]

        overhead = (
            mean_tokens(full) / mean_tokens(meta) - 1
        ) * 100

        overview.append(
            f"| {model} | {accuracy(meta):.1%} | "
            f"{accuracy(routing):.1%} | {accuracy(full):.1%} | "
            f"{overhead:+.1f}% |"
        )

        for reference_name in ("meta", "routing"):
            baseline = conditions[reference_name]
            fixed, broken = transitions(full, baseline)

            extra = (
                mean_tokens(full) / mean_tokens(baseline) - 1
            ) * 100

            effects.append(
                f"| {model} | {reference_name} | {fixed} | "
                f"{broken} | {extra:+.1f}% |"
            )

    conclusion = (
        "No statistically significant accuracy difference was detected "
        "between plan checking and subtask revision in the six direct "
        "paired comparisons. Checking consumed more tokens in every "
        "comparison. No coordinated condition significantly outperformed "
        "routing alone under the reported exact McNemar tests. "
        "Non-significance does not establish equivalence."
    )

    notes = """
## Interpretation and accounting

- B is a maximum allowance of coordination calls. It does not match
  realized calls, tokens, dollars, or wall-clock time. Policies can stop early.
- Token totals include pipeline prompt and completion tokens, including
  cached calls at their original token counts.
- Evaluation calls and reward-model CPU overhead are excluded.
- Reward-model routing uses CPU computation but no LLM API call.
- Changed plans can change execution costs.
- Summed historical LLM latency excludes search time and is not measured
  end-to-end runtime.
- Direct tests use Holm correction across six comparisons.
- Exploratory routing comparisons use a separate Holm correction across
  23 comparisons.
- Bootstrap intervals are pointwise percentile intervals, not simultaneous
  intervals. With few discordant outcomes, they can disagree with exact
  tests. Significance claims follow the reported exact tests.
- Numerical proximity does not diagnose factual drift or an error's cause.
  The secondary numeric metric counts recorded correctness OR first-number
  proximity within 5%.
- Task-text plan-change counts exclude changes solely to assignments
  or dependencies.
- Detector edit percentages are per detector call, not per question.
- Recorded-output checks do not establish that every internal agent/tool
  action succeeded or that every judge label is correct.
- Trace-level review remains separate.
"""

    readme = """# AOP-Budget: checking versus revision under a coordination-call allowance

COE549 Advanced LLM final project - Rayan Azzam.

Independent reimplementation of Agent-Oriented Planning (AOP), extended
with a coordination-budget controller and per-stage cost accounting.

## Corrected evaluation

The corrected grid contains 27 configurations: 12 GPT-4o and 15 GPT-4o-mini.
Every configuration uses the same 292 HuskyQA test questions, giving
7,884 question-condition outcomes.

"""

    readme += "\n".join(overview)
    readme += "\n\n" + conclusion + "\n\n"

    readme += """See [RESULTS.md](RESULTS.md) for corrected tables and qualifications.

![Corrected GPT-4o results](figures/corrected_gpt4o.png)

![Corrected GPT-4o-mini results](figures/corrected_mini.png)

## Conditions

- `meta`: decomposition, execution, aggregation; no reward-model routing.
- `routing`: reward-model routing without checking or revision.
- `full`: detector and revision procedure without the experimental B
  allowance. Other implementation limits still apply.
- `check`, `revise`, `split`, `random`: coordination allocation policies
  at B = 1, 2, 4.

GPT-4o does not include split conditions. This omission followed inspection
of mini results and is an exploratory design decision.

## Relationship to AOP

This is an independent reimplementation, not an exact reproduction.
Differences include:

- Wikipedia search instead of Bing.
- Substitute reward-model training data.
- Independently written prompts.
- GPT-4o-mini scoring and answer judging.
- Thresholds calibrated on a different scoring scale.
- Frozen representative works during testing.
- No recursive revision of newly created subtasks.
- A reward model trained with mini agents and reused for GPT-4o.

Original paper:
[Agent-Oriented Planning in Multi-Agent Systems](https://arxiv.org/abs/2410.02189).

## Corrected and historical outputs

Use `results_corrected_gpt4o`, `results_corrected_mini`, and
`analysis_corrected`.

The older `results` and `results_gpt4o` folders and their figures are
historical outputs. Do not mix historical and corrected results.

Corrections accept detector changes to assignments and dependencies,
normalize scalar dependency fields, prevent extra JSON repair calls during
coordination, and add routing-only controls.

Authentication-failure rows were backed up and retried without selecting
outcomes by correctness.

## Setup

Use Python 3.12 and install dependencies:

    python -m pip install -r requirements.txt
    python -m pytest -q

Provide the original 292-question `data/huskyqa/test.jsonl`, the saved model
and thresholds in `models`, and local API configuration in `.env`.
Never commit credentials or caches.

## Reproduce evaluation

These commands can incur API charges. Identical cached calls are reused
when the original caches are available. Corrected reruns are not
independent replications.

    python scripts/sweep.py --provider openai --model gpt-4o-mini --judge-model gpt-4o-mini --search wikipedia --embedder minilm --workers 2 --results-dir results_corrected_mini

    python scripts/sweep.py --provider openai --model gpt-4o --judge-model gpt-4o-mini --search wikipedia --embedder minilm --policies check,revise,random --workers 2 --results-dir results_corrected_gpt4o

Saved rows resume automatically. Provenance manifests guard against
mixing incompatible code or configurations.

## Offline analysis

These commands make no paid API calls:

    python scripts/analyze.py --run huskyqa_test --results-dir results_corrected_mini

    python scripts/analyze.py --run huskyqa_test --results-dir results_corrected_gpt4o

    python scripts/compare_policies.py --mini-dir results_corrected_mini/huskyqa_test --gpt4o-dir results_corrected_gpt4o/huskyqa_test --out analysis_corrected

## Scope limits

Development included inspection of test traces. Model aliases rather than
exact model snapshots were recorded. Shared cached generations do not
provide independent replications. Findings concern this benchmark,
implementation, and model pair.

Analysis followed observation of outcomes; no preregistration is claimed.

The code agent executes generated Python in a subprocess.
It is not a security sandbox.
"""

    readme += "\n" + notes

    results = [
        "# Corrected results\n\n",
        "These results supersede the historical headline results.\n\n",
        conclusion,
        "\n\n## Direct checking versus revision\n\n",
        (analysis / "check_vs_revise.md").read_text(
            encoding="utf-8"
        ),
        "\n\n## Exploratory comparisons against routing only\n\n",
        (analysis / "vs_routing_exploratory.md").read_text(
            encoding="utf-8"
        ),
        "\n\n## Matched outcome transitions and costs\n\n",
        "\n".join(effects),
        "\n\nFixes and breaks are paired outcome transitions, "
        "not diagnoses of why answers changed.\n",
    ]

    for model, directory in [
        ("GPT-4o", "results_corrected_gpt4o"),
        ("GPT-4o-mini", "results_corrected_mini"),
    ]:
        summary_file = (
            root / directory / "huskyqa_test" / "summary.md"
        )
        summary = summary_file.read_text(encoding="utf-8")

        summary = summary.replace(
            "Effect of coordination relative to meta",
            "Outcome changes relative to meta "
            "(routing and coordination combined)",
        )
        summary = summary.replace(
            "| plans changed |",
            "| task-text plans changed |",
        )
        summary = summary.replace(
            "(facts drift over time)",
            "(numerical proximity; cause not inferred)",
        )

        results.extend([
            f"\n\n## Full {model} summary\n\n",
            summary,
        ])

    results.extend(["\n\n", notes])

    backup = (
        root
        / "documentation_backups"
        / datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    )
    backup.mkdir(parents=True)

    for filename in ("README.md", "RESULTS.md"):
        original = root / filename
        if original.exists():
            shutil.copy2(original, backup / filename)

    figures = root / "figures"
    figures.mkdir(exist_ok=True)

    for directory, label in [
        ("results_corrected_gpt4o", "gpt4o"),
        ("results_corrected_mini", "mini"),
    ]:
        target = figures / f"corrected_{label}.png"

        if target.exists():
            shutil.copy2(target, backup / target.name)

        source = (
            root
            / directory
            / "huskyqa_test"
            / "accuracy_vs_budget.png"
        )
        shutil.copy2(source, target)

    (root / "README.md").write_text(
        readme,
        encoding="utf-8",
    )
    (root / "RESULTS.md").write_text(
        "".join(results),
        encoding="utf-8",
    )

    print("\nPrevious documentation backed up:", backup)
    print("UPDATED: README.md and RESULTS.md")
    print("UPDATED: corrected GPT-4o and mini figures")
    print("No paid API calls or GitHub push performed.")


if __name__ == "__main__":
    main()