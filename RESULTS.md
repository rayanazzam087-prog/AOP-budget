# Corrected results

These results supersede the historical headline results.

No statistically significant accuracy difference was detected between plan checking and subtask revision in the six direct paired comparisons. Checking consumed more tokens in every comparison. No coordinated condition significantly outperformed routing alone under the reported exact McNemar tests. Non-significance does not establish equivalence.

## Direct checking versus revision

# check_vs_revise

| Model | A vs B | Correct A / B | Difference pp [paired 95% CI] | A-only / B-only | p / Holm p | Tokens A / B |
|---|---|---|---|---|---|---|
| GPT-4o | check_B1 vs revise_B1 | 129 / 128 | +0.34 [-2.40, +3.42] | 10 / 9 | 1.0000 / 1.0000 | 4482.3 / 3915.5 |
| GPT-4o | check_B2 vs revise_B2 | 129 / 126 | +1.03 [-2.05, +4.11] | 12 / 9 | 0.6636 / 1.0000 | 4721.9 / 4150.6 |
| GPT-4o | check_B4 vs revise_B4 | 129 / 126 | +1.03 [-2.05, +4.11] | 12 / 9 | 0.6636 / 1.0000 | 5004.9 / 4176.0 |
| GPT-4o-mini | check_B1 vs revise_B1 | 100 / 102 | -0.68 [-2.05, +0.68] | 1 / 3 | 0.6250 / 1.0000 | 4095.4 / 3618.8 |
| GPT-4o-mini | check_B2 vs revise_B2 | 100 / 101 | -0.34 [-2.05, +1.37] | 3 / 4 | 1.0000 / 1.0000 | 4155.3 / 3874.5 |
| GPT-4o-mini | check_B4 vs revise_B4 | 100 / 101 | -0.34 [-2.05, +1.37] | 3 / 4 | 1.0000 / 1.0000 | 4181.5 / 3910.1 |

Holm correction covers 6 comparisons in this table. Intervals are pointwise paired percentile bootstrap intervals (10,000 resamples, seed 0). Failures remain in the denominator. Non-significance does not establish equivalence. Analysis performed after outcomes were available; no preregistration is claimed.


## Exploratory comparisons against routing only

# vs_routing_exploratory

| Model | A vs B | Correct A / B | Difference pp [paired 95% CI] | A-only / B-only | p / Holm p | Tokens A / B |
|---|---|---|---|---|---|---|
| GPT-4o | check_B1 vs routing | 129 / 129 | +0.00 [-2.05, +2.05] | 5 / 5 | 1.0000 / 1.0000 | 4482.3 / 3516.7 |
| GPT-4o | check_B2 vs routing | 129 / 129 | +0.00 [-2.05, +2.05] | 5 / 5 | 1.0000 / 1.0000 | 4721.9 / 3516.7 |
| GPT-4o | check_B4 vs routing | 129 / 129 | +0.00 [-2.05, +2.05] | 5 / 5 | 1.0000 / 1.0000 | 5004.9 / 3516.7 |
| GPT-4o | full vs routing | 127 / 129 | -0.68 [-3.42, +2.05] | 8 / 10 | 0.8145 / 1.0000 | 5414.3 / 3516.7 |
| GPT-4o | random_B1 vs routing | 131 / 129 | +0.68 [-1.71, +3.08] | 7 / 5 | 0.7744 / 1.0000 | 4392.6 / 3516.7 |
| GPT-4o | random_B2 vs routing | 127 / 129 | -0.68 [-3.77, +2.40] | 10 / 12 | 0.8318 / 1.0000 | 4985.1 / 3516.7 |
| GPT-4o | random_B4 vs routing | 127 / 129 | -0.68 [-3.77, +2.40] | 9 / 11 | 0.8238 / 1.0000 | 5564.9 / 3516.7 |
| GPT-4o | revise_B1 vs routing | 128 / 129 | -0.34 [-2.74, +1.71] | 5 / 6 | 1.0000 / 1.0000 | 3915.5 / 3516.7 |
| GPT-4o | revise_B2 vs routing | 126 / 129 | -1.03 [-3.42, +1.37] | 5 / 8 | 0.5811 / 1.0000 | 4150.6 / 3516.7 |
| GPT-4o | revise_B4 vs routing | 126 / 129 | -1.03 [-3.42, +1.37] | 5 / 8 | 0.5811 / 1.0000 | 4176.0 / 3516.7 |
| GPT-4o-mini | check_B1 vs routing | 100 / 99 | +0.34 [+0.00, +1.03] | 1 / 0 | 1.0000 / 1.0000 | 4095.4 / 3199.3 |
| GPT-4o-mini | check_B2 vs routing | 100 / 99 | +0.34 [+0.00, +1.03] | 1 / 0 | 1.0000 / 1.0000 | 4155.3 / 3199.3 |
| GPT-4o-mini | check_B4 vs routing | 100 / 99 | +0.34 [+0.00, +1.03] | 1 / 0 | 1.0000 / 1.0000 | 4181.5 / 3199.3 |
| GPT-4o-mini | full vs routing | 102 / 99 | +1.03 [-0.68, +2.74] | 5 / 2 | 0.4531 / 1.0000 | 4870.0 / 3199.3 |
| GPT-4o-mini | random_B1 vs routing | 100 / 99 | +0.34 [+0.00, +1.03] | 1 / 0 | 1.0000 / 1.0000 | 4036.0 / 3199.3 |
| GPT-4o-mini | random_B2 vs routing | 103 / 99 | +1.37 [+0.34, +2.74] | 4 / 0 | 0.1250 / 1.0000 | 4530.9 / 3199.3 |
| GPT-4o-mini | random_B4 vs routing | 102 / 99 | +1.03 [-0.68, +2.74] | 5 / 2 | 0.4531 / 1.0000 | 4940.9 / 3199.3 |
| GPT-4o-mini | revise_B1 vs routing | 102 / 99 | +1.03 [+0.00, +2.40] | 3 / 0 | 0.2500 / 1.0000 | 3618.8 / 3199.3 |
| GPT-4o-mini | revise_B2 vs routing | 101 / 99 | +0.68 [-1.03, +2.40] | 4 / 2 | 0.6875 / 1.0000 | 3874.5 / 3199.3 |
| GPT-4o-mini | revise_B4 vs routing | 101 / 99 | +0.68 [-1.03, +2.40] | 4 / 2 | 0.6875 / 1.0000 | 3910.1 / 3199.3 |
| GPT-4o-mini | split_B1 vs routing | 100 / 99 | +0.34 [+0.00, +1.03] | 1 / 0 | 1.0000 / 1.0000 | 4095.4 / 3199.3 |
| GPT-4o-mini | split_B2 vs routing | 103 / 99 | +1.37 [+0.34, +2.74] | 4 / 0 | 0.1250 / 1.0000 | 4540.0 / 3199.3 |
| GPT-4o-mini | split_B4 vs routing | 102 / 99 | +1.03 [-0.68, +2.74] | 5 / 2 | 0.4531 / 1.0000 | 4888.1 / 3199.3 |

Holm correction covers 23 comparisons in this table. Intervals are pointwise paired percentile bootstrap intervals (10,000 resamples, seed 0). Failures remain in the denominator. Non-significance does not establish equivalence. Analysis performed after outcomes were available; no preregistration is claimed.


## Matched outcome transitions and costs

| Model | Reference | Full fixes | Full breaks | Full token overhead |
|---|---|---|---|---|
| GPT-4o | meta | 10 | 10 | +52.3% |
| GPT-4o | routing | 8 | 10 | +54.0% |
| GPT-4o-mini | meta | 6 | 6 | +48.5% |
| GPT-4o-mini | routing | 5 | 2 | +52.2% |

Fixes and breaks are paired outcome transitions, not diagnoses of why answers changed.


## Full GPT-4o summary

## Results: huskyqa_test

| condition | n | acc | 95% CI | acc ±5% | LLM calls | coord | check | revise | prompt tok | compl tok | latency s | vs meta | vs full |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| meta | 292 | 43.5% | [38.0%, 49.0%] | 68.2% | 8.0 | 0.00 | 0.00 | 0.00 | 2718 | 837 | 14.2 | - | +10/-10 (p=1.000) |
| routing | 292 | 44.2% | [38.4%, 49.7%] | 68.2% | 8.0 | 0.00 | 0.00 | 0.00 | 2700 | 817 | 14.1 | +3/-1 (p=0.625) | +10/-8 (p=0.815) |
| full | 292 | 43.5% | [37.7%, 49.0%] | 68.8% | 10.5 | 2.27 | 1.23 | 1.04 | 4295 | 1120 | 14.5 | +10/-10 (p=1.000) | - |
| check_B1 | 292 | 44.2% | [38.7%, 50.0%] | 69.2% | 9.0 | 1.00 | 1.00 | 0.00 | 3524 | 958 | 15.2 | +8/-6 (p=0.791) | +9/-7 (p=0.804) |
| revise_B1 | 292 | 43.8% | [38.4%, 49.7%] | 68.8% | 8.7 | 0.60 | 0.00 | 0.60 | 3029 | 887 | 12.6 | +7/-6 (p=1.000) | +5/-4 (p=1.000) |
| random_B1 | 292 | 44.9% | [39.4%, 50.3%] | 69.2% | 9.1 | 1.00 | 0.71 | 0.29 | 3444 | 949 | 15.2 | +10/-6 (p=0.454) | +8/-4 (p=0.388) |
| check_B2 | 292 | 44.2% | [38.7%, 50.0%] | 69.5% | 9.3 | 1.23 | 1.23 | 0.00 | 3708 | 1014 | 15.5 | +8/-6 (p=0.791) | +8/-6 (p=0.791) |
| revise_B2 | 292 | 43.2% | [37.3%, 49.0%] | 68.5% | 9.1 | 0.96 | 0.00 | 0.96 | 3231 | 919 | 13.0 | +7/-8 (p=1.000) | +4/-5 (p=1.000) |
| random_B2 | 292 | 43.5% | [37.7%, 49.0%] | 68.2% | 9.9 | 1.70 | 1.06 | 0.64 | 3931 | 1054 | 13.9 | +12/-12 (p=1.000) | +4/-4 (p=1.000) |
| check_B4 | 292 | 44.2% | [38.4%, 49.7%] | 69.5% | 9.5 | 1.46 | 1.46 | 0.00 | 3910 | 1094 | 15.9 | +8/-6 (p=0.791) | +8/-6 (p=0.791) |
| revise_B4 | 292 | 43.2% | [37.7%, 48.6%] | 68.5% | 9.2 | 1.00 | 0.00 | 1.00 | 3254 | 922 | 13.0 | +7/-8 (p=1.000) | +4/-5 (p=1.000) |
| random_B4 | 292 | 43.5% | [38.0%, 49.0%] | 68.5% | 10.6 | 2.37 | 1.37 | 0.99 | 4397 | 1168 | 14.7 | +11/-11 (p=1.000) | +2/-2 (p=1.000) |

### Process statistics

| condition | checks that changed plan | re-describe | plan-in-detail | replan | RM reassignments / query | errors |
|---|---|---|---|---|---|---|
| meta | - | 0 | 0 | 0 | 0.00 | 0 |
| routing | - | 0 | 0 | 0 | 0.29 | 0 |
| full | 29% | 28 | 236 | 40 | 0.62 | 0 |
| check_B1 | 23% | 0 | 0 | 0 | 0.43 | 0 |
| revise_B1 | - | 12 | 128 | 35 | 0.36 | 0 |
| random_B1 | 25% | 4 | 63 | 17 | 0.42 | 0 |
| check_B2 | 29% | 0 | 0 | 0 | 0.54 | 0 |
| revise_B2 | - | 25 | 219 | 36 | 0.37 | 0 |
| random_B2 | 28% | 12 | 140 | 34 | 0.53 | 0 |
| check_B4 | 38% | 0 | 0 | 0 | 0.73 | 0 |
| revise_B4 | - | 29 | 227 | 36 | 0.37 | 0 |
| random_B4 | 35% | 21 | 225 | 44 | 0.66 | 0 |

### Outcome changes relative to meta (routing and coordination combined)

| condition | task-text plans changed | answers changed | wrong->right | right->wrong |
|---|---|---|---|---|
| routing | 0/292 | 45 | 3 | 1 |
| full | 184/292 | 96 | 10 | 10 |
| check_B1 | 48/292 | 60 | 8 | 6 |
| revise_B1 | 140/292 | 79 | 7 | 6 |
| random_B1 | 104/292 | 67 | 10 | 6 |
| check_B2 | 45/292 | 63 | 8 | 6 |
| revise_B2 | 161/292 | 86 | 7 | 8 |
| random_B2 | 165/292 | 87 | 12 | 12 |
| check_B4 | 45/292 | 63 | 8 | 6 |
| revise_B4 | 161/292 | 85 | 7 | 8 |
| random_B4 | 181/292 | 95 | 11 | 11 |

_acc ±5% counts numeric answers within 5% of gold (numerical proximity; cause not inferred); vs X = +queries only this condition got right / -queries only X got right, exact McNemar p-value on the same queries. Costs are means per query; latency = sum of LLM call latencies (cached calls keep their original latency)._

## Full GPT-4o-mini summary

## Results: huskyqa_test

| condition | n | acc | 95% CI | acc ±5% | LLM calls | coord | check | revise | prompt tok | compl tok | latency s | vs meta | vs full |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| meta | 292 | 34.9% | [29.5%, 40.4%] | 57.5% | 7.7 | 0.00 | 0.00 | 0.00 | 2608 | 672 | 12.1 | - | +6/-6 (p=1.000) |
| routing | 292 | 33.9% | [28.4%, 39.4%] | 54.5% | 7.6 | 0.00 | 0.00 | 0.00 | 2549 | 650 | 11.8 | +2/-5 (p=0.453) | +2/-5 (p=0.453) |
| full | 292 | 34.9% | [29.5%, 40.4%] | 55.1% | 10.1 | 1.99 | 1.05 | 0.93 | 3947 | 923 | 16.5 | +6/-6 (p=1.000) | - |
| check_B1 | 292 | 34.2% | [28.8%, 39.7%] | 55.1% | 8.6 | 1.00 | 1.00 | 0.00 | 3343 | 753 | 13.8 | +3/-5 (p=0.727) | +2/-4 (p=0.688) |
| revise_B1 | 292 | 34.9% | [29.5%, 40.4%] | 54.8% | 8.4 | 0.56 | 0.00 | 0.56 | 2871 | 748 | 13.3 | +4/-4 (p=1.000) | +2/-2 (p=1.000) |
| split_B1 | 292 | 34.2% | [29.1%, 39.4%] | 55.1% | 8.6 | 1.00 | 1.00 | 0.00 | 3343 | 753 | 13.8 | +3/-5 (p=0.727) | +2/-4 (p=0.688) |
| random_B1 | 292 | 34.2% | [28.8%, 39.4%] | 54.5% | 8.7 | 1.00 | 0.73 | 0.27 | 3270 | 766 | 13.9 | +3/-5 (p=0.727) | +2/-4 (p=0.688) |
| check_B2 | 292 | 34.2% | [28.8%, 39.7%] | 55.1% | 8.7 | 1.05 | 1.05 | 0.00 | 3392 | 764 | 14.0 | +3/-5 (p=0.727) | +2/-4 (p=0.688) |
| revise_B2 | 292 | 34.6% | [29.1%, 40.1%] | 54.8% | 8.9 | 0.87 | 0.00 | 0.87 | 3072 | 802 | 14.2 | +5/-6 (p=1.000) | +0/-1 (p=1.000) |
| split_B2 | 292 | 35.3% | [29.8%, 40.8%] | 55.5% | 9.5 | 1.59 | 1.02 | 0.56 | 3685 | 855 | 15.4 | +5/-4 (p=1.000) | +2/-1 (p=1.000) |
| random_B2 | 292 | 35.3% | [29.8%, 40.4%] | 56.5% | 9.4 | 1.59 | 0.98 | 0.61 | 3672 | 859 | 15.4 | +5/-4 (p=1.000) | +2/-1 (p=1.000) |
| check_B4 | 292 | 34.2% | [28.8%, 39.4%] | 55.1% | 8.7 | 1.08 | 1.08 | 0.00 | 3411 | 770 | 14.1 | +3/-5 (p=0.727) | +2/-4 (p=0.688) |
| revise_B4 | 292 | 34.6% | [29.1%, 40.1%] | 54.5% | 9.0 | 0.92 | 0.00 | 0.92 | 3100 | 810 | 14.3 | +5/-6 (p=1.000) | +0/-1 (p=1.000) |
| split_B4 | 292 | 34.9% | [29.5%, 40.4%] | 55.1% | 10.1 | 2.00 | 1.08 | 0.92 | 3959 | 929 | 16.6 | +6/-6 (p=1.000) | +0/-0 (p=1.000) |
| random_B4 | 292 | 34.9% | [29.5%, 40.4%] | 55.1% | 10.0 | 2.07 | 1.15 | 0.91 | 4003 | 938 | 16.7 | +6/-6 (p=1.000) | +0/-0 (p=1.000) |

### Process statistics

| condition | checks that changed plan | re-describe | plan-in-detail | replan | RM reassignments / query | errors |
|---|---|---|---|---|---|---|
| meta | - | 0 | 0 | 0 | 0.00 | 0 |
| routing | - | 0 | 0 | 0 | 0.29 | 0 |
| full | 6% | 27 | 219 | 26 | 0.33 | 0 |
| check_B1 | 5% | 0 | 0 | 0 | 0.30 | 0 |
| revise_B1 | - | 13 | 126 | 24 | 0.30 | 0 |
| split_B1 | 5% | 0 | 0 | 0 | 0.30 | 0 |
| random_B1 | 6% | 4 | 62 | 13 | 0.30 | 0 |
| check_B2 | 6% | 0 | 0 | 0 | 0.30 | 0 |
| revise_B2 | - | 24 | 206 | 24 | 0.32 | 0 |
| split_B2 | 7% | 13 | 125 | 26 | 0.31 | 0 |
| random_B2 | 13% | 14 | 141 | 23 | 0.32 | 0 |
| check_B4 | 8% | 0 | 0 | 0 | 0.31 | 0 |
| revise_B4 | - | 27 | 217 | 24 | 0.32 | 0 |
| split_B4 | 9% | 26 | 217 | 26 | 0.33 | 0 |
| random_B4 | 15% | 24 | 217 | 26 | 0.34 | 0 |

### Outcome changes relative to meta (routing and coordination combined)

| condition | task-text plans changed | answers changed | wrong->right | right->wrong |
|---|---|---|---|---|
| routing | 0/292 | 38 | 2 | 5 |
| full | 103/292 | 75 | 6 | 6 |
| check_B1 | 12/292 | 43 | 3 | 5 |
| revise_B1 | 76/292 | 64 | 4 | 4 |
| split_B1 | 12/292 | 43 | 3 | 5 |
| random_B1 | 44/292 | 52 | 3 | 5 |
| check_B2 | 13/292 | 43 | 3 | 5 |
| revise_B2 | 92/292 | 71 | 5 | 6 |
| split_B2 | 84/292 | 66 | 5 | 4 |
| random_B2 | 77/292 | 61 | 5 | 4 |
| check_B4 | 13/292 | 44 | 3 | 5 |
| revise_B4 | 95/292 | 73 | 5 | 6 |
| split_B4 | 102/292 | 75 | 6 | 6 |
| random_B4 | 90/292 | 70 | 6 | 6 |

_acc ±5% counts numeric answers within 5% of gold (numerical proximity; cause not inferred); vs X = +queries only this condition got right / -queries only X got right, exact McNemar p-value on the same queries. Costs are means per query; latency = sum of LLM call latencies (cached calls keep their original latency)._


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
