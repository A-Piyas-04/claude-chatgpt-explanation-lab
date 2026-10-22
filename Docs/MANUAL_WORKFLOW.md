# The complete step-by-step guide: comparing ChatGPT and Claude with a Gemini key

This guide walks you through all five experiments from start to finish, written
so you can follow it even if you have never written a line of code. Read it top
to bottom the first time. You can keep it open on your phone while you click
through the app on your computer.

## What you are actually doing (read this once)

You want to measure how well **ChatGPT** and **Claude** explain things, and use
what you learn to build a Claude skill later. Three simple facts shape the whole
process:

1. **The real answers come from the ChatGPT and Claude websites**, not from this
   app. You will open ChatGPT and Claude in your browser, ask them questions,
   copy their answers, and paste those answers into this app. There is no way
   around this copy-and-paste: no key you can buy will let the app pull answers
   out of your ChatGPT or Claude subscription for you.
2. **Gemini is your helper, not a contestant.** Your Gemini key lets the app do
   the tedious analysis automatically: scoring answers, rewriting them to test
   teaching techniques, and running an automated check. Gemini never pretends to
   be ChatGPT or Claude. Think of Gemini as the lab instrument and ChatGPT and
   Claude as the two things being studied.
3. **One honest limit.** Experiment 5 is about whether *real people* understand
   more. You have no participants here, so you will use an automated stand-in
   called the **AI proxy**. It checks whether an answer *contains* the
   information needed to answer a question — it does **not** prove a human
   learned anything. Keep that difference in mind; it matters when you write up
   results.

Here is the map of the five experiments and what each one tells you:

| # | Experiment | The question it answers |
| - | ---------- | ----------------------- |
| 1 | Baseline comparison | How do ChatGPT and Claude explain the same thing by default? |
| 2 | Prompt intervention | Does giving better instructions alone make explanations clearer? |
| 3 | Mechanism isolation | Which single rewriting technique actually improves an answer? |
| 4 | Cross-model transformation | Is the improvement from the technique, or just from using another model? |
| 5 | AI proxy (stand-in for human comprehension) | Which answer contains more answerable material? |

---

# PART 1 — Getting ready

Do everything in Part 1 once, before any experiment.

## 1.1 Start the app

The app has two halves that must both be running: the "engine" (called the API)
and the "website" (what you see in your browser). You start each one in its own
black command window called **PowerShell**.

**Open the first PowerShell window:**

1. Press the **Windows key** on your keyboard.
2. Type `powershell` and press **Enter**. A dark window opens.
3. Click inside it, then copy and paste the three lines below one block at a
   time. After pasting, press **Enter**.

```powershell
cd "E:\Projects\My Apps\explanation-lab\apps\api"
.\.venv\Scripts\python.exe -m uvicorn explanationlab.main:app --reload
```

Leave this window open. It is now the engine. You will see text scroll and then
mostly sit still — that is normal and means it is working. Do **not** close it.

**Open a second PowerShell window** the same way (Windows key → type
`powershell` → Enter), then paste:

```powershell
cd "E:\Projects\My Apps\explanation-lab\apps\web"
npm run dev
```

Leave this one open too. This is the website.

## 1.2 Open the app and check it is "live"

1. Open your web browser (Chrome, Edge, whatever you use).
2. In the address bar at the top, type `http://localhost:3000` and press
   **Enter**.
3. The app opens. Look at the top of the page for a small badge. It should say
   **gemini live**.

- If it says **gemini live** — perfect, Gemini is connected.
- If it says **Demo mode** — the app is not seeing your Gemini key. Close the
  first PowerShell window, open a new one, and repeat step 1.1. If it still says
  Demo mode, your key line in the `.env` file is wrong.

> **The SYNTHETIC warning.** Any answer the app marks with a **SYNTHETIC** label
> is fake demo data, not a real result. If you ever see SYNTHETIC on something
> you are studying, stop and fix the setup — never use SYNTHETIC output as a
> finding.

## 1.3 Create your five questions

Everything you do rests on good questions. Below are five ready-to-use
questions, already written with their fact-checklists. You will type each one
into the app now. (The fact-checklist is just a short list of true statements
about the topic; the app uses it later to spot if a rewrite accidentally changed
a fact.)

**For each of the five questions below, do this:**

1. In the app, click **Library** in the menu, then click **Questions**.
2. Click **Add question**.
3. Fill in the four boxes — **Question**, **Domain**, **Topic**,
   **Conceptual difficulty** — using the table for that question.
4. In the **Factual checklist** box, type the checklist lines, **one claim per
   line** (press Enter between them).
5. Click **Create question**.

Repeat for all five. When you are done you will have five questions saved.

---

### Question 1 — Caching

| Box | What to type |
| --- | --- |
| Question | `How do write-through and write-back caches handle a write, and what are the tradeoffs?` |
| Domain | `software_engineering` |
| Topic | `caching` |
| Conceptual difficulty | `moderate` |

Factual checklist (one line each):

```text
Write-through writes to the cache and the backing store before the write is considered complete.
Write-back writes to the cache first and copies the changed data to backing storage later.
Write-back can lose unflushed changes if the cache fails before writing back; write-through writes to backing storage more immediately.
Write-back usually has faster write performance because it delays the slower backing-store writes.
```

### Question 2 — Database indexing

| Box | What to type |
| --- | --- |
| Question | `How does a B-tree database index make a lookup faster, and what does the index cost you?` |
| Domain | `software_engineering` |
| Topic | `databases` |
| Conceptual difficulty | `moderate` |

Factual checklist:

```text
A B-tree keeps keys in sorted order so the database can narrow down to a row instead of scanning every row.
Each step down the tree removes a large share of the remaining rows, so lookups take roughly logarithmic time.
The index must be updated on every insert, update, and delete, which makes writes slower.
The index takes up extra storage space in addition to the table itself.
```

### Question 3 — TCP handshake

| Box | What to type |
| --- | --- |
| Question | `How does the TCP three-way handshake set up a connection, and why is each of the three steps needed?` |
| Domain | `networking` |
| Topic | `tcp` |
| Conceptual difficulty | `moderate` |

Factual checklist:

```text
The client starts by sending a SYN message with its initial sequence number.
The server replies with a SYN-ACK, acknowledging the client's number and sending its own sequence number.
The client sends an ACK that acknowledges the server's sequence number, which completes the handshake.
All three steps are needed so both sides confirm they can send and receive and agree on starting sequence numbers.
```

### Question 4 — Vaccines

| Box | What to type |
| --- | --- |
| Question | `How does a vaccine train the immune system to recognize a pathogen without causing the disease?` |
| Domain | `biology` |
| Topic | `immunology` |
| Conceptual difficulty | `moderate` |

Factual checklist:

```text
A vaccine presents a harmless piece, or a weakened or inactivated form, of the pathogen rather than the full live disease-causing agent.
The immune system responds by producing antibodies and activating cells specific to that antigen.
Memory B cells and T cells are formed and remain after the response fades.
On a later real exposure, those memory cells produce a faster and stronger response.
```

### Question 5 — Compound interest

| Box | What to type |
| --- | --- |
| Question | `How is compound interest different from simple interest, and why does the gap between them grow over time?` |
| Domain | `finance` |
| Topic | `interest` |
| Conceptual difficulty | `moderate` |

Factual checklist:

```text
Simple interest is calculated only on the original principal in every period.
Compound interest is calculated on the principal plus the interest already accumulated.
Because compound interest earns interest on past interest, the balance grows faster than with simple interest.
The gap widens over time because the amount that compound interest is applied to keeps growing each period.
```

---

> **Honest warning about these five.** They are common textbook topics, which
> makes them easy to fact-check but also means Gemini may already know the
> answers before it reads anything. That weakens Experiment 5 especially (the
> AI proxy may score a text correctly without needing the explanation at all).
> Use these five to learn the whole process end to end. For your **real** skill
> research, add a few questions from material only you have — a topic from your
> own notes, a product, a niche process — where the correct answer truly depends
> on the explanation in front of it. Part 2 and Part 3 work the same either way.

## 1.4 Two instruction blocks you will reuse

Experiment 2 asks each model the same question three ways. Two of those ways
need an instruction pasted **in front of** the question. Keep these two blocks
handy — you will copy them often.

**Instruction B — "Generic tutor"** (ordinary everyday prompting):

```text
Act as a helpful tutor. Explain clearly, step by step, using simple language and practical examples.
```

**Instruction C — "Structured pedagogical"** (a real teaching process):

```text
You are explaining a concept to help someone genuinely understand it. Follow this teaching process:
1. Infer who the learner likely is and what they already know.
2. Identify the prerequisite ideas needed before the main concept.
3. Establish the problem or question the concept answers.
4. Order the ideas so nothing is mentioned before the idea it depends on.
5. Explain the underlying mechanism — how and why it works — not just a definition.
6. Ground each abstract idea in something concrete.
7. Define every technical term the first time you use it.
8. Keep full technical accuracy; do not oversimplify to the point of being wrong.
9. Do not patronise or talk down to the reader.
10. Do not pad — remove anything that does not help understanding.
Now explain the following:
```

---

# PART 2 — Running the five experiments

A few things are the same in every experiment, so learn them once:

- **Getting an answer from a model** always means: open a **brand-new chat** in
  ChatGPT (or Claude) on the website, paste the prompt, wait for the full
  answer, and copy all of it. Use a new chat every time so earlier questions do
  not influence the answer. Note the model name shown on screen and the date.
- **Putting an answer into the app** always happens on the **Comparison** page:
  1. Click **Comparison** in the menu.
  2. At the top, select the question this answer belongs to.
  3. Click **Import a web-chat answer**.
  4. Fill in the boxes: **Provider** (`openai` for ChatGPT, `anthropic` for
     Claude), the **model name** exactly as it appeared, an **Answer label**
     (a short name so you can tell answers apart — examples are given below),
     the **pasted answer**, and **Capture notes** (just write the date and model
     name).
  5. Click **Import answer**.
  6. Check that it now shows **imported** and has **no SYNTHETIC label**.

Now the experiments.

## Experiment 1 — Baseline comparison

**What you are finding out:** how ChatGPT and Claude explain each topic when you
just ask plainly, with no special instructions. This is your main head-to-head.

**Step A — collect the answers.** For each of your five questions:

1. Open a new ChatGPT chat. Paste the plain question (just the question text, no
   extra instructions). Copy the full answer.
2. Import it on the Comparison page. Label it `ChatGPT — baseline`.
3. Open a new Claude chat. Paste the same plain question. Copy the full answer.
4. Import it. Label it `Claude — baseline`.

After this you have ten answers (two per question).

**Step B — look at the automatic measurements.** Still on the **Comparison**
page, with a question selected, the two answers appear side by side and the app
shows **diagnostics** automatically: word count, average sentence length, how
many very long sentences, jargon words, vague phrases, and so on. These
*describe* the writing. They do **not** say which is a better teacher — a
shorter sentence is not automatically clearer.

**Step C — get Gemini's opinion (the blinded judge).** For each answer:

1. Find the **Select a judge…** box and choose **gemini → gemini-3.5-flash-lite**.
2. Click **Run blinded judge**. "Blinded" means Gemini is not told which model
   wrote the answer, so it cannot play favourites.
3. Read the scores it gives. Treat them as *one opinion*, not proof.

**Step D — note the fine print.** Open the **Control limitations** section.
Because these came from the websites, the app correctly warns that the hidden
settings behind ChatGPT and Claude are unknown, so this is not a perfectly
fair lab comparison. Keep that caveat in your notes.

**What you walk away with:** for all five questions, side-by-side writing
measurements and Gemini's judge scores for ChatGPT vs Claude.

## Experiment 2 — Prompt intervention

**What you are finding out:** whether simply giving better instructions makes the
explanations clearer — and whether a real teaching process beats a casual
"explain simply."

For **each** of your five questions, you will collect **three** answers from
**each** model (six per question). The three versions are:

- **Version A (Default):** just the plain question. *You already have this from
  Experiment 1 — reuse it, do not redo it.*
- **Version B (Generic tutor):** paste **Instruction B** from Part 1.4, then the
  question, in one message.
- **Version C (Structured pedagogical):** paste **Instruction C** from Part 1.4,
  then the question, in one message.

**Step A — collect B and C.** For each question, in a new chat each time:

1. ChatGPT, Version B: paste Instruction B + the question. Import it, label
   `ChatGPT — B tutor`.
2. ChatGPT, Version C: paste Instruction C + the question. Import it, label
   `ChatGPT — C pedagogical`.
3. Claude, Version B: same, label `Claude — B tutor`.
4. Claude, Version C: same, label `Claude — C pedagogical`.

**Step B — compare the three versions.** On the **Comparison** page, look at the
diagnostics and run the **blinded judge** (Gemini) on each version, just like
Experiment 1.

**What to watch for:** the classic trap is Version B becoming shorter and
friendlier but not actually teaching more. Compare B against C for the same
question and the same model, and see whether the structured teaching process (C)
genuinely reads as clearer, not just nicer.

**What you walk away with:** evidence on whether instructions alone help — the
raw material for designing the instructions inside your future Claude skill.

## Experiment 3 — Mechanism isolation (which technique works)

**What you are finding out:** when you rewrite an answer, *which single technique*
does the real work. This one runs entirely inside the app using Gemini — no
website copy-paste needed.

The app has six rewriting techniques:

- **T1** — simpler vocabulary and sentences
- **T2** — reordering so nothing comes before what it depends on
- **T3** — spelling out the mechanism (how and why)
- **T4** — adding a concrete example or analogy
- **T5** — better layout (headings, short paragraphs, tables)
- **T6** — adjusting to the reader's background

**Step A — open the rewriter.** On the **Comparison** page, pick one answer (for
example your `Claude — baseline` for Question 1) and click **Transform this
answer**. This opens the Transformation workbench.

**Step B — run one technique at a time.** For the **same** starting answer, do a
separate run for each technique T1 through T6:

1. Choose the technique (just T1 on the first run).
2. Set the **transformation model** to **gemini → gemini-3.5-flash-lite**.
3. Make sure these are turned **on**: **Stage A (analysis)**, **Stage B
   (planning)**, **Stage D (fidelity review)**, and **Save as a variant**.
4. Click **Run transformation**.
5. Repeat for T2, then T3, and so on — one technique per run.

**Step C — read the results for each run:**

- **Per-treatment changes** shows the before and after, side by side, with the
  exact words that changed. This is how you see what the technique actually did.
- **Fidelity audit** warns if the rewrite changed a fact. Warnings marked
  **deterministic** are solid rules you can check by hand — trust those more
  than ones marked **llm_reviewer**.
- **Boundary check:** if a technique did something it was not supposed to (for
  example T1, which should only simplify words, also added headings), the app
  flags it. A flagged run is **not** a clean test of that technique — set it
  aside rather than counting it.

**What you walk away with:** a clear picture of which single technique produces
the biggest honest improvement with no fact changes. That technique is a strong
candidate for the core move in your Claude skill.

## Experiment 4 — Cross-model transformation

**What you are finding out:** when a rewrite helps, is it because of the
*technique*, or just because *a second capable model took another pass*? To tell
these apart you compare rewrites done by different models.

With only a Gemini key, you have two ways to do this:

**The automatic way (Gemini rewrites):** In the workbench (Experiment 3), rewrite
**ChatGPT's baseline** and **Claude's baseline** for the same question using
Gemini. When the rewriter is a different model from the original author, the app
shows a **Cross-model** note. This gives you two of the four combinations:
ChatGPT→Gemini and Claude→Gemini.

**The manual way (ChatGPT or Claude rewrites), to fill the other combinations:**

1. Copy a baseline answer (say, ChatGPT's answer to Question 1).
2. Open a new **Claude** chat and paste this, then the answer below it:

   ```text
   Below is an explanation. Rewrite it to be easier to understand and learn from, while keeping every fact, number, and technical claim exactly the same. Do not add any new facts.
   ```
3. Copy Claude's rewrite and import it on the Comparison page, labelled
   `ChatGPT→Claude rewrite`.
4. Do the same the other direction (Claude's answer rewritten by ChatGPT),
   labelled `Claude→ChatGPT rewrite`.

**How to read it:** compare the improvement across the different rewriters. If
rewrites help no matter who does the rewriting, the *technique* is doing the
work — good news for a portable skill. If answers only improve when one
particular model rewrites them, then it is that *model*, not the method, doing
the work.

**What you walk away with:** whether your teaching technique is something any
model can apply (so a Claude skill makes sense), or something only one model
happens to be good at.

## Experiment 5 — AI proxy (stand-in for human comprehension)

**What you are finding out:** which answer *contains* more of the information
needed to answer questions about the topic. Remember: this is an automated
stand-in, **not** proof that a human understood more.

**Step A — build a study.**

1. Click **Studies** in the menu, then **New study**.
2. Give it a name, for example `Caching — ChatGPT vs Claude`.
3. Pick the matching research question.
4. Under **Conditions**, select two answers that answer the **same** question —
   for example `ChatGPT — baseline` and `Claude — baseline`. (The app refuses to
   mix answers from different questions, on purpose.)

**Step B — write three questions about the topic.** The study starts with three
items. For this automated check, set **all three to Multiple choice** (the AI
proxy only understands multiple choice). For each item: type the question, type
the options, and click the small **radio circle** next to the correct one. If an
option represents a specific common misunderstanding, tick its **Misconception**
box.

Ready-made items for Question 1 (caching) — you can copy these to practise:

| Item | Question | Options (correct one in bold) |
| --- | --- | --- |
| 1 | `Which policy can confirm a write while the changed value is still only in the cache?` | Write-through / **Write-back** / Neither |
| 2 | `Under write-back, what happens first?` | **The cache accepts the change and backing storage is updated later** / Backing storage is updated before the cache / Both are always updated together |
| 3 | `A device confirms a write, then loses power before the pending cache change reaches storage. Which policy is more exposed to losing that change?` | Write-through / **Write-back** / Both exactly the same |

Then click **Create study**. You do **not** need to open it to participants or
share any link — leave it in **Draft**.

**Step C — run the AI proxy.**

1. On the study page, click the **AI proxy** tab.
2. Set **Proxy model** to **gemini → gemini-3.5-flash-lite**.
3. Click **Run AI proxy**.

The app asks Gemini the questions once **with no explanation at all**, and then
once **for each answer**.

**Step D — read it in the right order.**

1. Look at the **"Without any explanation"** result first. If Gemini already got
   everything right with no help, then your questions are too well-known to tell
   you anything — the useful ("diagnostic") items count will be **0**. Rewrite
   the questions to focus on specific details from the answers, and build a new
   study.
2. Then compare the two answers on **"correct with a supporting quote"** and on
   the **diagnostic items**. A higher number means Gemini found more answerable
   material in that answer. It does **not** mean a person learned more.

**What you walk away with:** a repeatable automated signal of which answer
carries more usable information — useful for spotting gaps, not for claiming
real-world learning.

---

# PART 3 — Saving your results and feeding the skill phase

## 3.1 What to save, and from where

This manual path does not create a big "experiment" file automatically, so you
save results in two simple ways:

- **From each study (Experiment 5):** on the study page, click **Export CSV**.
  This gives you a spreadsheet with the two answers' labels, the diagnostics, and
  the AI-proxy results. Save each one.
- **Everything else (judge scores, diagnostics, rewrite before/afters):** these
  show on screen. Keep a single plain-text or Word file — call it
  `research-notes.md` — and, for each question, jot down:
  - the Gemini judge scores for ChatGPT vs Claude (Experiment 1 and 2),
  - which single technique helped most and whether any fidelity warnings
    appeared (Experiment 3),
  - whether rewrites helped regardless of which model did them (Experiment 4),
  - the AI-proxy numbers (Experiment 5),
  - and any case where a rewrite made the answer *worse* — those are especially
    valuable.

Also keep a second file, `winning-explanations.md`, and paste the best
before-and-after rewrite examples you found. These become the examples inside
your Claude skill.

## 3.2 How this turns into a Claude skill

When you have run all five experiments across your questions, you will be able to
say, with evidence:

- which teaching **instructions** made answers clearer (Experiment 2),
- which single **technique** did the real work without breaking facts
  (Experiment 3),
- whether that technique is a **portable method** or just one model's talent
  (Experiment 4),
- and which answers carried more **answerable material** (Experiments 1 and 5).

Write your Claude skill around the winning instructions and techniques, using
your saved before-and-after examples as models. Then prove it directly: open a
fresh Claude chat, apply your new skill's instruction to a question, import that
new answer, and compare it against the plain baseline you saved. Repeat across
several questions.

## 3.3 The one claim you must not make

Nothing in this guide measures whether a **real person** understood more — the AI
proxy is a convenience, not a human. If you later want to claim your skill
improves real understanding, that still requires real people reading the answers
and being tested. Everything here gets you a well-grounded skill *candidate*; the
human proof is a separate, later step.
