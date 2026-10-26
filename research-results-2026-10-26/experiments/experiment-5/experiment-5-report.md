# Experiment 5 - AI proxy answerability

This is the manual workflow's AI proxy, not the platform's human comprehension experiment. Studies were left in Draft and have no participant submissions.

| Topic | No-text correct | Diagnostic items | Condition | Correct with exact quote | Diagnostic correct with quote |
| --- | ---: | ---: | --- | ---: | ---: |
| caching | 3/3 | 0 | chatgpt baseline | 3/3 | 0/0 |
| caching | 3/3 | 0 | claude baseline | 3/3 | 0/0 |
| caching | 3/3 | 0 | chatgpt transformed | 3/3 | 0/0 |
| caching | 3/3 | 0 | claude transformed | 3/3 | 0/0 |
| databases | 3/3 | 0 | chatgpt baseline | 3/3 | 0/0 |
| databases | 3/3 | 0 | claude baseline | 3/3 | 0/0 |
| databases | 3/3 | 0 | chatgpt transformed | 3/3 | 0/0 |
| databases | 3/3 | 0 | claude transformed | 3/3 | 0/0 |
| tcp | 3/3 | 0 | chatgpt baseline | 3/3 | 0/0 |
| tcp | 3/3 | 0 | claude baseline | 2/3 | 0/0 |
| tcp | 3/3 | 0 | claude transformed | 2/3 | 0/0 |
| immunology | 3/3 | 0 | chatgpt baseline | 3/3 | 0/0 |
| immunology | 3/3 | 0 | claude baseline | 3/3 | 0/0 |
| immunology | 3/3 | 0 | chatgpt transformed | 3/3 | 0/0 |
| immunology | 3/3 | 0 | claude transformed | 3/3 | 0/0 |
| interest | 3/3 | 0 | chatgpt baseline | 3/3 | 0/0 |
| interest | 3/3 | 0 | claude baseline | 3/3 | 0/0 |
| interest | 3/3 | 0 | chatgpt transformed | 3/3 | 0/0 |
| interest | 3/3 | 0 | claude transformed | 3/3 | 0/0 |

## Interpretation

All five no-explanation controls scored 3/3, leaving zero diagnostic items across the study set. The TCP study had three conditions because its ChatGPT T2 variant failed the fidelity screen and was excluded.

First read the no-explanation result. When diagnostic items = 0, Gemini already answered every question before seeing an explanation, so the study cannot measure added answerability. A correct choice plus an exact quote shows textual support only. It does not show that a person learned the concept.

Question wording and randomized answer order are stored in each `study-*-config.json`. Per-item choices and quotes are stored in each `proxy-*.json`. The corresponding `proxy-*-report.md` is the report persisted by the app.
