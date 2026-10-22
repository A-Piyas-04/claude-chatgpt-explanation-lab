"use client";

/**
 * Participant assessment interface.
 *
 * Sits outside the researcher layout group on purpose: no navigation, no mode
 * banners, no branding that hints at what is being tested. The page shows the
 * explanation and the questions, and nothing else.
 *
 * Nothing on this page reveals the condition. The payload from the API is built
 * by a server-side allow-list, so model identity, provider, treatment names and
 * answer keys are not present in the data this component receives — not merely
 * hidden by the UI.
 *
 * Reading time is measured from when the explanation becomes visible to when
 * the participant moves to the questions, which is why reading and answering
 * are separate steps.
 */

import { useMutation, useQuery } from "@tanstack/react-query";
import { useParams } from "next/navigation";
import React from "react";

import { Markdown } from "@/lib/markdown";
import { ApiError, ParticipantSession, api } from "@/lib/api";

type Phase = "consent" | "prior" | "reading" | "questions" | "feedback" | "done" | "withdrawn";

interface Intro {
  study_name: string;
  intro_text: string;
  consent_text: string;
  collect_prior_knowledge: boolean;
  estimated_minutes: number;
  item_count: number;
}

const LIKERT_CLARITY = [
  "Very hard to follow",
  "Hard to follow",
  "Slightly hard",
  "Neither easy nor hard",
  "Slightly easy",
  "Easy to follow",
  "Very easy to follow",
];

const LIKERT_EFFORT = [
  "Very low effort",
  "Low effort",
  "Slightly low",
  "Moderate",
  "Slightly high",
  "High effort",
  "Very high effort",
];

export default function ParticipantPage() {
  const params = useParams<{ token: string }>();
  const token = params.token;

  const [phase, setPhase] = React.useState<Phase>("consent");
  const [session, setSession] = React.useState<ParticipantSession | null>(null);
  const [priorLevel, setPriorLevel] = React.useState("");
  const [priorFamiliarity, setPriorFamiliarity] = React.useState("");
  const [answers, setAnswers] = React.useState<Record<string, { option?: number; text?: string }>>({});
  const [clarity, setClarity] = React.useState<number | null>(null);
  const [effort, setEffort] = React.useState<number | null>(null);
  const [feedback, setFeedback] = React.useState("");

  const readingStart = React.useRef<number | null>(null);
  const questionsStart = React.useRef<number | null>(null);
  const readingSeconds = React.useRef<number | null>(null);

  const intro = useQuery({
    queryKey: ["participant-intro", token],
    queryFn: () => api.get<Intro>(`p/${token}`),
    retry: false,
  });

  const enter = useMutation({
    mutationFn: () =>
      api.post<ParticipantSession>(`p/${token}/enter`, {
        consent_given: true,
        self_reported_level: priorLevel || null,
        prior_knowledge: priorFamiliarity ? { familiarity: priorFamiliarity } : {},
      }),
    onSuccess: (data) => {
      setSession(data);
      readingStart.current = Date.now();
      setPhase("reading");
    },
  });

  const submit = useMutation({
    mutationFn: () => {
      const payload = (session?.items ?? []).map((item) => {
        const answer = answers[item.id] ?? {};
        return {
          item_id: item.id,
          selected_option_index: answer.option ?? null,
          text_answer: answer.text ?? "",
          likert_value: null,
          seconds_spent: null,
        };
      });
      const assessmentSeconds = questionsStart.current
        ? (Date.now() - questionsStart.current) / 1000
        : null;
      return api.post(`p/${token}/submit`, {
        participant_code: session!.participant_code,
        answers: payload,
        reading_seconds: readingSeconds.current,
        assessment_seconds: assessmentSeconds,
        clarity_rating: clarity,
        cognitive_effort_rating: effort,
        free_text_feedback: feedback,
      });
    },
    onSuccess: () => setPhase("done"),
  });

  const withdraw = useMutation({
    mutationFn: () =>
      api.post(`p/${token}/withdraw`, { participant_code: session?.participant_code }),
    onSuccess: () => setPhase("withdrawn"),
  });

  if (intro.isLoading) {
    return <Frame><p className="text-sm text-ink-muted">Loading…</p></Frame>;
  }

  if (intro.error) {
    const message =
      intro.error instanceof ApiError ? intro.error.message : "This link is not available.";
    return (
      <Frame>
        <h1 className="text-lg font-semibold">This study is not available</h1>
        <p className="mt-2 text-sm leading-relaxed text-ink-muted">{message}</p>
        <p className="mt-4 text-xs text-ink-faint">
          If you were sent this link by a researcher, please let them know.
        </p>
      </Frame>
    );
  }

  const data = intro.data!;

  // ---- consent ----------------------------------------------------------
  if (phase === "consent") {
    return (
      <Frame>
        <h1 className="text-xl font-semibold tracking-tight">{data.study_name}</h1>
        <p className="mt-1 text-sm text-ink-muted">
          About {data.estimated_minutes} minutes · {data.item_count} question
          {data.item_count === 1 ? "" : "s"}
        </p>

        <div className="mt-6 rounded-lg border border-line bg-canvas px-5 py-4">
          <Markdown source={data.consent_text} variant="compact" />
        </div>

        <div className="mt-6 flex flex-wrap items-center gap-3">
          <button
            onClick={() =>
              data.collect_prior_knowledge ? setPhase("prior") : enter.mutate()
            }
            disabled={enter.isPending}
            className="rounded-md bg-accent px-4 py-2 text-sm font-medium text-white hover:bg-accent-strong disabled:opacity-50"
          >
            {enter.isPending ? "Starting…" : "I consent — begin"}
          </button>
          <p className="text-xs text-ink-faint">You can stop at any time.</p>
        </div>
        {enter.error ? <ErrorNote error={enter.error} /> : null}
      </Frame>
    );
  }

  // ---- prior knowledge --------------------------------------------------
  if (phase === "prior") {
    return (
      <Frame>
        <h1 className="text-lg font-semibold tracking-tight">Before you start</h1>
        <p className="mt-1.5 text-sm leading-relaxed text-ink-muted">
          Two quick questions. There is no right answer, and this does not affect what you are
          shown.
        </p>

        <fieldset className="mt-6">
          <legend className="text-sm font-medium">
            How would you describe your experience with technical subjects like this one?
          </legend>
          <div className="mt-2 space-y-1.5">
            {[
              { value: "beginner", label: "New to this area" },
              { value: "intermediate", label: "Some working experience" },
              { value: "advanced", label: "Experienced in this area" },
            ].map((option) => (
              <label key={option.value} className="flex cursor-pointer items-center gap-2 text-sm">
                <input
                  type="radio"
                  name="level"
                  value={option.value}
                  checked={priorLevel === option.value}
                  onChange={() => setPriorLevel(option.value)}
                  className="h-4 w-4 text-accent"
                />
                {option.label}
              </label>
            ))}
          </div>
        </fieldset>

        <fieldset className="mt-6">
          <legend className="text-sm font-medium">
            Before today, how familiar were you with this specific topic?
          </legend>
          <div className="mt-2 space-y-1.5">
            {[
              { value: "none", label: "Not at all familiar" },
              { value: "heard_of", label: "I had heard of it" },
              { value: "some", label: "I understood the basics" },
              { value: "well", label: "I knew it well" },
            ].map((option) => (
              <label key={option.value} className="flex cursor-pointer items-center gap-2 text-sm">
                <input
                  type="radio"
                  name="familiarity"
                  value={option.value}
                  checked={priorFamiliarity === option.value}
                  onChange={() => setPriorFamiliarity(option.value)}
                  className="h-4 w-4 text-accent"
                />
                {option.label}
              </label>
            ))}
          </div>
        </fieldset>

        <button
          onClick={() => enter.mutate()}
          disabled={enter.isPending || !priorLevel || !priorFamiliarity}
          className="mt-7 rounded-md bg-accent px-4 py-2 text-sm font-medium text-white hover:bg-accent-strong disabled:opacity-50"
        >
          {enter.isPending ? "Starting…" : "Continue"}
        </button>
        {enter.error ? <ErrorNote error={enter.error} /> : null}
      </Frame>
    );
  }

  if (!session) return <Frame><p className="text-sm">Loading…</p></Frame>;

  // ---- reading ----------------------------------------------------------
  if (phase === "reading") {
    return (
      <Frame wide>
        <p className="text-2xs font-semibold uppercase tracking-[0.14em] text-ink-faint">
          Step 1 of 2 · Read
        </p>
        <h1 className="mt-1 text-lg font-semibold tracking-tight">
          Read this explanation carefully
        </h1>
        <p className="mt-1.5 text-sm text-ink-muted">
          Take as long as you need. You will not be able to come back to it, and you will be asked
          questions about it afterwards.
        </p>

        <article className="mt-7 rounded-lg border border-line bg-surface px-6 py-7 shadow-card sm:px-10 sm:py-9">
          <Markdown source={session.explanation.text} variant="reading" className="mx-auto" />
        </article>

        <div className="mt-7 flex flex-wrap items-center gap-3">
          <button
            onClick={() => {
              readingSeconds.current = readingStart.current
                ? (Date.now() - readingStart.current) / 1000
                : null;
              questionsStart.current = Date.now();
              setPhase("questions");
            }}
            className="rounded-md bg-accent px-4 py-2 text-sm font-medium text-white hover:bg-accent-strong"
          >
            I have finished reading — continue to the questions
          </button>
          <p className="text-xs text-ink-faint">The explanation is not shown again.</p>
        </div>
      </Frame>
    );
  }

  // ---- questions --------------------------------------------------------
  if (phase === "questions") {
    const required = session.items.filter((item) => item.is_required);
    const answered = required.filter((item) => {
      const answer = answers[item.id];
      return answer && (answer.option !== undefined || (answer.text ?? "").trim().length > 0);
    });
    const complete = answered.length === required.length;

    return (
      <Frame>
        <p className="text-2xs font-semibold uppercase tracking-[0.14em] text-ink-faint">
          Step 2 of 2 · Questions
        </p>
        <h1 className="mt-1 text-lg font-semibold tracking-tight">
          What did you take from the explanation?
        </h1>
        <p className="mt-1.5 text-sm leading-relaxed text-ink-muted">
          Answer from memory and in your own words. Partial answers are useful — please do not look
          anything up, and do not worry about getting it perfect.
        </p>

        <ol className="mt-7 space-y-7">
          {session.items.map((item, index) => (
            <li key={item.id}>
              <p className="text-sm font-medium leading-snug">
                <span className="mr-1.5 text-ink-faint">{index + 1}.</span>
                {item.prompt}
                {!item.is_required ? (
                  <span className="ml-1.5 text-xs font-normal text-ink-faint">(optional)</span>
                ) : null}
              </p>

              {item.format === "multiple_choice" ? (
                <div className="mt-2.5 space-y-1.5">
                  {item.options.map((option, optionIndex) => (
                    <label
                      key={optionIndex}
                      className="flex cursor-pointer items-start gap-2.5 rounded-md border border-line bg-surface px-3 py-2.5 text-sm hover:border-line-strong"
                    >
                      <input
                        type="radio"
                        name={item.id}
                        checked={answers[item.id]?.option === optionIndex}
                        onChange={() =>
                          setAnswers((prev) => ({
                            ...prev,
                            [item.id]: { ...prev[item.id], option: optionIndex },
                          }))
                        }
                        className="mt-0.5 h-4 w-4 shrink-0 text-accent"
                      />
                      <span className="leading-snug">{option}</span>
                    </label>
                  ))}
                </div>
              ) : (
                <textarea
                  rows={5}
                  value={answers[item.id]?.text ?? ""}
                  onChange={(e) =>
                    setAnswers((prev) => ({
                      ...prev,
                      [item.id]: { ...prev[item.id], text: e.target.value },
                    }))
                  }
                  placeholder="Write as much or as little as you like."
                  className="mt-2.5 w-full rounded-md border border-line-strong bg-surface px-3 py-2 text-sm leading-relaxed focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent"
                />
              )}
            </li>
          ))}
        </ol>

        <div className="mt-8 flex flex-wrap items-center gap-3 border-t border-line pt-6">
          <button
            onClick={() => setPhase("feedback")}
            disabled={!complete}
            className="rounded-md bg-accent px-4 py-2 text-sm font-medium text-white hover:bg-accent-strong disabled:opacity-50"
          >
            Continue
          </button>
          {!complete ? (
            <p className="text-xs text-ink-faint">
              {answered.length} of {required.length} required questions answered.
            </p>
          ) : null}
        </div>
      </Frame>
    );
  }

  // ---- feedback ---------------------------------------------------------
  if (phase === "feedback") {
    return (
      <Frame>
        <h1 className="text-lg font-semibold tracking-tight">Two last questions</h1>
        <p className="mt-1.5 text-sm text-ink-muted">About the explanation itself.</p>

        <LikertScale
          legend="How easy was the explanation to follow?"
          labels={LIKERT_CLARITY}
          value={clarity}
          onChange={setClarity}
          name="clarity"
        />
        <LikertScale
          legend="How much mental effort did it take to understand?"
          labels={LIKERT_EFFORT}
          value={effort}
          onChange={setEffort}
          name="effort"
        />

        <div className="mt-7">
          <label htmlFor="feedback" className="text-sm font-medium">
            Anything else? (optional)
          </label>
          <p className="mt-0.5 text-xs text-ink-faint">
            If a particular part was confusing, naming it is especially useful.
          </p>
          <textarea
            id="feedback"
            rows={4}
            value={feedback}
            onChange={(e) => setFeedback(e.target.value)}
            className="mt-2 w-full rounded-md border border-line-strong bg-surface px-3 py-2 text-sm leading-relaxed focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent"
          />
        </div>

        <div className="mt-8 flex flex-wrap items-center gap-3 border-t border-line pt-6">
          <button
            onClick={() => submit.mutate()}
            disabled={submit.isPending || clarity === null || effort === null}
            className="rounded-md bg-accent px-4 py-2 text-sm font-medium text-white hover:bg-accent-strong disabled:opacity-50"
          >
            {submit.isPending ? "Submitting…" : "Submit"}
          </button>
          {clarity === null || effort === null ? (
            <p className="text-xs text-ink-faint">Please answer both rating questions.</p>
          ) : null}
        </div>
        {submit.error ? <ErrorNote error={submit.error} /> : null}
      </Frame>
    );
  }

  // ---- done -------------------------------------------------------------
  if (phase === "done") {
    return (
      <Frame>
        <h1 className="text-xl font-semibold tracking-tight">Thank you</h1>
        <p className="mt-2 text-sm leading-relaxed text-ink-muted">
          Your responses have been recorded. Results are reported only in aggregate, never
          individually.
        </p>
        <p className="mt-4 text-sm leading-relaxed text-ink-muted">
          We have not told you how you scored, and that is deliberate: knowing would change the
          results if you take part in a follow-up.
        </p>

        <div className="mt-7 rounded-lg border border-line bg-canvas px-4 py-3">
          <p className="text-xs font-medium">Changed your mind?</p>
          <p className="mt-1 text-xs leading-relaxed text-ink-muted">
            You can delete your responses. This cannot be undone, and nothing of yours will be
            kept.
          </p>
          <button
            onClick={() => withdraw.mutate()}
            disabled={withdraw.isPending}
            className="mt-3 rounded-md border border-danger/30 bg-danger-soft px-3 py-1.5 text-xs font-medium text-danger hover:bg-danger/10 disabled:opacity-50"
          >
            {withdraw.isPending ? "Deleting…" : "Withdraw and delete my responses"}
          </button>
          {withdraw.error ? <ErrorNote error={withdraw.error} /> : null}
        </div>

        <p className="mt-6 font-mono text-2xs text-ink-faint">
          Your anonymous code: {session.participant_code}
        </p>
      </Frame>
    );
  }

  // ---- withdrawn --------------------------------------------------------
  return (
    <Frame>
      <h1 className="text-xl font-semibold tracking-tight">Your responses have been deleted</h1>
      <p className="mt-2 text-sm leading-relaxed text-ink-muted">
        Nothing you submitted has been kept. Thank you for your time.
      </p>
    </Frame>
  );
}

function Frame({ children, wide = false }: { children: React.ReactNode; wide?: boolean }) {
  return (
    <div className="min-h-screen bg-canvas">
      <div className={`mx-auto px-5 py-10 sm:py-14 ${wide ? "max-w-3xl" : "max-w-2xl"}`}>
        {children}
      </div>
    </div>
  );
}

function LikertScale({
  legend,
  labels,
  value,
  onChange,
  name,
}: {
  legend: string;
  labels: string[];
  value: number | null;
  onChange: (value: number) => void;
  name: string;
}) {
  return (
    <fieldset className="mt-7">
      <legend className="text-sm font-medium">{legend}</legend>
      <div className="mt-2.5 space-y-1.5">
        {labels.map((label, index) => (
          <label
            key={index}
            className="flex cursor-pointer items-center gap-2.5 rounded-md border border-line bg-surface px-3 py-2 text-sm hover:border-line-strong"
          >
            <input
              type="radio"
              name={name}
              checked={value === index + 1}
              onChange={() => onChange(index + 1)}
              className="h-4 w-4 text-accent"
            />
            <span>{label}</span>
          </label>
        ))}
      </div>
    </fieldset>
  );
}

function ErrorNote({ error }: { error: unknown }) {
  const message = error instanceof Error ? error.message : String(error);
  return (
    <div className="mt-4 rounded-md border border-danger/30 bg-danger-soft px-3 py-2.5">
      <p className="text-xs leading-relaxed text-danger">{message}</p>
    </div>
  );
}
