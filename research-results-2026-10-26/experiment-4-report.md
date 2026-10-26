# Experiment 4 - Cross-model transformations

Treatment: **T2**. There are **20/20** saved cells: ChatGPT and Claude source answers, each rewritten by two Gemini models across five questions.

| Rewriter | Cells | Clean | Warnings | Serious concerns | Median word change |
| --- | ---: | ---: | ---: | ---: | ---: |
| gemini-3.5-flash-lite | 10 | 9 | 0 | 1 | +0 |
| gemini-3.1-flash-lite | 10 | 6 | 1 | 3 | +42.5 |

## Interpretation limits

T2 was chosen from Experiment 3 because 9/10 of its first-model runs had clean automated audits. The second rewriter had its own fidelity failures, listed in the table and CSV. A clean result is only a screening outcome.

Both rewriters use Gemini. This is a comparison of rewriter models on ChatGPT and Claude source text; it does **not** fill the ChatGPT-to-Claude or Claude-to-ChatGPT website rewrite cells in the manual. Neither source model has an API key configured in this app.

Any change can reflect the treatment, the rewriter, a second pass, or their interaction. The all-5/5 Gemini judge cannot rank these outputs, and no human comprehension outcome was collected. The CSV supports matched descriptive comparisons and fidelity screening, not a causal portability claim.

The app has no catalogue price for `gemini-3.1-flash-lite`; its zero cost estimate in raw results means **unestimated**, not free.
