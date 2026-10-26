# Experiment 3 - Single-treatment transformations

Saved runs: **26/60**. Each run used one treatment, Gemini 3.5 Flash-Lite, stages A/B/D, and saved a variant.

| Treatment | Runs | Clean | Warnings | Serious concerns | Median word change |
| --- | ---: | ---: | ---: | ---: | ---: |
| T1 | 5 | 4 | 0 | 1 | +71 |
| T2 | 5 | 5 | 0 | 0 | +0 |
| T3 | 4 | 0 | 4 | 0 | +275 |
| T4 | 4 | 0 | 2 | 2 | +134.5 |
| T5 | 4 | 2 | 0 | 2 | +38.5 |
| T6 | 4 | 2 | 1 | 1 | +0 |

## Interpretation

A clean verdict means the automated audit detected no issue. It does not verify factual accuracy. Runs with boundary violations or factual warnings are retained in the raw files and should not be counted as clean isolation of that treatment.

The diagnostic columns in `experiment-3-results.csv` describe text changes. The existing Gemini judge gave 5/5 on every dimension for all 30 imported answers, so that judge cannot establish which treatment improved teaching. No human comprehension outcomes exist.

## Files

`experiment-3-results.csv` has one row per saved variant. Each `transform-*.json` includes the full rewrite, per-treatment diff, pipeline stages, and fidelity warnings. Source and variant IDs connect these files to the app database.
