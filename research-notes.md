# ExplanationLab research notes

Generated from the app database on 2026-10-26 (Asia/Dhaka). This is a snapshot of stored measurements; it does not include independent human reading or comprehension tests.

## Data and interpretation

- 5 research questions and 30 manually imported, non-synthetic web-chat answers: ChatGPT and Claude, each with baseline, tutor, and pedagogical versions. The database also contains other seeded questions; they are outside this 30-answer set.
- Automated text diagnostics exist for all 30 answers. Gemini (`gemini-3.5-flash-lite`) has a stored blinded judge evaluation for all 30 answers.
- **Judge ceiling:** every one of the 270 stored rubric scores (30 answers x 9 dimensions) is **5/5**. These scores cannot distinguish the answers. Do not select a winner from them.
- **Checklist match** below is lexical keyword overlap, not a fact check. A correct paraphrase can be marked absent. Word and sentence measures describe the writing; they do not measure comprehension.
- All answers came from consumer web chats. Their hidden system prompts and generation settings are unknown, so provider comparisons are observational.
- "Long sentences" uses the app's built-in threshold. The response ID lets you find the exact answer and its full diagnostics and judge rationale in Comparison.

## Experiment 1 - Baseline comparison

Only the two plain-question answers for each topic are included in this section.

### Caching

**Question:** How do write-through and write-back caches handle a write, and what are the tradeoffs?

| Model | Words | Avg. words/sentence | Long sentences | Checklist match | Gemini judge | Response ID |
| --- | ---: | ---: | ---: | ---: | --- | --- |
| ChatGPT | 590 | 10.73 | 1 | 4/4 | 5/5 on all 9 dimensions | `7ac6680a-25b1-4216-b8d9-d58317d5e206` |
| Claude | 462 | 19.25 | 3 | 3/4 | 5/5 on all 9 dimensions | `7ecd8f9f-d2e8-418f-8f96-dee096278d2a` |

- Captured: ChatGPT `gpt-6-luna` at 2026-10-26 04:25 UTC; Claude `claude-sonnet-5-5` at 2026-10-26 05:12 UTC.
- Measured difference: ChatGPT is 128 words longer; its average sentence is 8.52 words shorter.
- Lexical checklist match: ChatGPT 4/4, Claude 3/4. Review the answer text before treating an unmatched claim as missing.
- The Gemini rubric is tied at its maximum on every dimension; it offers no ranking for this pair.

### Database indexing

**Question:** How does a B-tree database index make a lookup faster, and what does the index cost you?

| Model | Words | Avg. words/sentence | Long sentences | Checklist match | Gemini judge | Response ID |
| --- | ---: | ---: | ---: | ---: | --- | --- |
| ChatGPT | 595 | 15.26 | 4 | 3/4 | 5/5 on all 9 dimensions | `fe4b2942-b26f-4bc3-bef3-df0640e69137` |
| Claude | 488 | 18.07 | 3 | 3/4 | 5/5 on all 9 dimensions | `41e2edb9-7232-46f7-baeb-4efbcdc058b7` |

- Captured: ChatGPT `gpt-6-luna` at 2026-10-26 05:17 UTC; Claude `claude-sonnet-5-5` at 2026-10-26 05:14 UTC.
- Measured difference: ChatGPT is 107 words longer; its average sentence is 2.81 words shorter.
- Lexical checklist match: ChatGPT 3/4, Claude 3/4. Review the answer text before treating an unmatched claim as missing.
- The Gemini rubric is tied at its maximum on every dimension; it offers no ranking for this pair.

### TCP handshake

**Question:** How does the TCP three-way handshake set up a connection, and why is each of the three steps needed?

| Model | Words | Avg. words/sentence | Long sentences | Checklist match | Gemini judge | Response ID |
| --- | ---: | ---: | ---: | ---: | --- | --- |
| ChatGPT | 762 | 12.29 | 2 | 4/4 | 5/5 on all 9 dimensions | `4ffa3cbb-1e8d-4a46-ad5d-69e476710992` |
| Claude | 493 | 18.96 | 1 | 4/4 | 5/5 on all 9 dimensions | `3cfaae4b-bf68-4beb-9eef-a00f8f92bce1` |

- Captured: ChatGPT `gpt-6-luna` at 2026-10-26 05:20 UTC; Claude `claude-sonnet-5-5` at 2026-10-26 05:22 UTC.
- Measured difference: ChatGPT is 269 words longer; its average sentence is 6.67 words shorter.
- Lexical checklist match: ChatGPT 4/4, Claude 4/4. Review the answer text before treating an unmatched claim as missing.
- The Gemini rubric is tied at its maximum on every dimension; it offers no ranking for this pair.

### Vaccines

**Question:** How does a vaccine train the immune system to recognize a pathogen without causing the disease?

| Model | Words | Avg. words/sentence | Long sentences | Checklist match | Gemini judge | Response ID |
| --- | ---: | ---: | ---: | ---: | --- | --- |
| ChatGPT | 601 | 14.66 | 1 | 3/4 | 5/5 on all 9 dimensions | `77fa0bb5-fe74-4069-b4ce-c01aed582d0f` |
| Claude | 437 | 17.48 | 3 | 2/4 | 5/5 on all 9 dimensions | `0f26480d-7a72-4396-8964-0f189a6a59fd` |

- Captured: ChatGPT `gpt-6-luna` at 2026-10-26 05:30 UTC; Claude `claude-sonnet-5-5` at 2026-10-26 05:27 UTC.
- Measured difference: ChatGPT is 164 words longer; its average sentence is 2.82 words shorter.
- Lexical checklist match: ChatGPT 3/4, Claude 2/4. Review the answer text before treating an unmatched claim as missing.
- The Gemini rubric is tied at its maximum on every dimension; it offers no ranking for this pair.

### Compound interest

**Question:** How is compound interest different from simple interest, and why does the gap between them grow over time?

| Model | Words | Avg. words/sentence | Long sentences | Checklist match | Gemini judge | Response ID |
| --- | ---: | ---: | ---: | ---: | --- | --- |
| ChatGPT | 376 | 9.17 | 1 | 3/4 | 5/5 on all 9 dimensions | `fb628255-20fd-4e30-b898-169bff702874` |
| Claude | 290 | 17.06 | 2 | 4/4 | 5/5 on all 9 dimensions | `1183e608-2143-4cc2-b81e-0755c4fc29cf` |

- Captured: ChatGPT `gpt-6-luna` at 2026-10-26 05:31 UTC; Claude `claude-sonnet-5-5` at 2026-10-26 05:33 UTC.
- Measured difference: ChatGPT is 86 words longer; its average sentence is 7.89 words shorter.
- Lexical checklist match: ChatGPT 3/4, Claude 4/4. Review the answer text before treating an unmatched claim as missing.
- The Gemini rubric is tied at its maximum on every dimension; it offers no ranking for this pair.

## Experiment 2 - Prompt intervention

Each table compares the three prompt conditions within each model. "A" is the baseline reused from Experiment 1.

### Caching

| Model | Condition | Words | Avg. words/sentence | Long sentences | Checklist match | Gemini judge | Response ID |
| --- | --- | ---: | ---: | ---: | ---: | --- | --- |
| ChatGPT | A - Baseline | 590 | 10.73 | 1 | 4/4 | 5/5 on all 9 dimensions | `7ac6680a-25b1-4216-b8d9-d58317d5e206` |
| ChatGPT | B - Tutor | 831 | 12.98 | 2 | 4/4 | 5/5 on all 9 dimensions | `0d949680-435c-449e-89e9-350ea564e7ab` |
| ChatGPT | C - Pedagogical | 1118 | 13.63 | 5 | 4/4 | 5/5 on all 9 dimensions | `e74cdbe1-e713-4c57-9fe9-0a61a0dfd25d` |
| Claude | A - Baseline | 462 | 19.25 | 3 | 3/4 | 5/5 on all 9 dimensions | `7ecd8f9f-d2e8-418f-8f96-dee096278d2a` |
| Claude | B - Tutor | 593 | 15.21 | 3 | 3/4 | 5/5 on all 9 dimensions | `dcf5e29a-6875-4e9d-8b5f-fbbed48fa08c` |
| Claude | C - Pedagogical | 826 | 20.65 | 9 | 4/4 | 5/5 on all 9 dimensions | `9f05b778-20ef-4a59-bac7-aa51124b8994` |

- ChatGPT: tutor is +241 words versus baseline; pedagogical is +528 words versus baseline. These length changes alone do not establish better teaching.
- Claude: tutor is +131 words versus baseline; pedagogical is +364 words versus baseline. These length changes alone do not establish better teaching.
- Judge scores are tied at 5/5 on all nine dimensions for all six answers; use reading and later tests to evaluate the prompt effect.

### Database indexing

| Model | Condition | Words | Avg. words/sentence | Long sentences | Checklist match | Gemini judge | Response ID |
| --- | --- | ---: | ---: | ---: | ---: | --- | --- |
| ChatGPT | A - Baseline | 595 | 15.26 | 4 | 3/4 | 5/5 on all 9 dimensions | `fe4b2942-b26f-4bc3-bef3-df0640e69137` |
| ChatGPT | B - Tutor | 1300 | 13.68 | 4 | 4/4 | 5/5 on all 9 dimensions | `e8ddebba-e7c2-422a-9f7b-95218461079f` |
| ChatGPT | C - Pedagogical | 1332 | 14.97 | 6 | 3/4 | 5/5 on all 9 dimensions | `a583c761-d865-4c2f-b87f-45b1d2e654a8` |
| Claude | A - Baseline | 488 | 18.07 | 3 | 3/4 | 5/5 on all 9 dimensions | `41e2edb9-7232-46f7-baeb-4efbcdc058b7` |
| Claude | B - Tutor | 810 | 13.28 | 3 | 3/4 | 5/5 on all 9 dimensions | `7e82a71e-8885-4735-833a-43d9a5275588` |
| Claude | C - Pedagogical | 787 | 17.11 | 3 | 3/4 | 5/5 on all 9 dimensions | `14948f7e-786b-4dda-8703-1f1392b47dcb` |

- ChatGPT: tutor is +705 words versus baseline; pedagogical is +737 words versus baseline. These length changes alone do not establish better teaching.
- Claude: tutor is +322 words versus baseline; pedagogical is +299 words versus baseline. These length changes alone do not establish better teaching.
- Judge scores are tied at 5/5 on all nine dimensions for all six answers; use reading and later tests to evaluate the prompt effect.

### TCP handshake

| Model | Condition | Words | Avg. words/sentence | Long sentences | Checklist match | Gemini judge | Response ID |
| --- | --- | ---: | ---: | ---: | ---: | --- | --- |
| ChatGPT | A - Baseline | 762 | 12.29 | 2 | 4/4 | 5/5 on all 9 dimensions | `4ffa3cbb-1e8d-4a46-ad5d-69e476710992` |
| ChatGPT | B - Tutor | 784 | 11.2 | 0 | 4/4 | 5/5 on all 9 dimensions | `1c07f616-5f53-4bc5-89c8-55f3a73ed886` |
| ChatGPT | C - Pedagogical | 1052 | 11.69 | 1 | 4/4 | 5/5 on all 9 dimensions | `eda6bc26-f531-49ba-b0b5-b7af1d0bb499` |
| Claude | A - Baseline | 493 | 18.96 | 1 | 4/4 | 5/5 on all 9 dimensions | `3cfaae4b-bf68-4beb-9eef-a00f8f92bce1` |
| Claude | B - Tutor | 547 | 17.65 | 4 | 4/4 | 5/5 on all 9 dimensions | `c7a02b20-9e78-4302-ad70-44094f538a46` |
| Claude | C - Pedagogical | 1081 | 22.06 | 10 | 4/4 | 5/5 on all 9 dimensions | `b2e6ac60-314a-40a9-a4bd-6d42de8c0918` |

- ChatGPT: tutor is +22 words versus baseline; pedagogical is +290 words versus baseline. These length changes alone do not establish better teaching.
- Claude: tutor is +54 words versus baseline; pedagogical is +588 words versus baseline. These length changes alone do not establish better teaching.
- Judge scores are tied at 5/5 on all nine dimensions for all six answers; use reading and later tests to evaluate the prompt effect.

### Vaccines

| Model | Condition | Words | Avg. words/sentence | Long sentences | Checklist match | Gemini judge | Response ID |
| --- | --- | ---: | ---: | ---: | ---: | --- | --- |
| ChatGPT | A - Baseline | 601 | 14.66 | 1 | 3/4 | 5/5 on all 9 dimensions | `77fa0bb5-fe74-4069-b4ce-c01aed582d0f` |
| ChatGPT | B - Tutor | 726 | 12.96 | 0 | 3/4 | 5/5 on all 9 dimensions | `b87e0c2f-4c52-4dde-ba91-cbcb93a2b508` |
| ChatGPT | C - Pedagogical | 1362 | 13.62 | 1 | 3/4 | 5/5 on all 9 dimensions | `aa6abd08-4a2c-446c-8fb0-7682177516cc` |
| Claude | A - Baseline | 437 | 17.48 | 3 | 2/4 | 5/5 on all 9 dimensions | `0f26480d-7a72-4396-8964-0f189a6a59fd` |
| Claude | B - Tutor | 569 | 13.23 | 0 | 3/4 | 5/5 on all 9 dimensions | `178c1e25-a559-410e-a7dd-1878aca0303b` |
| Claude | C - Pedagogical | 1109 | 15.4 | 4 | 4/4 | 5/5 on all 9 dimensions | `d62d0250-52ed-49d3-b917-5ac47f0251ee` |

- ChatGPT: tutor is +125 words versus baseline; pedagogical is +761 words versus baseline. These length changes alone do not establish better teaching.
- Claude: tutor is +132 words versus baseline; pedagogical is +672 words versus baseline. These length changes alone do not establish better teaching.
- Judge scores are tied at 5/5 on all nine dimensions for all six answers; use reading and later tests to evaluate the prompt effect.

### Compound interest

| Model | Condition | Words | Avg. words/sentence | Long sentences | Checklist match | Gemini judge | Response ID |
| --- | --- | ---: | ---: | ---: | ---: | --- | --- |
| ChatGPT | A - Baseline | 376 | 9.17 | 1 | 3/4 | 5/5 on all 9 dimensions | `fb628255-20fd-4e30-b898-169bff702874` |
| ChatGPT | B - Tutor | 531 | 12.07 | 2 | 3/4 | 5/5 on all 9 dimensions | `df200b71-15e7-4256-b108-a01ce61b3292` |
| ChatGPT | C - Pedagogical | 501 | 13.18 | 1 | 4/4 | 5/5 on all 9 dimensions | `87e18940-609b-4e13-ab4b-accc21ccb027` |
| Claude | A - Baseline | 290 | 17.06 | 2 | 4/4 | 5/5 on all 9 dimensions | `1183e608-2143-4cc2-b81e-0755c4fc29cf` |
| Claude | B - Tutor | 494 | 14.97 | 0 | 4/4 | 5/5 on all 9 dimensions | `46721278-80e3-4d84-86a9-9b31e1bca613` |
| Claude | C - Pedagogical | 536 | 13.4 | 1 | 4/4 | 5/5 on all 9 dimensions | `a6885a2f-f5ce-4dfa-b11c-8144d3314036` |

- ChatGPT: tutor is +155 words versus baseline; pedagogical is +125 words versus baseline. These length changes alone do not establish better teaching.
- Claude: tutor is +204 words versus baseline; pedagogical is +246 words versus baseline. These length changes alone do not establish better teaching.
- Judge scores are tied at 5/5 on all nine dimensions for all six answers; use reading and later tests to evaluate the prompt effect.

## Experiment 3 - Mechanism isolation

No saved transformation variants or fidelity reports were in the database when this file was generated. Results pending.

## Experiment 4 - Cross-model transformation

No cross-model transformation variants were in the database when this file was generated. Results pending.

## Experiment 5 - AI proxy answerability

No studies or AI proxy reports were in the database when this file was generated. Results pending. AI proxy results, when available, measure answerability from text, not human comprehension.

## Source and limits

- Source: `apps/api/explanationlab.sqlite3`, including its active SQLite WAL state, queried through SQLite.
- Judge model: `gemini-3.5-flash-lite`. The nine dimensions are clarity, logical progression, prerequisite handling, mechanism explanation, example quality, audience suitability, unnecessary complexity, information loss, and factual fidelity.
- Gemini judgments are model opinions. The universal 5/5 pattern is a ceiling effect in this dataset and should be reported as such.
- A human should still inspect the actual prose and factual checklists before drawing a substantive conclusion.
