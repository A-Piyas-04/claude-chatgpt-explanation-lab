"use client";

/**
 * Experiment detail: lifecycle, per-run progress and errors, condition
 * results, exports and the generated report.
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
  EvidenceLabel,
  KeyValue,
  Loading,
  Mono,
  PageHeader,
  ProgressBar,
  Section,
  StatValue,
  StatusDot,
  SyntheticBadge,
  Table,
  Tabs,
  Td,
  Textarea,
  Tr,
  formatInt,
  formatMs,
  formatUsd,
} from "@/components/ui";
import {
  ConditionSummaryTable,
  DiagnosticsComparison,
} from "@/components/results";
import { Markdown } from "@/lib/markdown";
import { Experiment, ExperimentSummary, Job, api } from "@/lib/api";

interface ExperimentDetail {
  experiment: Experiment;
  conditions: {
    id: string;
    label: string;
    order_index: number;
    provider: string;
    model_id: string;
    prompt_version_id: string | null;
    learner_profile_id: string | null;
    generation_settings: Record<string, unknown>;
    treatments: string[];
    transform_provider: string | null;
    transform_model_id: string | null;
    transform_settings: Record<string, unknown>;
  }[];
  questions: { id: string; text: string; domain: string; conceptual_difficulty: string }[];
  runs: {
    id: string;
    condition_id: string;
    question_id: string;
    replicate_index: number;
    status: string;
    attempts: number;
    error: string | null;
    error_type: string | null;
    started_at: string | null;
    finished_at: string | null;
  }[];
  run_counts: Record<string, number>;
  jobs: Job[];
}

const LIFECYCLE = ["draft", "configured", "running", "completed", "evaluated", "reported"];

export default function ExperimentDetailPage() {
  const params = useParams<{ id: string }>();
  const id = params.id;
  const queryClient = useQueryClient();
  const [tab, setTab] = React.useState("progress");
  const [notes, setNotes] = React.useState<string | null>(null);
  const [report, setReport] = React.useState<string | null>(null);

  const detail = useQuery({
    queryKey: ["experiment", id],
    queryFn: () => api.get<ExperimentDetail>(`experiments/${id}`),
    // Poll while anything is still in flight.
    refetchInterval: (query) => {
      const data = query.state.data as ExperimentDetail | undefined;
      if (!data) return false;
      const active = data.jobs.some((j) => j.status === "running" || j.status === "queued");
      const pending = (data.run_counts.pending ?? 0) + (data.run_counts.running ?? 0) > 0;
      return active || pending ? 2000 : false;
    },
  });

  const summary = useQuery({
    queryKey: ["experiment-summary", id],
    queryFn: () => api.get<ExperimentSummary>(`analytics/experiments/${id}`),
    enabled: !!detail.data && (detail.data.run_counts.succeeded ?? 0) > 0,
  });

  const retry = useMutation({
    mutationFn: () =>
      api.post(`experiments/${id}/run`, { confirm_cost: true, retry_failed_only: true }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["experiment", id] }),
  });

  const saveNotes = useMutation({
    mutationFn: (value: string) => api.patch(`experiments/${id}/notes`, { researcher_notes: value }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["experiment", id] }),
  });

  const makeReport = useMutation({
    mutationFn: () =>
      api.post<{ body_markdown: string; contains_synthetic_data: boolean }>(
        `experiments/${id}/report`,
      ),
    onSuccess: (data) => {
      setReport(data.body_markdown);
      setTab("report");
      queryClient.invalidateQueries({ queryKey: ["experiment", id] });
    },
  });

  if (detail.isLoading) return <Loading label="Loading experiment" />;
  if (detail.error) return <ErrorState error={detail.error} retry={detail.refetch} />;

  const data = detail.data!;
  const experiment = data.experiment;
  const totalRuns = data.runs.length;
  const succeeded = data.run_counts.succeeded ?? 0;
  const failed = data.run_counts.failed ?? 0;
  const pending = (data.run_counts.pending ?? 0) + (data.run_counts.running ?? 0);
  const activeJob = data.jobs.find((j) => j.status === "running" || j.status === "queued");
  const questionsById = new Map(data.questions.map((q) => [q.id, q]));
  const conditionsById = new Map(data.conditions.map((c) => [c.id, c]));

  return (
    <>
      <PageHeader
        eyebrow={`Experiment · ${experiment.type.replace(/_/g, " ")}`}
        title={experiment.name}
        description={experiment.objective || "No objective recorded."}
        actions={
          <>
            {failed > 0 ? (
              <Button loading={retry.isPending} onClick={() => retry.mutate()}>
                Retry {failed} failed run{failed === 1 ? "" : "s"}
              </Button>
            ) : null}
            <a href={api.downloadUrl(`experiments/${id}/export?format=csv`)} download>
              <Button>Export CSV</Button>
            </a>
            <a href={api.downloadUrl(`experiments/${id}/export?format=json`)} download>
              <Button>Export JSON</Button>
            </a>
            <Button
              variant="primary"
              loading={makeReport.isPending}
              onClick={() => makeReport.mutate()}
            >
              Generate report
            </Button>
          </>
        }
      />

      {retry.error ? <ErrorState error={retry.error} /> : null}

      <Section>
        <Card>
          <div className="flex flex-wrap items-center gap-x-6 gap-y-3 px-4 py-3">
            <ol className="flex flex-wrap items-center gap-1.5 text-xs">
              {LIFECYCLE.map((stage, index) => {
                const currentIndex = LIFECYCLE.indexOf(experiment.status);
                const reached = currentIndex >= index;
                const isFailed = experiment.status === "failed";
                return (
                  <li key={stage} className="flex items-center gap-1.5">
                    <span
                      className={
                        "rounded px-1.5 py-0.5 font-medium " +
                        (reached && !isFailed
                          ? "bg-accent-soft text-accent-strong"
                          : "text-ink-faint")
                      }
                    >
                      {stage}
                    </span>
                    {index < LIFECYCLE.length - 1 ? (
                      <span className="text-ink-faint" aria-hidden>
                        →
                      </span>
                    ) : null}
                  </li>
                );
              })}
            </ol>
            {experiment.status === "failed" ? (
              <Badge tone="danger">failed</Badge>
            ) : null}
            <div className="ml-auto">
              <KeyValue
                columns={3}
                items={[
                  { label: "Seed", value: <Mono>{experiment.seed}</Mono> },
                  { label: "Replicates", value: experiment.repetitions },
                  {
                    label: "Est. cost",
                    value: formatUsd(experiment.estimated_cost_usd),
                    hint: "Pre-flight estimate; actual spend is in the usage records.",
                  },
                ]}
              />
            </div>
          </div>
        </Card>
      </Section>

      {activeJob ? (
        <Section>
          <Card>
            <CardHeader
              title="Batch in progress"
              description="Failed runs do not stop the batch; each is recorded and retryable."
              actions={<Badge tone="warn">{activeJob.status}</Badge>}
            />
            <div className="px-4 py-3">
              <ProgressBar done={activeJob.progress_done} total={activeJob.progress_total} />
            </div>
          </Card>
        </Section>
      ) : null}

      <Tabs
        tabs={[
          { id: "progress", label: "Runs", count: totalRuns },
          { id: "conditions", label: "Conditions", count: data.conditions.length },
          { id: "results", label: "Results" },
          { id: "report", label: "Report" },
          { id: "notes", label: "Notes" },
        ]}
        active={tab}
        onChange={setTab}
      />

      {tab === "progress" ? (
        <>
          <div className="mb-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
            {[
              { label: "Total runs", value: totalRuns, tone: "" },
              { label: "Succeeded", value: succeeded, tone: "text-accent" },
              { label: "Failed", value: failed, tone: failed ? "text-danger" : "" },
              { label: "Pending", value: pending, tone: pending ? "text-warn" : "" },
            ].map((metric) => (
              <Card key={metric.label} className="px-4 py-3">
                <p className="text-2xs uppercase tracking-wide text-ink-faint">{metric.label}</p>
                <p className={`mt-0.5 text-xl font-semibold tabular-nums ${metric.tone}`}>
                  {metric.value}
                </p>
              </Card>
            ))}
          </div>

          <Table head={["Status", "Condition", "Question", "Rep", "Attempts", "Error"]}>
            {data.runs.map((run) => {
              const condition = conditionsById.get(run.condition_id);
              const question = questionsById.get(run.question_id);
              return (
                <Tr key={run.id}>
                  <Td>
                    <span className="inline-flex items-center gap-1.5 whitespace-nowrap text-xs">
                      <StatusDot status={run.status} />
                      {run.status}
                    </span>
                  </Td>
                  <Td className="text-xs">{condition?.label ?? run.condition_id}</Td>
                  <Td className="max-w-[26rem] text-xs text-ink-muted">
                    {question?.text ?? run.question_id}
                  </Td>
                  <Td className="tabular-nums text-xs">{run.replicate_index}</Td>
                  <Td className="tabular-nums text-xs">{run.attempts}</Td>
                  <Td className="max-w-[22rem] text-xs">
                    {run.error ? (
                      <span className="text-danger">
                        <span className="font-medium">{run.error_type}</span>: {run.error}
                      </span>
                    ) : (
                      <span className="text-ink-faint">—</span>
                    )}
                  </Td>
                </Tr>
              );
            })}
          </Table>
        </>
      ) : null}

      {tab === "conditions" ? (
        <div className="space-y-3">
          {data.conditions.map((condition) => (
            <Card key={condition.id}>
              <CardHeader
                title={condition.label}
                description={
                  condition.treatments.length
                    ? `Treatments: ${condition.treatments.join(" + ")}`
                    : "No transformation (control / baseline arm)"
                }
              />
              <div className="px-4 py-3">
                <KeyValue
                  columns={3}
                  items={[
                    { label: "Source model", value: <Mono>{`${condition.provider}/${condition.model_id}`}</Mono> },
                    {
                      label: "Transformation model",
                      value: condition.transform_model_id ? (
                        <Mono>{`${condition.transform_provider}/${condition.transform_model_id}`}</Mono>
                      ) : (
                        <span className="text-ink-faint">—</span>
                      ),
                      hint: "Configured separately from the source model so the two can be told apart.",
                    },
                    {
                      label: "Prompt version",
                      value: condition.prompt_version_id ? (
                        <Mono>{condition.prompt_version_id.slice(0, 8)}</Mono>
                      ) : (
                        <span className="text-ink-faint">—</span>
                      ),
                    },
                    {
                      label: "Requested settings",
                      value: (
                        <Mono>{JSON.stringify(condition.generation_settings)}</Mono>
                      ),
                    },
                  ]}
                />
              </div>
            </Card>
          ))}
          <Caveat>
            Experiment configuration is immutable once created. Editing a prompt template later
            creates a new version and leaves this experiment&apos;s record untouched.
          </Caveat>
        </div>
      ) : null}

      {tab === "results" ? (
        summary.isLoading ? (
          <Loading label="Aggregating results" />
        ) : summary.error ? (
          <ErrorState error={summary.error} retry={summary.refetch} />
        ) : !summary.data ? (
          <EmptyState title="No completed runs yet">
            Results appear once at least one run has succeeded.
          </EmptyState>
        ) : (
          <div className="space-y-6">
            {summary.data.contains_synthetic_data ? (
              <Caveat tone="synthetic">
                This experiment contains synthetic demo output. The figures below describe fixture
                text and are not research findings.
              </Caveat>
            ) : null}
            <Caveat>{summary.data.evidence_note}</Caveat>
            <ConditionSummaryTable summary={summary.data} />
            <DiagnosticsComparison summary={summary.data} />
            <div className="flex flex-wrap gap-2">
              <Link href={`/compare?experiment=${id}`}>
                <Button>Open in comparison workspace</Button>
              </Link>
              <Link href={`/studies?experiment=${id}`}>
                <Button variant="primary">Create a human comprehension study</Button>
              </Link>
            </div>
          </div>
        )
      ) : null}

      {tab === "report" ? (
        report ? (
          <Card>
            <CardHeader
              title="Generated report"
              description="Markdown; also available as a file export"
              actions={
                <a href={api.downloadUrl(`experiments/${id}/export?format=markdown`)} download>
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
              <Button
                variant="primary"
                loading={makeReport.isPending}
                onClick={() => makeReport.mutate()}
              >
                Generate report
              </Button>
            }
          >
            The report records the objective, hypothesis, conditions, dataset, methodology,
            results and limitations. It states what the evidence does and does not support — it
            does not write conclusions for you.
          </EmptyState>
        )
      ) : null}

      {tab === "notes" ? (
        <Card>
          <CardHeader
            title="Researcher notes"
            description="Included in the generated report"
            actions={
              <Button
                size="sm"
                variant="primary"
                loading={saveNotes.isPending}
                onClick={() => saveNotes.mutate(notes ?? experiment.researcher_notes)}
              >
                Save
              </Button>
            }
          />
          <div className="px-4 py-3">
            <Textarea
              rows={12}
              value={notes ?? experiment.researcher_notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Observations, anomalies, decisions taken during the run, and anything that would change how these results should be read."
            />
          </div>
        </Card>
      ) : null}
    </>
  );
}
