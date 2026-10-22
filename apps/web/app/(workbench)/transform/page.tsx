"use client";

/**
 * Transformation workbench.
 *
 * Shows the pipeline doing its work rather than just its output: per-treatment
 * before/after with a measured change summary, the fidelity audit, and the
 * cost of every stage. A researcher should be able to see *which* treatment
 * produced a given change, which is the whole point of applying them
 * one at a time.
 */

import { useMutation, useQuery } from "@tanstack/react-query";
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
  Field,
  KeyValue,
  Loading,
  Mono,
  PageHeader,
  Section,
  Select,
  SyntheticBadge,
  Table,
  Tabs,
  Td,
  Tr,
  formatMs,
  formatUsd,
} from "@/components/ui";
import { Markdown, UnifiedDiff } from "@/lib/markdown";
import { ResponseDetail, TransformResult, api } from "@/lib/api";
import {
  groupModels,
  modelKey,
  parseModelKey,
  useModels,
  useQuestions,
  useResponses,
  useStrategies,
} from "@/lib/hooks";

export default function TransformPage() {
  const searchParams = useSearchParams();
  const initialResponse = searchParams.get("response") ?? "";

  const questions = useQuestions();
  const models = useModels();
  const strategies = useStrategies();

  const [questionId, setQuestionId] = React.useState("");
  const [responseId, setResponseId] = React.useState(initialResponse);
  const [treatments, setTreatments] = React.useState<string[]>(["T1"]);
  const [transformKey, setTransformKey] = React.useState("");
  const [runAnalysis, setRunAnalysis] = React.useState(true);
  const [runPlanning, setRunPlanning] = React.useState(true);
  const [runFidelity, setRunFidelity] = React.useState(true);
  const [saveVariant, setSaveVariant] = React.useState(true);
  const [effort, setEffort] = React.useState("");
  const [result, setResult] = React.useState<TransformResult | null>(null);
  const [tab, setTab] = React.useState("output");

  const responses = useResponses({ questionId: questionId || undefined, enabled: !!questionId });

  React.useEffect(() => {
    if (!questionId && questions.data?.length && !initialResponse) {
      setQuestionId(questions.data[0].id);
    }
  }, [questions.data, questionId, initialResponse]);

  const detail = useQuery({
    queryKey: ["response", responseId],
    queryFn: () => api.get<ResponseDetail>(`responses/${responseId}`),
    enabled: !!responseId,
  });

  const transform = useMutation({
    mutationFn: () => {
      const { provider, model_id } = parseModelKey(transformKey);
      const settings: Record<string, unknown> = { max_output_tokens: 6000 };
      if (effort) settings.effort = effort;
      return api.post<TransformResult>(`responses/${responseId}/transform`, {
        treatments,
        provider,
        model_id,
        settings,
        run_analysis: runAnalysis,
        run_planning: runPlanning,
        run_fidelity: runFidelity,
        save_variant: saveVariant,
      });
    },
    onSuccess: (data) => {
      setResult(data);
      setTab("output");
    },
  });

  const grouped = groupModels(models.data);
  const source = detail.data?.response;
  const sourceModel = source ? `${source.provider}/${source.model_id}` : "";
  const transformModel = transformKey ? parseModelKey(transformKey).model_id : "";
  const crossModel = Boolean(transformModel && source && transformModel !== source.model_id);

  return (
    <>
      <PageHeader
        eyebrow="Transformation workbench"
        title="Apply treatments and inspect what changed"
        description="Treatments run one at a time so each change is attributable. Every variant is checked for factual drift before you use it as a stimulus."
      />

      <div className="grid gap-5 xl:grid-cols-[380px_minmax(0,1fr)]">
        <div className="space-y-5 xl:sticky xl:top-20 xl:self-start">
          <Card>
            <CardHeader title="1 · Source answer" />
            <div className="space-y-4 px-4 py-3">
              <Field label="Research question">
                <Select
                  value={questionId}
                  onChange={(e) => {
                    setQuestionId(e.target.value);
                    setResponseId("");
                    setResult(null);
                  }}
                >
                  <option value="">Select…</option>
                  {(questions.data ?? []).map((q) => (
                    <option key={q.id} value={q.id}>
                      {q.text}
                    </option>
                  ))}
                </Select>
              </Field>
              <Field label="Answer to transform">
                <Select
                  value={responseId}
                  onChange={(e) => {
                    setResponseId(e.target.value);
                    setResult(null);
                  }}
                >
                  <option value="">Select…</option>
                  {(responses.data ?? []).map((r) => (
                    <option key={r.id} value={r.id}>
                      {r.model_id}
                      {r.applied_treatments.length ? ` [${r.applied_treatments.join("+")}]` : ""}
                      {r.is_synthetic ? " (synthetic)" : ""}
                    </option>
                  ))}
                </Select>
              </Field>
              {source ? (
                <KeyValue
                  columns={1}
                  items={[
                    { label: "Source model", value: <Mono>{sourceModel}</Mono> },
                    { label: "Kind", value: source.kind },
                    { label: "Origin", value: source.origin },
                  ]}
                />
              ) : null}
            </div>
          </Card>

          <Card>
            <CardHeader
              title="2 · Treatments"
              description="Each treatment is bounded; hover for what it must not do"
            />
            <div className="space-y-2 px-4 py-3">
              {(strategies.data ?? []).map((strategy) => (
                <Checkbox
                  key={strategy.key}
                  checked={treatments.includes(strategy.key)}
                  onChange={(checked) =>
                    setTreatments((prev) =>
                      checked ? [...prev, strategy.key] : prev.filter((k) => k !== strategy.key),
                    )
                  }
                  label={
                    <span title={strategy.boundary_note}>
                      <span className="font-medium">{strategy.key}</span> — {strategy.name}
                    </span>
                  }
                  description={strategy.description}
                />
              ))}
            </div>
            {treatments.length > 1 ? (
              <div className="border-t border-line px-4 py-3">
                <Caveat>
                  Applied in the canonical order T3 → T4 → T6 → T1 → T2 → T5, so content-adding
                  treatments run before presentation ones. The order used is recorded on the
                  variant.
                </Caveat>
              </div>
            ) : null}
          </Card>

          <Card>
            <CardHeader
              title="3 · Transformation model"
              description="Chosen separately from the source model"
            />
            <div className="space-y-4 px-4 py-3">
              <Field
                label="Model"
                hint="Using a different model from the source makes this a cross-model transformation (Experiment 4)."
              >
                <Select value={transformKey} onChange={(e) => setTransformKey(e.target.value)}>
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
              {crossModel ? (
                <Caveat tone="accent">
                  Cross-model: <Mono>{source?.model_id}</Mono> generated, <Mono>{transformModel}</Mono>{" "}
                  transforms. Any improvement could come from the methodology, the transforming
                  model, or their interaction — run the full grid in the studio to tell them apart.
                </Caveat>
              ) : null}
              <Field label="Effort">
                <Select value={effort} onChange={(e) => setEffort(e.target.value)}>
                  <option value="">Provider default</option>
                  {["low", "medium", "high", "xhigh", "max"].map((level) => (
                    <option key={level} value={level}>
                      {level}
                    </option>
                  ))}
                </Select>
              </Field>
              <div className="space-y-2">
                <Checkbox checked={runAnalysis} onChange={setRunAnalysis} label="Stage A — analysis" />
                <Checkbox checked={runPlanning} onChange={setRunPlanning} label="Stage B — planning" />
                <Checkbox
                  checked={runFidelity}
                  onChange={setRunFidelity}
                  label="Stage D — LLM fidelity review"
                  description="Deterministic checks run regardless."
                />
                <Checkbox
                  checked={saveVariant}
                  onChange={setSaveVariant}
                  label="Save as a variant"
                  description="Required if you want to use it in a human study."
                />
              </div>
              <Button
                variant="primary"
                className="w-full"
                disabled={!responseId || !transformKey || treatments.length === 0}
                loading={transform.isPending}
                onClick={() => transform.mutate()}
              >
                Run transformation
              </Button>
              <p className="text-2xs leading-relaxed text-ink-faint">
                Calls:{" "}
                {(runAnalysis ? 1 : 0) +
                  (runPlanning ? 1 : 0) +
                  treatments.length +
                  (runFidelity ? 1 : 0)}{" "}
                model request(s).
              </p>
              {transform.error ? <ErrorState error={transform.error} /> : null}
            </div>
          </Card>
        </div>

        <div className="space-y-5">
          {!source ? (
            <EmptyState title="Select a source answer">
              Pick a question and one of its stored answers on the left.
            </EmptyState>
          ) : (
            <>
              {!result ? (
                <Card>
                  <CardHeader
                    title="Source answer"
                    description={
                      <span className="flex flex-wrap items-center gap-1.5">
                        <Mono>{sourceModel}</Mono>
                        {source.is_synthetic ? <SyntheticBadge /> : null}
                      </span>
                    }
                  />
                  <div className="px-5 py-4">
                    <Markdown source={source.text} variant="compact" />
                  </div>
                </Card>
              ) : (
                <>
                  {result.is_synthetic ? (
                    <Caveat tone="synthetic">
                      This transformation operated on synthetic fixture text, so the variant is
                      synthetic too. The pipeline really ran; the content carries no evidential
                      value.
                    </Caveat>
                  ) : null}

                  <Card>
                    <CardHeader
                      title="Result"
                      description={
                        <span className="flex flex-wrap items-center gap-x-3 gap-y-1">
                          <span>
                            Treatments applied in order: {result.treatment_order.join(" → ")}
                          </span>
                          <span>·</span>
                          <span>{formatUsd(result.total_cost_usd)}</span>
                          {result.variant_response_id ? (
                            <>
                              <span>·</span>
                              <Mono>saved as {result.variant_response_id.slice(0, 8)}</Mono>
                            </>
                          ) : (
                            <Badge tone="warn">not saved</Badge>
                          )}
                        </span>
                      }
                      actions={
                        result.variant_response_id ? (
                          <Link href={`/studies?response=${result.variant_response_id}`}>
                            <Button size="sm" variant="primary">
                              Use in a human study
                            </Button>
                          </Link>
                        ) : null
                      }
                    />
                    <div className="px-4 pt-3">
                      <Tabs
                        tabs={[
                          { id: "output", label: "Side by side" },
                          { id: "changes", label: "Per-treatment changes", count: result.changes.length },
                          {
                            id: "fidelity",
                            label: "Fidelity audit",
                            count: result.fidelity?.warnings.length ?? 0,
                          },
                          { id: "stages", label: "Pipeline stages", count: result.stages.length },
                        ]}
                        active={tab}
                        onChange={setTab}
                      />
                    </div>

                    {tab === "output" ? (
                      <div className="grid gap-0 lg:grid-cols-2">
                        <div className="border-b border-line px-5 py-4 lg:border-b-0 lg:border-r">
                          <p className="mb-2 text-2xs font-semibold uppercase tracking-wide text-ink-faint">
                            Original — {source.model_id}
                          </p>
                          <Markdown source={source.text} variant="compact" />
                        </div>
                        <div className="bg-accent-soft/30 px-5 py-4">
                          <p className="mb-2 text-2xs font-semibold uppercase tracking-wide text-accent-strong">
                            Transformed — {result.applied_treatments.join(" + ")}
                          </p>
                          <Markdown source={result.text} variant="compact" />
                        </div>
                      </div>
                    ) : null}

                    {tab === "changes" ? (
                      <div className="space-y-4 px-4 py-4">
                        {result.changes.map((change, index) => (
                          <Card key={change.treatment} className="bg-canvas">
                            <CardHeader
                              title={
                                <span className="flex items-center gap-2">
                                  <Badge tone="accent">{change.treatment}</Badge>
                                  {change.name}
                                </span>
                              }
                              description={`Step ${index + 1} of ${result.changes.length}`}
                            />
                            <div className="px-4 py-3">
                              <KeyValue
                                columns={3}
                                items={[
                                  {
                                    label: "Words",
                                    value: `${change.stats.words_before} → ${change.stats.words_after} (${
                                      change.stats.word_delta >= 0 ? "+" : ""
                                    }${change.stats.word_delta})`,
                                  },
                                  {
                                    label: "Sentences",
                                    value: `${change.stats.sentences_before} → ${change.stats.sentences_after}`,
                                  },
                                  {
                                    label: "Avg sentence words",
                                    value: `${change.stats.avg_sentence_words_before} → ${change.stats.avg_sentence_words_after}`,
                                  },
                                  { label: "Headings added", value: change.stats.headings_added },
                                  { label: "List items added", value: change.stats.list_items_added },
                                  {
                                    label: "Word overlap with input",
                                    value: `${Math.round(change.stats.word_similarity * 100)}%`,
                                    hint: "Low overlap on a presentation-only treatment suggests the prose was rewritten too.",
                                  },
                                ]}
                              />
                              <Disclosure summary="Unified diff" className="mt-3">
                                <UnifiedDiff diff={change.unified_diff} />
                              </Disclosure>
                            </div>
                          </Card>
                        ))}
                        <Caveat>
                          These statistics are computed deterministically from the text, not
                          reported by the model. They are how you check a treatment stayed inside
                          its boundary.
                        </Caveat>
                      </div>
                    ) : null}

                    {tab === "fidelity" ? (
                      <div className="space-y-3 px-4 py-4">
                        {result.fidelity ? (
                          <>
                            <div className="flex flex-wrap items-center gap-2">
                              <Badge
                                tone={
                                  result.fidelity.verdict === "serious_concerns"
                                    ? "danger"
                                    : result.fidelity.verdict === "warnings"
                                      ? "warn"
                                      : "success"
                                }
                              >
                                {result.fidelity.verdict.replace(/_/g, " ")}
                              </Badge>
                              <span className="text-2xs text-ink-faint">
                                {result.fidelity.deterministic_warning_count ?? 0} from
                                deterministic checks ·{" "}
                                {result.fidelity.llm_warning_count ?? 0} from the LLM reviewer
                                {result.fidelity.llm_review_ran ? "" : " (LLM review skipped)"}
                              </span>
                            </div>

                            {result.fidelity.warnings.length === 0 ? (
                              <Caveat>
                                No problems detected. This means nothing was flagged — not that the
                                transformation is verified accurate.
                              </Caveat>
                            ) : (
                              <ul className="space-y-2">
                                {result.fidelity.warnings.map((warning, i) => (
                                  <li
                                    key={i}
                                    className={
                                      "rounded-md border px-3 py-2.5 " +
                                      (warning.severity === "high"
                                        ? "border-danger/30 bg-danger-soft"
                                        : warning.severity === "medium"
                                          ? "border-warn/30 bg-warn-soft"
                                          : "border-line bg-canvas")
                                    }
                                  >
                                    <div className="flex flex-wrap items-center gap-1.5">
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
                                      <Badge>{warning.severity}</Badge>
                                      {warning.detector ? (
                                        <Badge
                                          title={
                                            warning.detector === "deterministic"
                                              ? "Found by a reproducible rule you can verify by hand."
                                              : "Reported by the LLM reviewer."
                                          }
                                        >
                                          {warning.detector}
                                        </Badge>
                                      ) : null}
                                    </div>
                                    <p className="mt-1.5 text-xs leading-relaxed">{warning.detail}</p>
                                    {warning.source_excerpt ? (
                                      <p className="mt-1 text-2xs italic text-ink-muted">
                                        Source: &ldquo;{warning.source_excerpt}&rdquo;
                                      </p>
                                    ) : null}
                                    {warning.transformed_excerpt ? (
                                      <p className="mt-0.5 text-2xs italic text-ink-muted">
                                        Transformed: &ldquo;{warning.transformed_excerpt}&rdquo;
                                      </p>
                                    ) : null}
                                  </li>
                                ))}
                              </ul>
                            )}

                            <Caveat tone="warn">
                              Provisional assessment. Deterministic checks (numeric drift, hedge
                              loss, length loss, treatment-boundary violations) can escalate the
                              verdict but never soften it — a model saying &ldquo;clean&rdquo; does
                              not clear a changed number.
                            </Caveat>
                          </>
                        ) : (
                          <Caveat tone="warn">Fidelity verification was not run.</Caveat>
                        )}
                      </div>
                    ) : null}

                    {tab === "stages" ? (
                      <div className="px-4 py-4">
                        <Table head={["Stage", "What it did", "Model", "Tokens", "Latency", "Cost"]}>
                          {result.stages.map((stage, i) => (
                            <Tr key={i}>
                              <Td>
                                <Badge tone="accent">{stage.stage}</Badge>
                              </Td>
                              <Td className="text-xs">{stage.label}</Td>
                              <Td className="font-mono text-2xs">{stage.model_id}</Td>
                              <Td className="whitespace-nowrap text-2xs tabular-nums">
                                {stage.input_tokens ?? "—"} in / {stage.output_tokens ?? "—"} out
                              </Td>
                              <Td className="text-2xs tabular-nums">{formatMs(stage.latency_ms)}</Td>
                              <Td className="text-2xs tabular-nums">
                                {stage.served_from_cache ? (
                                  <Badge>cached</Badge>
                                ) : (
                                  formatUsd(stage.cost_usd)
                                )}
                              </Td>
                            </Tr>
                          ))}
                        </Table>
                        <Caveat className="mt-3">
                          Running treatments individually costs more than one combined prompt. That
                          is the price of attribution: it is the only way to know which treatment
                          produced which change.
                        </Caveat>
                        {result.control_limitations.length > 0 ? (
                          <Disclosure
                            summary={`Control limitations (${result.control_limitations.length})`}
                            className="mt-3"
                          >
                            <ul className="space-y-1.5 text-2xs text-ink-muted">
                              {result.control_limitations.map((limitation, i) => (
                                <li key={i}>▲ {limitation}</li>
                              ))}
                            </ul>
                          </Disclosure>
                        ) : null}
                      </div>
                    ) : null}
                  </Card>

                  {result.plan ? (
                    <Card>
                      <CardHeader
                        title="Stage B — what the pipeline decided this explanation needed"
                        description="A plan that declines a technique is a valid plan"
                      />
                      <div className="px-4 py-3">
                        <KeyValue
                          columns={3}
                          items={[
                            { label: "Learner level", value: String(result.plan.learner_level) },
                            { label: "Detail level", value: String(result.plan.detail_level) },
                            {
                              label: "Example needed",
                              value: result.plan.needs_concrete_example ? "yes" : "no",
                            },
                            { label: "Analogy needed", value: result.plan.needs_analogy ? "yes" : "no" },
                            { label: "Diagram needed", value: result.plan.needs_diagram ? "yes" : "no" },
                          ]}
                        />
                      </div>
                    </Card>
                  ) : null}
                </>
              )}
            </>
          )}
        </div>
      </div>
    </>
  );
}
