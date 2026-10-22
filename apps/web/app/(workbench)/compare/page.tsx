"use client";

/**
 * Answer comparison workspace.
 *
 * Three rendering modes because they answer different questions: rendered
 * markdown for normal reading, raw text for seeing exactly what the model
 * emitted, and a distraction-free reading mode for judging readability without
 * the surrounding chrome influencing the judgement.
 */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import React from "react";

import {
  Badge,
  Button,
  Caveat,
  Card,
  CardHeader,
  Checkbox,
  Disclosure,
  EmptyState,
  ErrorState,
  EvidenceLabel,
  Field,
  Input,
  KeyValue,
  Loading,
  Mono,
  PageHeader,
  Select,
  SyntheticBadge,
  Table,
  Td,
  Textarea,
  Tr,
  formatInt,
  formatMs,
  formatUsd,
} from "@/components/ui";
import { Markdown } from "@/lib/markdown";
import { ResponseDetail, ResponseRow, api } from "@/lib/api";
import { groupModels, modelKey, parseModelKey, useModels, useQuestions, useResponses } from "@/lib/hooks";

type ViewMode = "rendered" | "raw" | "reading";

export default function ComparePage() {
  const searchParams = useSearchParams();
  const questions = useQuestions();
  const [questionId, setQuestionId] = React.useState<string>("");
  const [selected, setSelected] = React.useState<string[]>([]);
  const [mode, setMode] = React.useState<ViewMode>("rendered");
  const [showDiagnostics, setShowDiagnostics] = React.useState(true);
  const [importOpen, setImportOpen] = React.useState(false);

  React.useEffect(() => {
    if (!questionId && questions.data?.length) setQuestionId(questions.data[0].id);
  }, [questions.data, questionId]);

  const responses = useResponses({ questionId: questionId || undefined, enabled: !!questionId });

  React.useEffect(() => {
    // Default to the two most recent variants for the chosen question.
    if (responses.data && responses.data.length && selected.length === 0) {
      setSelected(responses.data.slice(0, 2).map((r) => r.id));
    }
  }, [responses.data, selected.length]);

  React.useEffect(() => {
    setSelected([]);
  }, [questionId]);

  if (questions.isLoading) return <Loading label="Loading questions" />;

  const question = questions.data?.find((q) => q.id === questionId);

  return (
    <>
      <PageHeader
        eyebrow="Comparison workspace"
        title="Read answers side by side"
        description="Explanations for one question, rendered identically so presentation differences do not masquerade as content differences."
        actions={
          <>
            <Button onClick={() => setImportOpen((open) => !open)}>
              {importOpen ? "Close import" : "Import a web-chat answer"}
            </Button>
            <Link href="/transform">
              <Button variant="primary">Transformation workbench</Button>
            </Link>
          </>
        }
      />

      <Card className="mb-5">
        <div className="flex flex-wrap items-end gap-4 px-4 py-3">
          <Field label="Research question" className="min-w-[22rem] flex-1">
            <Select value={questionId} onChange={(e) => setQuestionId(e.target.value)}>
              {(questions.data ?? []).map((q) => (
                <option key={q.id} value={q.id}>
                  {q.text}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="Rendering">
            <Select value={mode} onChange={(e) => setMode(e.target.value as ViewMode)}>
              <option value="rendered">Rendered (normalised)</option>
              <option value="raw">Raw model output</option>
              <option value="reading">Distraction-free reading</option>
            </Select>
          </Field>
          <Checkbox
            checked={showDiagnostics}
            onChange={setShowDiagnostics}
            label="Show diagnostics"
          />
        </div>
        {question && question.factual_checklist.length > 0 ? (
          <div className="border-t border-line px-4 py-3">
            <Disclosure summary={`Reviewed factual checklist (${question.factual_checklist.length} claims)`}>
              <ul className="space-y-1 text-xs text-ink-muted">
                {question.factual_checklist.map((claim, i) => (
                  <li key={i} className="flex gap-2">
                    <span className="text-ink-faint">{i + 1}.</span>
                    <span>{claim}</span>
                  </li>
                ))}
              </ul>
              <p className="mt-2 text-2xs text-ink-faint">
                Reviewed by: {question.checklist_reviewed_by ?? "not recorded"}. Coverage below is
                lexical keyword overlap, so a correct paraphrase can register as a miss.
              </p>
            </Disclosure>
          </div>
        ) : null}
      </Card>

      {importOpen ? (
        <ManualImport
          questionId={questionId}
          onDone={() => {
            setImportOpen(false);
            responses.refetch();
          }}
        />
      ) : null}

      {responses.isLoading ? (
        <Loading label="Loading responses" />
      ) : responses.error ? (
        <ErrorState error={responses.error} retry={responses.refetch} />
      ) : (responses.data ?? []).length === 0 ? (
        <EmptyState
          title="No stored answers for this question"
          action={
            <Link href="/studio">
              <Button variant="primary">Run an experiment</Button>
            </Link>
          }
        >
          Run a baseline experiment to generate answers, or import a real answer pasted from a
          ChatGPT or Claude web chat.
        </EmptyState>
      ) : (
        <>
          <Card className="mb-5">
            <CardHeader
              title="Select variants to compare"
              description={`${selected.length} selected · ${(responses.data ?? []).length} available`}
            />
            <div className="max-h-56 overflow-y-auto px-4 py-3">
              <div className="space-y-1.5">
                {(responses.data ?? []).map((response) => (
                  <Checkbox
                    key={response.id}
                    checked={selected.includes(response.id)}
                    onChange={(checked) =>
                      setSelected((prev) =>
                        checked ? [...prev, response.id] : prev.filter((id) => id !== response.id),
                      )
                    }
                    label={
                      <span className="flex flex-wrap items-center gap-1.5">
                        <span className="font-mono text-xs">{response.model_id}</span>
                        <Badge>{response.kind}</Badge>
                        {response.applied_treatments.map((t) => (
                          <Badge key={t} tone="accent">
                            {t}
                          </Badge>
                        ))}
                        {response.origin === "manual_import" ? (
                          <Badge tone="warn">imported</Badge>
                        ) : null}
                        {response.is_synthetic ? <SyntheticBadge /> : null}
                      </span>
                    }
                    description={`${response.label || "(no label)"} · ${new Date(
                      response.created_at,
                    ).toLocaleString()}`}
                  />
                ))}
              </div>
            </div>
          </Card>

          {selected.length === 0 ? (
            <EmptyState title="Select at least one variant above" />
          ) : (
            <div
              className={
                "grid gap-5 " +
                (selected.length === 1
                  ? "grid-cols-1"
                  : selected.length === 2
                    ? "grid-cols-1 xl:grid-cols-2"
                    : "grid-cols-1 xl:grid-cols-2 2xl:grid-cols-3")
              }
            >
              {selected.map((responseId) => (
                <ResponsePanel
                  key={responseId}
                  responseId={responseId}
                  mode={mode}
                  showDiagnostics={showDiagnostics}
                />
              ))}
            </div>
          )}
        </>
      )}
    </>
  );
}

function ResponsePanel({
  responseId,
  mode,
  showDiagnostics,
}: {
  responseId: string;
  mode: ViewMode;
  showDiagnostics: boolean;
}) {
  const queryClient = useQueryClient();
  const models = useModels();
  const [judgeKey, setJudgeKey] = React.useState("");
  const [annotation, setAnnotation] = React.useState("");

  const detail = useQuery({
    queryKey: ["response", responseId],
    queryFn: () => api.get<ResponseDetail>(`responses/${responseId}`),
  });

  const judge = useMutation({
    mutationFn: () => {
      const { provider, model_id } = parseModelKey(judgeKey);
      return api.post(`responses/${responseId}/judge-now`, { provider, model_id });
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["response", responseId] }),
  });

  const annotate = useMutation({
    mutationFn: () =>
      api.post(`responses/${responseId}/annotations`, { label: "note", body: annotation }),
    onSuccess: () => {
      setAnnotation("");
      queryClient.invalidateQueries({ queryKey: ["response", responseId] });
    },
  });

  if (detail.isLoading) return <Card className="p-4"><Loading /></Card>;
  if (detail.error) return <Card className="p-4"><ErrorState error={detail.error} /></Card>;

  const data = detail.data!;
  const response = data.response;
  const metrics = data.automated_diagnostics.metrics;
  const grouped = groupModels(models.data);

  return (
    <Card className="flex flex-col">
      <CardHeader
        title={
          <span className="flex flex-wrap items-center gap-1.5">
            <span className="font-mono text-xs">{response.model_id}</span>
            <Badge>{response.kind}</Badge>
            {response.applied_treatments.map((t) => (
              <Badge key={t} tone="accent">
                {t}
              </Badge>
            ))}
            {response.is_synthetic ? <SyntheticBadge /> : null}
          </span>
        }
        description={
          <span className="flex flex-wrap gap-x-3 gap-y-0.5">
            <span>{response.provider}</span>
            <span>·</span>
            <span>{formatInt(response.output_tokens)} output tokens</span>
            <span>·</span>
            <span>{formatMs(response.latency_ms)}</span>
            <span>·</span>
            <span>{formatUsd(response.cost_usd)}</span>
            {response.served_from_cache ? (
              <>
                <span>·</span>
                <Badge>from cache</Badge>
              </>
            ) : null}
          </span>
        }
      />

      {response.is_synthetic ? (
        <div className="px-4 pt-3">
          <Caveat tone="synthetic">
            Demo fixture, not model output. Diagnostics below describe the fixture text.
          </Caveat>
        </div>
      ) : null}

      <div className={mode === "reading" ? "bg-canvas px-6 py-6" : "px-4 py-4"}>
        {mode === "raw" ? (
          <pre className="max-h-[32rem] overflow-auto whitespace-pre-wrap break-words rounded-md border border-line bg-canvas p-3 font-mono text-2xs leading-relaxed">
            {response.text}
          </pre>
        ) : (
          <div className={mode === "reading" ? "mx-auto" : ""}>
            <Markdown source={response.text} variant={mode === "reading" ? "reading" : "compact"} />
          </div>
        )}
      </div>

      <div className="mt-auto space-y-3 border-t border-line px-4 py-3">
        {response.control_limitations.length > 0 ? (
          <Disclosure summary={`Control limitations (${response.control_limitations.length})`}>
            <ul className="space-y-1.5 text-2xs leading-relaxed text-ink-muted">
              {response.control_limitations.map((limitation, i) => (
                <li key={i} className="flex gap-1.5">
                  <span className="text-warn" aria-hidden>
                    ▲
                  </span>
                  <span>{limitation}</span>
                </li>
              ))}
            </ul>
          </Disclosure>
        ) : null}

        <Disclosure summary="Generation metadata">
          <KeyValue
            columns={2}
            items={[
              { label: "Response id", value: <Mono>{response.id.slice(0, 8)}</Mono> },
              { label: "Origin", value: response.origin },
              { label: "Finish reason", value: response.finish_reason ?? "—" },
              {
                label: "Requested settings",
                value: <Mono>{JSON.stringify(response.requested_settings)}</Mono>,
              },
              {
                label: "Effective settings",
                value: <Mono>{JSON.stringify(response.generation_settings)}</Mono>,
              },
              { label: "Created", value: new Date(response.created_at).toLocaleString() },
            ]}
          />
          {response.system_prompt_snapshot ? (
            <div className="mt-3">
              <p className="mb-1 text-2xs font-semibold uppercase tracking-wide text-ink-faint">
                Exact system prompt used
              </p>
              <pre className="max-h-48 overflow-auto whitespace-pre-wrap rounded border border-line bg-canvas p-2 font-mono text-2xs">
                {response.system_prompt_snapshot}
              </pre>
            </div>
          ) : null}
        </Disclosure>

        {showDiagnostics && metrics ? (
          <Disclosure summary="Automated diagnostics" defaultOpen>
            <div className="mb-2 flex items-center gap-2">
              <EvidenceLabel evidenceClass="automated_diagnostic" />
            </div>
            <KeyValue
              columns={2}
              items={[
                { label: "Words", value: formatInt(metrics.surface.word_count) },
                { label: "Sentences", value: formatInt(metrics.surface.sentence_count) },
                { label: "Avg sentence words", value: metrics.surface.avg_sentence_words },
                {
                  label: "Sentences > 30 words",
                  value: `${metrics.surface.long_sentence_count} (${Math.round(
                    (metrics.surface.long_sentence_share ?? 0) * 100,
                  )}%)`,
                },
                { label: "Longest paragraph", value: `${metrics.surface.max_paragraph_words} words` },
                { label: "Flesch reading ease", value: metrics.readability.flesch_reading_ease },
                { label: "Jargon candidates", value: metrics.jargon.candidate_count },
                { label: "Indirection phrases", value: metrics.jargon.indirection_phrase_count },
                { label: "Unresolved references", value: metrics.unresolved_references.count },
                { label: "Headings", value: metrics.structure.heading_count },
                {
                  label: "Causal markers / 100w",
                  value: metrics.explanation_steps.causal_density_per_100w,
                },
                {
                  label: "Repeated trigrams",
                  value: metrics.repetition.repeated_trigram_count,
                },
                {
                  label: "Checklist coverage",
                  value:
                    metrics.concept_coverage.coverage_ratio === null
                      ? "no checklist"
                      : `${metrics.concept_coverage.covered}/${metrics.concept_coverage.checklist_size}`,
                },
                {
                  label: "Terms undefined at first use",
                  value:
                    metrics.terminology_introduction.undefined_share === null
                      ? "—"
                      : `${Math.round(metrics.terminology_introduction.undefined_share * 100)}%`,
                },
              ]}
            />

            {metrics.jargon.indirection_phrases.length > 0 ? (
              <div className="mt-3">
                <p className="mb-1 text-2xs font-semibold uppercase tracking-wide text-ink-faint">
                  Indirection phrases found
                </p>
                <div className="flex flex-wrap gap-1">
                  {metrics.jargon.indirection_phrases.map((phrase) => (
                    <Badge key={phrase} tone="warn">
                      {phrase}
                    </Badge>
                  ))}
                </div>
              </div>
            ) : null}

            {metrics.unresolved_references.examples.length > 0 ? (
              <div className="mt-3">
                <p className="mb-1 text-2xs font-semibold uppercase tracking-wide text-ink-faint">
                  Possibly unresolved references
                </p>
                <ul className="space-y-1 text-2xs text-ink-muted">
                  {metrics.unresolved_references.examples.map((example, i) => (
                    <li key={i} className="italic">
                      &ldquo;{example.excerpt}&rdquo;
                    </li>
                  ))}
                </ul>
              </div>
            ) : null}

            <Caveat className="mt-3">{metrics.interpretation_warning}</Caveat>
          </Disclosure>
        ) : null}

        {data.fidelity_reports.length > 0 ? (
          <Disclosure
            summary={`Factual fidelity — ${data.fidelity_reports[0].verdict.replace(/_/g, " ")} (${
              data.fidelity_reports[0].warnings.length
            } warning${data.fidelity_reports[0].warnings.length === 1 ? "" : "s"})`}
            defaultOpen={data.fidelity_reports[0].verdict !== "clean"}
          >
            {data.fidelity_reports[0].warnings.length === 0 ? (
              <Caveat>
                No problems detected. This is not verification that the transformation is accurate.
              </Caveat>
            ) : (
              <ul className="space-y-2">
                {data.fidelity_reports[0].warnings.map((warning, i) => (
                  <li key={i} className="rounded border border-line bg-canvas px-2.5 py-2">
                    <span className="flex flex-wrap items-center gap-1.5">
                      <Badge
                        tone={
                          warning.severity === "high"
                            ? "danger"
                            : warning.severity === "medium"
                              ? "warn"
                              : "neutral"
                        }
                      >
                        {warning.type.replace(/_/g, " ")}
                      </Badge>
                      {warning.detector ? <Badge>{warning.detector}</Badge> : null}
                    </span>
                    <p className="mt-1 text-2xs leading-relaxed text-ink-muted">{warning.detail}</p>
                  </li>
                ))}
              </ul>
            )}
            <Caveat tone="warn" className="mt-2">
              Provisional assessment, partly produced by an LLM. Not proof of correctness.
            </Caveat>
          </Disclosure>
        ) : null}

        {data.ai_judge_evaluations.length > 0 ? (
          <Disclosure summary={`AI judge opinions (${data.ai_judge_evaluations.length})`}>
            <div className="mb-2">
              <EvidenceLabel evidenceClass="ai_judge_opinion" />
            </div>
            {data.ai_judge_evaluations.map((evaluation) => (
              <div key={evaluation.id} className="mb-3 last:mb-0">
                <p className="mb-1.5 text-2xs text-ink-faint">
                  <Mono>{`${evaluation.provider}/${evaluation.model_id}`}</Mono> · {evaluation.rubric}{" "}
                  · {evaluation.blinded ? "blinded" : "not blinded"}
                </p>
                <Table head={["Dimension", "Score", "Evidence"]} className="border-0">
                  {evaluation.scores.map((score) => (
                    <Tr key={score.metric}>
                      <Td className="text-2xs">{score.metric.replace(/_/g, " ")}</Td>
                      <Td className="text-2xs tabular-nums">
                        {score.score}/5
                        <span className="ml-1 text-ink-faint">({score.confidence})</span>
                      </Td>
                      <Td className="max-w-[16rem] text-2xs italic text-ink-muted">
                        {score.evidence || "—"}
                      </Td>
                    </Tr>
                  ))}
                </Table>
              </div>
            ))}
          </Disclosure>
        ) : null}

        <div className="flex flex-wrap items-end gap-2">
          <Field label="Judge model" className="min-w-[12rem] flex-1">
            <Select value={judgeKey} onChange={(e) => setJudgeKey(e.target.value)}>
              <option value="">Select a judge…</option>
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
            size="sm"
            disabled={!judgeKey}
            loading={judge.isPending}
            onClick={() => judge.mutate()}
          >
            Run blinded judge
          </Button>
        </div>
        {judge.error ? <ErrorState error={judge.error} /> : null}

        <Disclosure summary={`Annotations (${data.annotations.length})`}>
          {data.annotations.length > 0 ? (
            <ul className="mb-3 space-y-2">
              {data.annotations.map((note) => (
                <li key={note.id} className="rounded border border-line bg-canvas px-2.5 py-2">
                  <p className="text-2xs text-ink-faint">
                    {note.author} · {new Date(note.created_at).toLocaleString()}
                    {note.label ? ` · ${note.label}` : ""}
                  </p>
                  <p className="mt-0.5 text-xs">{note.body}</p>
                </li>
              ))}
            </ul>
          ) : null}
          <Textarea
            rows={2}
            value={annotation}
            onChange={(e) => setAnnotation(e.target.value)}
            placeholder="Note an explanation characteristic: dense paragraph, undefined term, missing step…"
          />
          <Button
            size="sm"
            className="mt-2"
            disabled={!annotation.trim()}
            loading={annotate.isPending}
            onClick={() => annotate.mutate()}
          >
            Add annotation
          </Button>
        </Disclosure>

        <div className="flex flex-wrap gap-2 pt-1">
          <Link href={`/transform?response=${response.id}`}>
            <Button size="sm">Transform this answer</Button>
          </Link>
          <Link href={`/analysis?response=${response.id}`}>
            <Button size="sm">Analyse concepts</Button>
          </Link>
        </div>
      </div>
    </Card>
  );
}

function ManualImport({ questionId, onDone }: { questionId: string; onDone: () => void }) {
  const models = useModels();
  const [provider, setProvider] = React.useState("anthropic");
  const [modelId, setModelId] = React.useState("");
  const [label, setLabel] = React.useState("");
  const [text, setText] = React.useState("");
  const [notes, setNotes] = React.useState("");

  const importMutation = useMutation({
    mutationFn: () =>
      api.post<ResponseRow>("responses/import", {
        question_id: questionId,
        provider,
        model_id: modelId,
        label,
        text,
        interface: "web_chat",
        captured_at: new Date().toISOString(),
        notes,
      }),
    onSuccess: onDone,
  });

  return (
    <Card className="mb-5">
      <CardHeader
        title="Import a real answer from a consumer chat interface"
        description="API output and the ChatGPT / Claude web apps are not the same system. Imported answers are recorded with distinct provenance and are never treated as API-comparable."
      />
      <div className="grid gap-4 px-4 py-3 sm:grid-cols-2">
        <Field label="Provider">
          <Select value={provider} onChange={(e) => setProvider(e.target.value)}>
            <option value="anthropic">anthropic</option>
            <option value="openai">openai</option>
            <option value="gemini">gemini</option>
            <option value="manual">manual / other</option>
          </Select>
        </Field>
        <Field
          label="Model as labelled in the interface"
          hint="Record what the product called it, even if it is not an API model id."
        >
          <Input
            value={modelId}
            onChange={(e) => setModelId(e.target.value)}
            placeholder="e.g. Claude Opus 5.5 (web)"
            list="known-models"
          />
          <datalist id="known-models">
            {(models.data ?? []).map((m) => (
              <option key={m.id} value={m.model_id} />
            ))}
          </datalist>
        </Field>
        <Field label="Pasted answer" className="sm:col-span-2">
          <Textarea
            rows={10}
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="Paste the full response here."
          />
        </Field>
        <Field label="Answer label" className="sm:col-span-2" hint="Identifies this answer in study results; participants will not see it.">
          <Input
            value={label}
            onChange={(e) => setLabel(e.target.value)}
            placeholder="e.g. Claude web — original"
          />
        </Field>
        <Field label="Capture notes" className="sm:col-span-2" hint="Anything about how it was obtained.">
          <Input
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            placeholder="New chat, no custom instructions, default settings."
          />
        </Field>
      </div>
      <div className="flex items-center gap-3 border-t border-line px-4 py-3">
        <Button
          variant="primary"
          disabled={!questionId || !modelId.trim() || text.trim().length < 20}
          loading={importMutation.isPending}
          onClick={() => importMutation.mutate()}
        >
          Import answer
        </Button>
        {importMutation.error ? <ErrorState error={importMutation.error} /> : null}
      </div>
    </Card>
  );
}
