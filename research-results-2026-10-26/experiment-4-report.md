# Experiment 4 - Cross-model transformations

Treatment: **T2**. There are **5/20** saved cells: ChatGPT and Claude source answers, each rewritten by two Gemini models across five questions.

| Rewriter | Cells | Clean | Warnings | Serious concerns | Median word change |
| --- | ---: | ---: | ---: | ---: | ---: |
| gemini-3.5-flash-lite | 5 | 5 | 0 | 0 | +0 |
| gemini-3.5-flash | 0 | 0 | 0 | 0 | +0 |

## Interpretation limits

Both rewriters use Gemini. This is a comparison of rewriter models on ChatGPT and Claude source text; it does **not** fill the ChatGPT-to-Claude or Claude-to-ChatGPT website rewrite cells in the manual. Neither source model has an API key configured in this app.

Any change can reflect the treatment, the rewriter, a second pass, or their interaction. The all-5/5 Gemini judge cannot rank these outputs, and no human comprehension outcome was collected. The CSV supports matched descriptive comparisons and fidelity screening, not a causal portability claim.

The app has no catalogue price for `gemini-3.5-flash`; its zero cost estimate in raw results means **unestimated**, not free.
