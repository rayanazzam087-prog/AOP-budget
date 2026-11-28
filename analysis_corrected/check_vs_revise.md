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
