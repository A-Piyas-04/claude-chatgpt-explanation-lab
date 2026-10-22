# Restart the ChatGPT–Claude experiment with a Gemini API key

Follow these steps **in order** for a fresh run. Create a new question, import new ChatGPT and Claude answers, and create a new study. You do **not** need to delete previous work or hire participants. Your only repeated copy-paste work is moving the two web-chat answers into this app; Gemini handles the analysis and AI proxy check. The AI proxy is an automated check of answerability, not a measurement of human learning.

## 1. Add your Gemini key and restart the app

Stop the old API and web terminals with **Ctrl+C**. Open the project's root folder, `E:\Projects\My Apps\explanation-lab`, in File Explorer. Open the `.env` file there in a text editor. If it does not exist, make a copy of `.env.example` in the same folder and name the copy `.env`.

Add or replace this one line in `.env` with **your actual Gemini API key**:

```text
GEMINI_API_KEY=your-key-here
```

Save the file. Do not paste the key into ChatGPT, Claude, or this manual. Now open **two new PowerShell terminals** and run the commands below. Keep both terminals open while using the app.

```powershell
cd "E:\Projects\My Apps\explanation-lab"
cd apps/api
# Install the current backend dependencies. This can be skipped on later restarts.
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m uvicorn explanationlab.main:app --reload
```

```powershell
cd "E:\Projects\My Apps\explanation-lab"
cd apps/web
npm run dev
```

Open <http://localhost:3000> and refresh the page. The header should say **gemini live**, and **Library → Models** should show `gemini-3.5-flash-lite`. If the header still says demo, check the key line in the **root** `.env`, then stop and restart Terminal 1.

Google lists this model on an API free tier, subject to your project's limits. Check your project's plan and active limits in Google AI Studio before running many calls; a paid-tier project can incur charges. The app's cost display is an estimate and does not know your free-tier allowance. [Google pricing](https://ai.google.dev/gemini-api/docs/pricing) · [Google rate limits](https://ai.google.dev/gemini-api/docs/rate-limits).

## 2. Create a **new** research question

Go to **Library → Questions → Add question**. For a first run, use:

| Field | Enter |
| --- | --- |
| Question | `How do write-through and write-back caches handle a write, and what are the tradeoffs?` |
| Domain | `software_engineering` |
| Topic | `caching` |
| Difficulty | `moderate` |

In **Factual checklist**, put one verified claim per line:

```text
Write-through writes to the cache and backing store before the write is complete.
Write-back writes to the cache first and sends changed data to backing storage later.
Write-back can lose unflushed changes if the cache fails; write-through performs more immediate backing-store writes.
```

Click **Create question**. This caching question gives you a concrete first run, but Gemini may already know its answers. For a useful skill experiment, repeat these steps with a real topic and factual checklist you can verify from your own source material. Do not treat the example's score as proof of skill quality.

## 3. Collect and import the two source answers

Open a **new chat** in ChatGPT web and another **new chat** in Claude web. Copy the exact question from step 2 into each chat as the entire prompt. Record the displayed model name and date. Copy each complete answer without editing it. Your web subscriptions work for this; no OpenAI or Anthropic API key is needed.

In **Comparison**, select the question and click **Import a web-chat answer**. Do this once per answer:

| Field | ChatGPT answer | Claude answer |
| --- | --- | --- |
| Provider | `openai` | `anthropic` |
| Model as labelled in the interface | Exact displayed model name | Exact displayed model name |
| Answer label | `ChatGPT web — original` | `Claude web — original` |
| Pasted answer | Full ChatGPT answer | Full Claude answer |
| Capture notes | Date, exact displayed model, fresh chat, settings | Date, exact displayed model, fresh chat, settings |

Click **Import answer** each time. Both must show **imported** and have **no SYNTHETIC badge**. The answer labels distinguish the conditions in study results. **Comparison** computes text diagnostics automatically. These describe writing features; they do not measure learning.

## 4. Run the automated analysis and transformation

Work on one imported answer at a time. In every model selector below, choose **gemini → gemini-3.5-flash-lite**. Each click below makes a real Gemini API call and saves its result in the app.

1. **Comparison:** select the two imported answers. The text diagnostics appear automatically. For each answer, select Gemini under **Judge model** and click **Run blinded judge**. Read the judge score as a model's opinion, not a comprehension score.
2. **Pedagogical analysis:** select an imported answer and click **Extract concept graph**. Check the inferred prerequisites against your own knowledge; the edges are hypotheses.
3. **Transformation:** select the imported **Claude** answer as the source. Choose one treatment first, such as **T2 sequencing** or **T3 mechanism**. Select Gemini as the transformation model. Leave **Stage A — analysis**, **Stage B — planning**, **Stage D — LLM fidelity review**, and **Save as a variant** on, then click **Run transformation**. Read the before/after changes and factual warnings. Check the new text against the original and factual checklist.

The saved transformed answer is real Gemini API output derived from a real Claude web answer. It is **not** a Claude answer and cannot by itself prove a Claude skill works. You may use it to discover a promising teaching move, then instruct Claude web with that move and import Claude's new answer to test the skill idea directly.

## 5. Create an automated comparison without participants

Return to **Human evaluation / Studies → New study**. Select the **original imported ChatGPT and Claude answers** for the same question. Name it `ChatGPT vs Claude — caching answerability`. The balance and prior-knowledge switches apply only to human participants; you can leave them at their defaults.

The builder starts with three items. Keep dimensions **A**, **B**, and **C**, and set **all three** formats to **Multiple choice**. The AI proxy currently accepts only multiple-choice items. Enter the following; click the **radio circle** beside each bold correct option:

| Dimension | Question | Options; correct one in **bold** |
| --- | --- | --- |
| A, immediate | `Which policy can acknowledge a write while the changed value is still only in the cache?` | `Write-through`; **`Write-back`**; `Neither` |
| B, mechanism | `What happens first under write-back?` | **`The cache accepts the change; backing storage is updated later`**; `Backing storage is updated before the cache`; `Both are always updated together` |
| C, transfer | `A device acknowledges a write, then loses power before pending cache changes reach storage. Which policy is more exposed to losing that change?` | `Write-through`; **`Write-back`**; `Both have exactly the same exposure` |

For your own topic, use questions whose correct answers are verifiable against source material. Include a question that applies a rule to a new case. Familiar textbook questions may be known to Gemini before it reads either answer, so they are weak evidence of added answerability.

Click **Create study**. Open the new study and check the condition labels and that neither answer has a **SYNTHETIC** badge. **Leave the study in Draft**; opening it and sharing a participant link are unnecessary for this path.

## 6. Run and interpret the AI proxy

On the study page, click **AI proxy**. Select **gemini → gemini-3.5-flash-lite**, then **Run AI proxy**. The app makes one Gemini call **without an explanation** and one call for **each stored answer**. It scores each multiple-choice selection and checks for a supporting quote in the answer. The report is saved on that tab; rerunning replaces the displayed *latest* result and keeps earlier reports in the database. No participant is created.

Read **Without any explanation** first. If Gemini gets all items right, **Diagnostic items = 0**; rewrite the questions around less familiar but verifiable details, and create a new study. Then compare **Correct with quote** and **On diagnostic items** for the two answers. Open **Inspect** to see each choice and quote. A higher count means Gemini found more answerable material in that text under this test. It does **not** show that a person learned more. One deterministic Gemini pass per answer is useful for finding gaps, not a statistical estimate.

To build a **Claude skill**, write a candidate teaching instruction from the findings. Apply it in a **fresh Claude web chat** to the same question, import the new Claude answer, and create a **second study with original Claude versus instructed Claude**. Run the AI proxy again. Repeat across several questions and topics, checking factual accuracy and fidelity as well as answerability. This gives real model outputs and repeatable automated observations for choosing a skill candidate. A claim that the skill improves *human comprehension* still requires actual users later; AI cannot stand in for them.

**What you should see at the end:** two imported answers, automatic text diagnostics, saved Gemini judge/analysis output, an optional Gemini transformation, and a saved **AI proxy** result for a new study. **Setup** stores the answers and questions. **Submissions / Grading / Results** are for real people and will remain empty here. Gemini-assisted short-answer grading needs a real submitted free-text answer.

**Which page to use:** use **Comparison → Pedagogical analysis / Transformation → Studies → AI proxy** for this ChatGPT–Claude experiment. **Experiment Studio** can automate Gemini-source batches, but it cannot pull answers from your ChatGPT or Claude web subscriptions.
