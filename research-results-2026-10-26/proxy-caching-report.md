# AI proxy answerability audit — AI proxy - caching - baselines vs T2

Model: gemini/gemini-3.5-flash-lite

No-explanation baseline: 3/3 items already answered correctly.

Diagnostic items: 0.

- chatgpt - base: 3/3 answers correct with a quote found in the text; 0/0 on diagnostic items.
- Claude - base: 3/3 answers correct with a quote found in the text; 0/0 on diagnostic items.
- gemini/gemini-3.5-flash-lite [T2]: 3/3 answers correct with a quote found in the text; 0/0 on diagnostic items.
- gemini/gemini-3.5-flash-lite [T2]: 3/3 answers correct with a quote found in the text; 0/0 on diagnostic items.

**Limit:** Gemini is an AI proxy, not a human learner. Correct answers can come from prior model knowledge. The no-explanation baseline flags those items. Exact quote matching checks textual support, not understanding. These scores must never be reported as human comprehension.
