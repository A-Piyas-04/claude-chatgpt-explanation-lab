# Experiment 5 - AI proxy answerability

This is the manual workflow's AI proxy, not the platform's human comprehension experiment. Studies were left in Draft and have no participant submissions.

| Topic | No-text correct | Diagnostic items | Condition | Correct with exact quote | Diagnostic correct with quote |
| --- | ---: | ---: | --- | ---: | ---: |

## Interpretation

First read the no-explanation result. When diagnostic items = 0, Gemini already answered every question before seeing an explanation, so the study cannot measure added answerability. A correct choice plus an exact quote shows textual support only. It does not show that a person learned the concept.

Question wording and randomized answer order are stored in each `study-*-config.json`. Per-item choices and quotes are stored in each `proxy-*.json`. The corresponding `proxy-*-report.md` is the report persisted by the app.
