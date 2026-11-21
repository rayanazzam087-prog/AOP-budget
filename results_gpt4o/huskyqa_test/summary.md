## Results: huskyqa_test

| condition | n | acc | 95% CI | acc ±5% | LLM calls | coord | check | revise | prompt tok | compl tok | latency s | vs meta | vs full |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| meta | 292 | 43.5% | [37.7%, 49.0%] | 68.2% | 8.0 | 0.00 | 0.00 | 0.00 | 2718 | 837 | 14.2 | - | +9/-9 (p=1.000) |
| full | 292 | 43.5% | [38.0%, 49.0%] | 68.2% | 10.4 | 2.21 | 1.16 | 1.04 | 4240 | 1098 | 14.4 | +9/-9 (p=1.000) | - |
| check_B1 | 292 | 43.8% | [38.0%, 49.3%] | 68.5% | 9.0 | 1.00 | 1.00 | 0.00 | 3524 | 960 | 15.2 | +7/-6 (p=1.000) | +8/-7 (p=1.000) |
| revise_B1 | 292 | 43.8% | [38.0%, 49.3%] | 68.8% | 8.7 | 0.60 | 0.00 | 0.60 | 3029 | 887 | 12.6 | +7/-6 (p=1.000) | +4/-3 (p=1.000) |
| random_B1 | 292 | 44.5% | [39.0%, 50.0%] | 68.8% | 9.1 | 1.00 | 0.71 | 0.29 | 3444 | 949 | 15.2 | +9/-6 (p=0.607) | +7/-4 (p=0.549) |
| check_B2 | 292 | 44.2% | [38.4%, 49.7%] | 68.8% | 9.2 | 1.16 | 1.16 | 0.00 | 3653 | 992 | 15.4 | +7/-5 (p=0.774) | +8/-6 (p=0.791) |
| revise_B2 | 292 | 43.2% | [37.7%, 48.6%] | 68.5% | 9.1 | 0.96 | 0.00 | 0.96 | 3231 | 919 | 13.0 | +7/-8 (p=1.000) | +3/-4 (p=1.000) |
| random_B2 | 292 | 43.5% | [37.7%, 49.0%] | 67.5% | 9.9 | 1.67 | 1.02 | 0.65 | 3907 | 1042 | 13.8 | +11/-11 (p=1.000) | +4/-4 (p=1.000) |
| check_B4 | 292 | 44.2% | [38.4%, 49.7%] | 68.8% | 9.3 | 1.26 | 1.26 | 0.00 | 3745 | 1021 | 15.5 | +7/-5 (p=0.774) | +8/-6 (p=0.791) |
| revise_B4 | 292 | 43.2% | [37.3%, 49.0%] | 68.5% | 9.2 | 1.00 | 0.00 | 1.00 | 3254 | 922 | 13.0 | +7/-8 (p=1.000) | +3/-4 (p=1.000) |
| random_B4 | 292 | 43.8% | [38.0%, 49.7%] | 68.2% | 10.5 | 2.26 | 1.25 | 1.01 | 4304 | 1129 | 14.5 | +10/-9 (p=1.000) | +2/-1 (p=1.000) |

### Process statistics

| condition | checks that changed plan | re-describe | plan-in-detail | replan | RM reassignments / query | errors |
|---|---|---|---|---|---|---|
| meta | - | 0 | 0 | 0 | 0.00 | 0 |
| full | 20% | 28 | 236 | 40 | 0.50 | 0 |
| check_B1 | 16% | 0 | 0 | 0 | 0.37 | 0 |
| revise_B1 | - | 12 | 128 | 35 | 0.36 | 0 |
| random_B1 | 19% | 4 | 63 | 17 | 0.39 | 0 |
| check_B2 | 20% | 0 | 0 | 0 | 0.42 | 0 |
| revise_B2 | - | 25 | 219 | 36 | 0.37 | 0 |
| random_B2 | 20% | 12 | 143 | 36 | 0.45 | 0 |
| check_B4 | 23% | 0 | 0 | 0 | 0.45 | 0 |
| revise_B4 | - | 29 | 227 | 36 | 0.37 | 0 |
| random_B4 | 25% | 23 | 228 | 44 | 0.49 | 0 |

### Effect of coordination relative to meta

| condition | plans changed | answers changed | wrong->right | right->wrong |
|---|---|---|---|---|
| full | 183/292 | 95 | 9 | 9 |
| check_B1 | 48/292 | 60 | 7 | 6 |
| revise_B1 | 140/292 | 79 | 7 | 6 |
| random_B1 | 104/292 | 67 | 9 | 6 |
| check_B2 | 44/292 | 62 | 7 | 5 |
| revise_B2 | 161/292 | 86 | 7 | 8 |
| random_B2 | 168/292 | 87 | 11 | 11 |
| check_B4 | 44/292 | 62 | 7 | 5 |
| revise_B4 | 161/292 | 85 | 7 | 8 |
| random_B4 | 181/292 | 95 | 10 | 9 |

_acc ±5% counts numeric answers within 5% of gold (facts drift over time); vs X = +queries only this condition got right / -queries only X got right, exact McNemar p-value on the same queries. Costs are means per query; latency = sum of LLM call latencies (cached calls keep their original latency)._