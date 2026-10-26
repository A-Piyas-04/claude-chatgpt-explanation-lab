# Experiment 3 - Single-treatment transformations

Saved runs: **45/60**. Each run used one treatment, Gemini 3.5 Flash-Lite, stages A/B/D, and saved a variant.

| Treatment | Runs | Clean | Warnings | Serious concerns | Median word change |
| --- | ---: | ---: | ---: | ---: | ---: |
| T1 | 8 | 6 | 1 | 1 | +42.5 |
| T2 | 8 | 8 | 0 | 0 | +0 |
| T3 | 8 | 0 | 6 | 2 | +235 |
| T4 | 7 | 1 | 2 | 4 | +120 |
| T5 | 7 | 2 | 0 | 5 | +38 |
| T6 | 7 | 5 | 1 | 1 | +0 |

## Interpretation

A clean verdict means the automated audit detected no issue. It does not verify factual accuracy. Runs with boundary violations or factual warnings are retained in the raw files and should not be counted as clean isolation of that treatment.

The diagnostic columns in `experiment-3-results.csv` describe text changes. The existing Gemini judge gave 5/5 on every dimension for all 30 imported answers, so that judge cannot establish which treatment improved teaching. No human comprehension outcomes exist.

## Files

`experiment-3-results.csv` has one row per saved variant. Each `transform-*.json` includes the full rewrite, per-treatment diff, pipeline stages, and fidelity warnings. Source and variant IDs connect these files to the app database.
