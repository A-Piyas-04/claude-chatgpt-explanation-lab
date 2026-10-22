"use client";

/**
 * Results and analytics.
 *
 * Cross-cutting comparisons by model, provider, treatment, topic and learner
 * level, plus the cost/latency price of each technique. Synthetic rows are
 * excluded by default so the dashboard is never quietly populated with fixture
 * data.
 */

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import React from "react";

import {
  Badge,
  Button,
  Caveat,
  Card,
  CardHeader,
  Checkbox,
  EmptyState,
  ErrorState,
  EvidenceLabel,
  Field,
  Loading,
  PageHeader,
  Section,
  Select,
  StatValue,
  Table,
  Td,
  Tr,
  formatMs,
  formatUsd,
} from "@/components/ui";
import { MetricBars } from "@/components/results";
import { StatSummary, api } from "@/lib/api";
import { useExperiments, useStudies } from "@/lib/hooks";

interface Breakdown {
  group_by: string;
  metric: string;
  evidence_class: string;
  groups: (StatSummary & { key: string; independence_warnings: string[] })[];
  include_synthetic: boolean;
  note?: string;
  caveat: string;
}

interface CostLatency {
  groups: {
    treatments: string;
    n: number;
    cost_usd: StatSummary;
    latency_ms: StatSummary;
    output_tokens: StatSummary;
  }[];
  note: string;
}

const GROUP_OPTIONS = [
  { value: "model", label: "Model" },
  { value: "provider", label: "Provider" },
  { value: "treatment", label: "Treatment" },
  { value: "domain", label: "Topic domain" },
  { value: "learner_level", label: "Learner level" },
];

const METRIC_OPTIONS = [
  { value: "judge_clarity", label: "AI judge · clarity", evidence: "ai_judge_opinion" },
  {
    value: "judge_mechanism_explanation",
    label: "AI judge · mechanism explanation",
    evidence: "ai_judge_opinion",
  },
  {
    value: "judge_prerequisite_handling",
    label: "AI judge · prerequisite handling",
    evidence: "ai_judge_opinion",
  },
  {
    value: "judge_unnecessary_complexity",
    label: "AI judge · no unnecessary complexity",
    evidence: "ai_judge_opinion",
  },
  { value: "word_count", label: "Diagnostic · word count", evidence: "automated_diagnostic" },
  {
    value: "avg_sentence_words",
    label: "Diagnostic · average sentence length",
    evidence: "automated_diagnostic",
  },
  {
    value: "flesch_reading_ease",
    label: "Diagnostic · Flesch reading ease",
    evidence: "automated_diagnostic",
  },
  {
    value: "jargon_candidates",
    label: "Diagnostic · jargon candidates",
    evidence: "automated_diagnostic",
  },
  {
    value: "indirection_phrases",
    label: "Diagnostic · indirection phrases",
    evidence: "automated_diagnostic",
  },
  {
    value: "unresolved_references",
    label: "Diagnostic · unresolved references",
    evidence: "automated_diagnostic",
  },
  {
    value: "causal_density_per_100w",
    label: "Diagnostic · causal markers per 100 words",
    evidence: "automated_diagnostic",
  },
  {
    value: "checklist_coverage_ratio",
    label: "Diagnostic · factual checklist coverage",
    evidence: "automated_diagnostic",
  },
  { value: "latency_ms", label: "Operations · latency", evidence: "automated_diagnostic" },
  { value: "cost_usd", label: "Operations · cost", evidence: "automated_diagnostic" },
];

export default function ResultsPage() {
  const [groupBy, setGroupBy] = React.useState("model");
  const [metric, setMetric] = React.useState("avg_sentence_words");
  const [includeSynthetic, setIncludeSynthetic] = React.useState(false);

  const experiments = useExperiments();
  const studies = useStudies();

  const breakdown = useQuery({
    queryKey: ["breakdown", groupBy, metric, includeSynthetic],
    queryFn: () =>
      api.get<Breakdown>(
        `analytics/breakdown?group_by=${groupBy}&metric=${metric}&include_synthetic=${includeSynthetic}`,
      ),
  });

  const costLatency = useQuery({
    queryKey: ["cost-latency", includeSynthetic],
    queryFn: () => api.get<CostLatency>(`analytics/cost-latency?include_synthetic=${includeSynthetic}`),
  });

  const metricMeta = METRIC_OPTIONS.find((m) => m.value === metric);

  return (
    <>
      <PageHeader
        eyebrow="Results and analytics"
        title="Compare conditions"
        description="Slice one measure across models, treatments, topics or learner levels. Remember what each measure is: only human study results are evidence of comprehension."
      />

      <Caveat tone="accent" className="mb-5">
        <strong>Reading these charts:</strong> a difference in a diagnostic means the texts differ.
        A difference in a judge score means one model&apos;s opinion differs. Neither tells you a
        human understood more. For that, open a{" "}
        <Link href="/studies" className="underline">
          human comprehension study
        </Link>
        .
      </Caveat>

      <Card className="mb-5">
        <div className="flex flex-wrap items-end gap-4 px-4 py-3">
          <Field label="Group by">
            <Select value={groupBy} onChange={(e) => setGroupBy(e.target.value)}>
              {GROUP_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="Measure" className="min-w-[18rem]">
            <Select value={metric} onChange={(e) => setMetric(e.target.value)}>
              {METRIC_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </Select>
          </Field>
          <div className="pb-1.5">
            <Checkbox
              checked={includeSynthetic}
              onChange={setIncludeSynthetic}
              label="Include synthetic demo data"
              description="Off by default so results are never silently populated with fixtures."
            />
          </div>
        </div>
      </Card>

      {breakdown.isLoading ? (
        <Loading label="Aggregating" />
      ) : breakdown.error ? (
        <ErrorState error={breakdown.error} retry={breakdown.refetch} />
      ) : breakdown.data!.groups.length === 0 ? (
        <EmptyState
          title="Nothing to compare yet"
          action={
            <Link href="/studio">
              <Button variant="primary">Run an experiment</Button>
            </Link>
          }
        >
          {breakdown.data!.note ??
            "Run an experiment, or enable synthetic demo data to see how this page works."}
        </EmptyState>
      ) : (
        <Section>
          <MetricBars
            title={metricMeta?.label ?? metric}
            description={`Grouped by ${GROUP_OPTIONS.find((g) => g.value === groupBy)?.label.toLowerCase()}`}
            evidenceClass={breakdown.data!.evidence_class}
            domain={metric.startsWith("judge_") ? [1, 5] : undefined}
            rows={breakdown.data!.groups.map((group) => ({
              label: group.key,
              summary: group,
              synthetic: includeSynthetic,
            }))}
          />

          <Table
            head={["Group", "Mean", "95% interval", "n", "SD", "Clustering"]}
            className="mt-4"
          >
            {breakdown.data!.groups.map((group) => (
              <Tr key={group.key}>
                <Td className="text-xs font-medium">{group.key}</Td>
                <Td className="tabular-nums text-xs">{group.mean ?? "—"}</Td>
                <Td className="tabular-nums text-xs">
                  {group.ci_low !== null ? `${group.ci_low} – ${group.ci_high}` : "n too small"}
                </Td>
                <Td className="tabular-nums text-xs">{group.n}</Td>
                <Td className="tabular-nums text-xs">{group.sd ?? "—"}</Td>
                <Td className="max-w-[22rem] text-2xs text-warn">
                  {group.independence_warnings.length > 0
                    ? group.independence_warnings.join(" ")
                    : "—"}
                </Td>
              </Tr>
            ))}
          </Table>

          <Caveat className="mt-3">{breakdown.data!.caveat}</Caveat>
        </Section>
      )}

      <Section
        title="Cost and latency per technique"
        description="What each treatment set costs in money and time"
      >
        {costLatency.isLoading ? (
          <Loading />
        ) : costLatency.error ? (
          <ErrorState error={costLatency.error} />
        ) : costLatency.data!.groups.length === 0 ? (
          <EmptyState title="No cost data yet" />
        ) : (
          <>
            <Table head={["Treatments", "n", "Cost per answer", "Latency", "Output tokens"]}>
              {costLatency.data!.groups.map((group) => (
                <Tr key={group.treatments}>
                  <Td className="text-xs font-medium">
                    {group.treatments === "(untransformed)" ? (
                      <span className="text-ink-faint">untransformed</span>
                    ) : (
                      <span className="flex flex-wrap gap-1">
                        {group.treatments.split("+").map((t) => (
                          <Badge key={t} tone="accent">
                            {t}
                          </Badge>
                        ))}
                      </span>
                    )}
                  </Td>
                  <Td className="tabular-nums text-xs">{group.n}</Td>
                  <Td className="text-xs">
                    <StatValue summary={group.cost_usd} format={(v) => formatUsd(v)} compact />
                  </Td>
                  <Td className="text-xs">
                    <StatValue summary={group.latency_ms} format={(v) => formatMs(v)} compact />
                  </Td>
                  <Td className="text-xs">
                    <StatValue summary={group.output_tokens} format={(v) => v.toFixed(0)} compact />
                  </Td>
                </Tr>
              ))}
            </Table>
            <Caveat className="mt-3">{costLatency.data!.note}</Caveat>
          </>
        )}
      </Section>

      <div className="grid gap-5 lg:grid-cols-2">
        <Card>
          <CardHeader
            title="Experiments"
            description="Open one for its per-condition results"
            actions={
              <Link href="/studio">
                <Button size="sm" variant="primary">
                  New
                </Button>
              </Link>
            }
          />
          {(experiments.data ?? []).length === 0 ? (
            <p className="px-4 py-6 text-sm text-ink-muted">None yet.</p>
          ) : (
            <Table head={["Experiment", "Type", "Status"]} className="rounded-none border-0">
              {(experiments.data ?? []).map((experiment) => (
                <Tr key={experiment.id}>
                  <Td>
                    <Link
                      href={`/experiments/${experiment.id}`}
                      className="text-xs font-medium text-accent-strong underline-offset-2 hover:underline"
                    >
                      {experiment.name}
                    </Link>
                  </Td>
                  <Td className="text-xs text-ink-muted">{experiment.type.replace(/_/g, " ")}</Td>
                  <Td className="text-xs">{experiment.status}</Td>
                </Tr>
              ))}
            </Table>
          )}
        </Card>

        <Card>
          <CardHeader
            title="Human comprehension studies"
            description="The primary evidence"
            actions={
              <Link href="/studies">
                <Button size="sm" variant="primary">
                  New
                </Button>
              </Link>
            }
          />
          {(studies.data ?? []).length === 0 ? (
            <div className="px-4 py-6">
              <p className="text-sm text-ink-muted">
                No studies yet. Diagnostics and judge scores cannot substitute for one.
              </p>
            </div>
          ) : (
            <Table head={["Study", "Status", "Seed"]} className="rounded-none border-0">
              {(studies.data ?? []).map((study) => (
                <Tr key={study.id}>
                  <Td>
                    <Link
                      href={`/studies/${study.id}`}
                      className="text-xs font-medium text-accent-strong underline-offset-2 hover:underline"
                    >
                      {study.name}
                    </Link>
                  </Td>
                  <Td className="text-xs">{study.status}</Td>
                  <Td className="font-mono text-2xs">{study.seed}</Td>
                </Tr>
              ))}
            </Table>
          )}
        </Card>
      </div>
    </>
  );
}
