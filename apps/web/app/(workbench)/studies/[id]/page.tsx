"use client";

/**
 * Study detail: participant link, submissions, grading queue and results.
 *
 * The grading view is where the platform's hardest rule lives: an AI-suggested
 * score is shown next to the human field but can never become the final score
 * on its own. The researcher has to type a number.
 */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useParams } from "next/navigation";
import React from "react";

import {
  Badge,
  Button,
  Caveat,
  Card,
  CardHeader,
  Disclosure,
  EmptyState,
  ErrorState,
  Field,
  Input,
  KeyValue,
  Loading,
  Mono,
  PageHeader,
  Select,
  StatusDot,
  SyntheticBadge,
  Table,
  Tabs,
  Td,
  Textarea,
  Tr,
  formatUsd,
} from "@/components/ui";
import { StudyResultsView } from "@/components/results";
import { Markdown } from "@/lib/markdown";
import { Study, StudyResults, api } from "@/lib/api";
import { groupModels, modelKey, parseModelKey, useModels } from "@/lib/hooks";

interface StudyDetail {
  study: Study;
  participant_url_path: string;
  conditions: {
    id: string;
    label: string;
    response_id: string;
    model_id: string;
    provider: string;
    treatments: string[];
    is_enabled: boolean;
    is_synthetic: boolean;
    assigned: number;
  }[];
  items: {
    id: string;
    order_index: number;
    format: string;
    dimension: string;
    prompt: string;
    options: string[];
    correct_option_index: number | null;
    misconception_option_indexes: number[];
    max_score: number;
    rubric_id: string | null;
  }[];
  participants: { assigned: number; submitted: number; withdrawn: number };
}

interface SubmissionRow {
  summary: {
    submission_id: string;
    participant_code: string;
    condition_id: string;
    comprehension_score: number | null;
    comprehension_complete: boolean;
    pending_grading_items: number;
    misconception_count: number;
    perceived_clarity: number | null;
    cognitive_effort: number | null;
    reading_seconds: number | null;
    assessment_seconds: number | null;
    by_dimension: Record<string, { earned: number; available: number; score_ratio: number | null; complete: boolean }>;
  };
  condition_label: string;
  items: {
    item_response_id: string;
    item_id: string;
    format: string;
    dimension: string;
    prompt: string;
    max_score: number;
    selected_option_index: number | null;
    text_answer: string;
    likert_value: number | null;
    auto_score: number | null;
    ai_suggested_score: number | null;
    ai_rationale: string;
    human_score: number | null;
    final_score: number | null;
    grading_mode: string;
    misconception_detected: boolean;
    grader_notes: string;
    needs_grading: boolean;
  }[];
}

interface ProxyEvaluation {
  id: string;
  evidence_class: "ai_proxy_answerability";
  provider: string;
  model_id: string;
  item_count: number;
  baseline_correct_count: number;
  diagnostic_item_count: number;
  estimated_cost_usd: number;
  warning: string;
  conditions: {
    condition_id: string;
    label: string;
    grounded_correct: number;
    diagnostic_grounded_correct: number;
    items: {
      item_id: string;
      question: string;
      correct: boolean;
      quote_found: boolean;
      grounded_correct: boolean;
      baseline_correct: boolean;
      evidence_quote: string;
    }[];
  }[];
}

export default function StudyDetailPage() {
  const params = useParams<{ id: string }>();
  const id = params.id;
  const queryClient = useQueryClient();
  const models = useModels();
  const [tab, setTab] = React.useState("setup");
  const [aiGradeKey, setAiGradeKey] = React.useState("");
  const [proxyKey, setProxyKey] = React.useState("");
  const [report, setReport] = React.useState<string | null>(null);
  const [copied, setCopied] = React.useState(false);

  const detail = useQuery({
    queryKey: ["study", id],
    queryFn: () => api.get<StudyDetail>(`studies/${id}`),
  });
  const submissions = useQuery({
    queryKey: ["study-submissions", id],
    queryFn: () => api.get<SubmissionRow[]>(`studies/${id}/submissions`),
  });
  const results = useQuery({
    queryKey: ["study-results", id],
    queryFn: () => api.get<StudyResults>(`studies/${id}/results`),
  });
  const proxy = useQuery({
    queryKey: ["study-proxy", id],
    queryFn: () => api.get<ProxyEvaluation | null>(`studies/${id}/proxy-evaluation`),
  });

  const setStatus = useMutation({
    mutationFn: (status: string) => api.post(`studies/${id}/status`, { status }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["study", id] }),
  });

  const rotate = useMutation({
    mutationFn: () => api.post(`studies/${id}/rotate-token`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["study", id] }),
  });

  const aiGrade = useMutation({
    mutationFn: () => {
      const { provider, model_id } = parseModelKey(aiGradeKey);
      return api.post<{ ai_suggestions_created: number; skipped: number; errors: string[]; estimated_cost_usd: number; note: string }>(
        `studies/${id}/ai-grade?provider=${provider}&model_id=${encodeURIComponent(model_id)}`,
      );
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["study-submissions", id] }),
  });

  const runProxy = useMutation({
    mutationFn: () => {
      const { provider, model_id } = parseModelKey(proxyKey);
      return api.post<ProxyEvaluation>(`studies/${id}/proxy-evaluation`, { provider, model_id });
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["study-proxy", id] }),
  });

  const makeReport = useMutation({
    mutationFn: () => api.post<{ body_markdown: string }>(`studies/${id}/report`),
    onSuccess: (data) => {
      setReport(data.body_markdown);
      setTab("report");
    },
  });

  if (detail.isLoading) return <Loading label="Loading study" />;
  if (detail.error) return <ErrorState error={detail.error} retry={detail.refetch} />;

  const data = detail.data!;
  const study = data.study;
  const participantUrl =
    typeof window !== "undefined"
      ? `${window.location.origin}${data.participant_url_path}`
      : data.participant_url_path;
  const pendingGrading = (submissions.data ?? []).reduce(
    (total, row) => total + row.summary.pending_grading_items,
    0,
  );
  const grouped = groupModels(models.data);

  return (
    <>
      <PageHeader
        eyebrow="Human comprehension study"
        title={study.name}
        description={
          <span className="flex flex-wrap items-center gap-2">
            <span className="inline-flex items-center gap-1.5">
              <StatusDot status={study.status} />
              {study.status}
            </span>
            <span>·</span>
            <span>{data.participants.submitted} submission(s)</span>
            <span>·</span>
            <span>seed {study.seed}</span>
          </span>
        }
        actions={
          <>
            {study.status === "draft" ? (
              <Button
                variant="primary"
                loading={setStatus.isPending}
                onClick={() => setStatus.mutate("open")}
              >
                Open for participants
              </Button>
            ) : study.status === "open" ? (
              <Button loading={setStatus.isPending} onClick={() => setStatus.mutate("closed")}>
                Close study
              </Button>
            ) : (
              <Button loading={setStatus.isPending} onClick={() => setStatus.mutate("open")}>
                Reopen
              </Button>
            )}
            <a href={api.downloadUrl(`studies/${id}/export?format=csv`)} download>
              <Button>Export CSV</Button>
            </a>
            <Button variant="primary" loading={makeReport.isPending} onClick={() => makeReport.mutate()}>
              Generate report
            </Button>
          </>
        }
      />

      {setStatus.error ? <ErrorState error={setStatus.error} /> : null}

      <Tabs
        tabs={[
          { id: "setup", label: "Setup" },
          { id: "grading", label: "Grading", count: pendingGrading },
          { id: "results", label: "Results" },
          { id: "proxy", label: "AI proxy" },
          { id: "report", label: "Report" },
        ]}
        active={tab}
        onChange={setTab}
      />

      {tab === "setup" ? (
        <div className="space-y-5">
          <Card>
            <CardHeader
              title="Participant link"
              description="Grants access to the assessment only — it carries no researcher privileges"
              actions={
                <Button size="sm" loading={rotate.isPending} onClick={() => rotate.mutate()}>
                  Rotate token
                </Button>
              }
            />
            <div className="px-4 py-3">
              {study.status !== "open" ? (
                <Caveat tone="warn">
                  The study is {study.status}. Open it before sharing the link, or participants
                  will be turned away.
                </Caveat>
              ) : null}
              <div className="mt-2 flex flex-wrap items-center gap-2">
                <code className="min-w-0 flex-1 break-all rounded-md border border-line bg-canvas px-3 py-2 font-mono text-xs">
                  {participantUrl}
                </code>
                <Button
                  size="sm"
                  onClick={() => {
                    navigator.clipboard?.writeText(participantUrl);
                    setCopied(true);
                    setTimeout(() => setCopied(false), 1800);
                  }}
                >
                  {copied ? "Copied" : "Copy"}
                </Button>
                <Link href={data.participant_url_path} target="_blank">
                  <Button size="sm">Preview</Button>
                </Link>
              </div>
              <Caveat className="mt-3">
                Participants are identified by a random code only. No name, email or IP address is
                collected, individual results are never published, and a participant can delete
                their own data from the assessment page.
              </Caveat>
            </div>
          </Card>

          <Card>
            <CardHeader
              title="Conditions"
              description="Blinded to participants — these labels never leave the researcher API"
            />
            <Table head={["Arm", "Stimulus", "Treatments", "Assigned"]} className="rounded-none border-0">
              {data.conditions.map((condition) => (
                <Tr key={condition.id}>
                  <Td className="text-xs font-medium">
                    <span className="flex flex-wrap items-center gap-1.5">
                      {condition.label}
                      {condition.is_synthetic ? <SyntheticBadge /> : null}
                    </span>
                  </Td>
                  <Td className="font-mono text-2xs">
                    <Link
                      href={`/compare?response=${condition.response_id}`}
                      className="text-accent underline"
                    >
                      {condition.model_id}
                    </Link>
                  </Td>
                  <Td className="text-xs">
                    {condition.treatments.length ? (
                      <span className="flex flex-wrap gap-1">
                        {condition.treatments.map((t) => (
                          <Badge key={t} tone="accent">
                            {t}
                          </Badge>
                        ))}
                      </span>
                    ) : (
                      <span className="text-ink-faint">untransformed</span>
                    )}
                  </Td>
                  <Td className="tabular-nums text-xs">{condition.assigned}</Td>
                </Tr>
              ))}
            </Table>
            <div className="border-t border-line px-4 py-3">
              <KeyValue
                columns={3}
                items={[
                  { label: "Allocation", value: study.balance_conditions ? "balanced, seeded" : "random, seeded" },
                  { label: "Seed", value: <Mono>{study.seed}</Mono> },
                  {
                    label: "Cap per arm",
                    value: study.max_per_condition ?? "none",
                  },
                ]}
              />
            </div>
          </Card>

          <Card>
            <CardHeader title="Assessment items" description={`${data.items.length} items`} />
            <div className="space-y-3 px-4 py-3">
              {data.items.map((item, index) => (
                <div key={item.id} className="rounded-md border border-line bg-canvas px-3 py-2.5">
                  <div className="flex flex-wrap items-center gap-1.5">
                    <Badge>{index + 1}</Badge>
                    <Badge tone="accent">{item.format.replace(/_/g, " ")}</Badge>
                    <Badge>{item.dimension.replace(/_/g, " ")}</Badge>
                    <span className="text-2xs text-ink-faint">max {item.max_score}</span>
                  </div>
                  <p className="mt-1.5 text-xs">{item.prompt}</p>
                  {item.options.length > 0 ? (
                    <ol className="mt-1.5 space-y-0.5 text-2xs text-ink-muted">
                      {item.options.map((option, optionIndex) => (
                        <li key={optionIndex}>
                          {optionIndex === item.correct_option_index ? (
                            <span className="font-semibold text-accent">✓ </span>
                          ) : item.misconception_option_indexes.includes(optionIndex) ? (
                            <span className="font-semibold text-warn">△ </span>
                          ) : (
                            <span className="text-ink-faint">· </span>
                          )}
                          {option}
                        </li>
                      ))}
                    </ol>
                  ) : null}
                </div>
              ))}
              <Caveat>
                Item order is randomised per participant within format blocks, with free-text
                items always after multiple-choice ones.
              </Caveat>
            </div>
          </Card>

          <Disclosure summary="Consent notice shown to participants">
            <Markdown source={study.consent_text} variant="compact" />
          </Disclosure>
        </div>
      ) : null}

      {tab === "grading" ? (
        <div className="space-y-5">
          <Card>
            <CardHeader
              title="AI-assisted grading"
              description="Produces suggestions only — a suggestion never becomes a final score by itself"
            />
            <div className="flex flex-wrap items-end gap-3 px-4 py-3">
              <Field label="Grading model" className="min-w-[14rem]">
                <Select value={aiGradeKey} onChange={(e) => setAiGradeKey(e.target.value)}>
                  <option value="">Select…</option>
                  {[...grouped.entries()].map(([provider, entries]) => (
                    <optgroup key={provider} label={provider}>
                      {entries
                        .filter((m) => m.is_enabled)
                        .map((m) => (
                          <option key={modelKey(m)} value={modelKey(m)}>
                            {m.model_id}
                          </option>
                        ))}
                    </optgroup>
                  ))}
                </Select>
              </Field>
              <Button
                disabled={!aiGradeKey || pendingGrading === 0}
                loading={aiGrade.isPending}
                onClick={() => aiGrade.mutate()}
              >
                Suggest grades for {pendingGrading} ungraded answer(s)
              </Button>
            </div>
            {aiGrade.data ? (
              <div className="border-t border-line px-4 py-3">
                <KeyValue
                  columns={3}
                  items={[
                    { label: "Suggestions created", value: aiGrade.data.ai_suggestions_created },
                    { label: "Skipped", value: aiGrade.data.skipped },
                    { label: "Estimated cost", value: formatUsd(aiGrade.data.estimated_cost_usd) },
                  ]}
                />
                <Caveat tone="warn" className="mt-3">
                  {aiGrade.data.note}
                </Caveat>
                {aiGrade.data.errors.length > 0 ? (
                  <ul className="mt-2 space-y-1 text-2xs text-danger">
                    {aiGrade.data.errors.map((error, i) => (
                      <li key={i}>{error}</li>
                    ))}
                  </ul>
                ) : null}
              </div>
            ) : null}
            {aiGrade.error ? (
              <div className="border-t border-line px-4 py-3">
                <ErrorState error={aiGrade.error} />
              </div>
            ) : null}
          </Card>

          {submissions.isLoading ? (
            <Loading label="Loading submissions" />
          ) : (submissions.data ?? []).length === 0 ? (
            <EmptyState title="No submissions yet">
              Share the participant link. Submissions appear here as they arrive.
            </EmptyState>
          ) : (
            (submissions.data ?? []).map((row) => (
              <SubmissionCard key={row.summary.submission_id} row={row} studyId={id} />
            ))
          )}
        </div>
      ) : null}

      {tab === "results" ? (
        results.isLoading ? (
          <Loading label="Aggregating results" />
        ) : results.error ? (
          <ErrorState error={results.error} retry={results.refetch} />
        ) : (results.data?.totals.submitted ?? 0) === 0 ? (
          <EmptyState title="No submissions yet">
            Results appear once at least one participant has submitted.
          </EmptyState>
        ) : (
          <StudyResultsView results={results.data!} />
        )
      ) : null}

      {tab === "proxy" ? (
        <div className="space-y-5">
          <Caveat tone="warn">
            An AI proxy is not a participant. This audit checks whether Gemini can answer the
            study questions with quotes from each explanation, and which questions it already
            knew without reading anything. Its scores never enter human Results.
          </Caveat>
          <Card>
            <CardHeader title="Run automated answerability audit" description="Requires 2–4 real answers and 1–10 multiple-choice items." />
            <div className="flex flex-wrap items-end gap-3 px-4 py-3">
              <Field label="Proxy model" className="min-w-[15rem]">
                <Select value={proxyKey} onChange={(e) => setProxyKey(e.target.value)}>
                  <option value="">Select…</option>
                  {[...grouped.entries()].map(([provider, entries]) => (
                    <optgroup key={provider} label={provider}>
                      {entries.filter((model) => model.is_enabled).map((model) => (
                        <option key={modelKey(model)} value={modelKey(model)}>{model.model_id}</option>
                      ))}
                    </optgroup>
                  ))}
                </Select>
              </Field>
              <Button variant="primary" disabled={!proxyKey} loading={runProxy.isPending} onClick={() => runProxy.mutate()}>
                Run AI proxy
              </Button>
            </div>
            {runProxy.error ? <div className="px-4 pb-3"><ErrorState error={runProxy.error} /></div> : null}
          </Card>
          {proxy.data ? (
            <Card>
              <CardHeader title="Latest AI proxy result" description={`${proxy.data.provider}/${proxy.data.model_id} · estimated ${formatUsd(proxy.data.estimated_cost_usd)}`} />
              <div className="space-y-4 px-4 py-4">
                <Caveat tone="warn">{proxy.data.warning}</Caveat>
                <p className="text-sm">
                  Without any explanation, Gemini already answered {proxy.data.baseline_correct_count}/{proxy.data.item_count} items correctly.
                  {proxy.data.diagnostic_item_count === 0 ? " No item can test added answerability in this audit; write harder, less familiar questions." : ` ${proxy.data.diagnostic_item_count} item(s) remain diagnostic.`}
                </p>
                <Table head={["Answer", "Correct with quote", "On diagnostic items"]}>
                  {proxy.data.conditions.map((condition) => (
                    <Tr key={condition.condition_id}>
                      <Td>{condition.label}</Td>
                      <Td>{condition.grounded_correct}/{proxy.data!.item_count}</Td>
                      <Td>{condition.diagnostic_grounded_correct}/{proxy.data!.diagnostic_item_count}</Td>
                    </Tr>
                  ))}
                </Table>
                {proxy.data.conditions.map((condition) => (
                  <Disclosure key={condition.condition_id} summary={`Inspect ${condition.label}`}>
                    <ul className="space-y-2 text-xs">
                      {condition.items.map((item) => (
                        <li key={item.item_id}>
                          <strong>{item.grounded_correct ? "Supported" : "Not supported"}</strong> · {item.question}
                          {item.baseline_correct ? " · Gemini knew this without the text" : ""}
                          {item.evidence_quote ? <p className="mt-1 italic">Quote: {item.evidence_quote}{item.quote_found ? "" : " (not found verbatim)"}</p> : null}
                        </li>
                      ))}
                    </ul>
                  </Disclosure>
                ))}
              </div>
            </Card>
          ) : null}
        </div>
      ) : null}

      {tab === "report" ? (
        report ? (
          <Card>
            <CardHeader
              title="Study report"
              actions={
                <a href={api.downloadUrl(`studies/${id}/export?format=markdown`)} download>
                  <Button size="sm">Download .md</Button>
                </a>
              }
            />
            <div className="px-5 py-4">
              <Markdown source={report} variant="compact" />
            </div>
          </Card>
        ) : (
          <EmptyState
            title="No report generated yet"
            action={
              <Button variant="primary" loading={makeReport.isPending} onClick={() => makeReport.mutate()}>
                Generate report
              </Button>
            }
          >
            The report states the design, the per-condition comprehension results with their
            uncertainty, and the limitations. It leaves the findings section for you to write.
          </EmptyState>
        )
      ) : null}
    </>
  );
}

function SubmissionCard({ row, studyId }: { row: SubmissionRow; studyId: string }) {
  const queryClient = useQueryClient();
  const [drafts, setDrafts] = React.useState<Record<string, { score: string; notes: string; misconception: boolean }>>(
    {},
  );

  const grade = useMutation({
    mutationFn: ({ itemResponseId, score, notes, misconception }: { itemResponseId: string; score: number; notes: string; misconception: boolean }) =>
      api.post(`item-responses/${itemResponseId}/grade`, {
        human_score: score,
        grader_notes: notes,
        misconception_detected: misconception,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["study-submissions", studyId] });
      queryClient.invalidateQueries({ queryKey: ["study-results", studyId] });
    },
  });

  const summary = row.summary;

  return (
    <Card>
      <CardHeader
        title={
          <span className="flex flex-wrap items-center gap-2">
            <Mono>{summary.participant_code}</Mono>
            <Badge>{row.condition_label}</Badge>
            {summary.pending_grading_items > 0 ? (
              <Badge tone="warn">{summary.pending_grading_items} to grade</Badge>
            ) : (
              <Badge tone="success">fully graded</Badge>
            )}
          </span>
        }
        description={
          <span className="flex flex-wrap gap-x-3 gap-y-0.5">
            <span>
              Comprehension:{" "}
              {summary.comprehension_score === null
                ? "pending"
                : `${Math.round(summary.comprehension_score * 100)}%`}
              {!summary.comprehension_complete ? " (incomplete)" : ""}
            </span>
            <span>·</span>
            <span>Clarity {summary.perceived_clarity ?? "—"}/7</span>
            <span>·</span>
            <span>Effort {summary.cognitive_effort ?? "—"}/7</span>
            <span>·</span>
            <span>
              Read {summary.reading_seconds ? `${Math.round(summary.reading_seconds)}s` : "—"}
            </span>
          </span>
        }
      />
      <div className="divide-y divide-line">
        {row.items.map((item) => {
          const draft = drafts[item.item_response_id] ?? {
            score: item.human_score !== null ? String(item.human_score) : "",
            notes: item.grader_notes,
            misconception: item.misconception_detected,
          };
          const isObjective = item.format === "multiple_choice";
          return (
            <div key={item.item_response_id} className="px-4 py-3">
              <div className="flex flex-wrap items-center gap-1.5">
                <Badge tone="accent">{item.dimension.replace(/_/g, " ")}</Badge>
                <Badge>{item.format.replace(/_/g, " ")}</Badge>
                <span className="text-2xs text-ink-faint">max {item.max_score}</span>
                {item.misconception_detected ? <Badge tone="warn">misconception</Badge> : null}
              </div>
              <p className="mt-1.5 text-xs font-medium">{item.prompt}</p>

              {isObjective ? (
                <p className="mt-1.5 text-xs">
                  Selected option {item.selected_option_index}.{" "}
                  <span
                    className={
                      item.auto_score && item.auto_score > 0 ? "text-accent" : "text-danger"
                    }
                  >
                    Auto-scored {item.auto_score ?? 0}/{item.max_score}
                  </span>
                </p>
              ) : (
                <>
                  <blockquote className="mt-1.5 rounded-md border-l-2 border-line-strong bg-canvas px-3 py-2 text-xs italic leading-relaxed">
                    {item.text_answer || "(blank)"}
                  </blockquote>

                  {item.ai_suggested_score !== null ? (
                    <div className="mt-2 rounded-md border border-warn/25 bg-warn-soft px-3 py-2">
                      <p className="text-2xs font-semibold text-warn">
                        AI suggestion: {item.ai_suggested_score}/{item.max_score} — not counted
                        until you confirm it
                      </p>
                      <p className="mt-1 text-2xs leading-relaxed text-warn/90">
                        {item.ai_rationale}
                      </p>
                    </div>
                  ) : null}

                  <div className="mt-2 flex flex-wrap items-end gap-2">
                    <Field label="Human score" className="w-28">
                      <Input
                        type="number"
                        min={0}
                        max={item.max_score}
                        step="0.5"
                        value={draft.score}
                        onChange={(e) =>
                          setDrafts((prev) => ({
                            ...prev,
                            [item.item_response_id]: { ...draft, score: e.target.value },
                          }))
                        }
                      />
                    </Field>
                    <Field label="Grader notes" className="min-w-[14rem] flex-1">
                      <Input
                        value={draft.notes}
                        onChange={(e) =>
                          setDrafts((prev) => ({
                            ...prev,
                            [item.item_response_id]: { ...draft, notes: e.target.value },
                          }))
                        }
                        placeholder="Why this score?"
                      />
                    </Field>
                    <label className="flex items-center gap-1.5 pb-1.5 text-2xs">
                      <input
                        type="checkbox"
                        checked={draft.misconception}
                        onChange={(e) =>
                          setDrafts((prev) => ({
                            ...prev,
                            [item.item_response_id]: { ...draft, misconception: e.target.checked },
                          }))
                        }
                        className="h-3.5 w-3.5"
                      />
                      misconception
                    </label>
                    <Button
                      size="sm"
                      variant="primary"
                      disabled={draft.score === ""}
                      loading={grade.isPending}
                      onClick={() =>
                        grade.mutate({
                          itemResponseId: item.item_response_id,
                          score: Number(draft.score),
                          notes: draft.notes,
                          misconception: draft.misconception,
                        })
                      }
                    >
                      Save grade
                    </Button>
                    {item.human_score !== null ? (
                      <Badge tone="success">graded {item.human_score}</Badge>
                    ) : null}
                  </div>
                </>
              )}
            </div>
          );
        })}
      </div>
      {grade.error ? (
        <div className="px-4 py-3">
          <ErrorState error={grade.error} />
        </div>
      ) : null}
    </Card>
  );
}
