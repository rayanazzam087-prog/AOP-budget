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
