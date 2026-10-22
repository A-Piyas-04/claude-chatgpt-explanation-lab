"use client";

/**
 * Shared result views.
 *
 * Charting rule applied throughout: a bar is only drawn for a quantity where
 * the comparison is meaningful, every chart states its evidence class, and
 * where an interval exists it is drawn as an error bar rather than implied by
 * a bare bar height.
 */

import React from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ErrorBar,
  Legend,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import {
  Badge,
  Caveat,
  Card,
  CardHeader,
  EvidenceLabel,
  Select,
  StatValue,
  SyntheticBadge,
  Table,
  Td,
  Tr,
  formatMs,
  formatUsd,
} from "./ui";
import { ExperimentSummary, StatSummary, StudyResults } from "@/lib/api";

const SERIES_COLORS = ["#2f5d50", "#8a5a00", "#6b21a8", "#1f6f8b", "#9b2c25", "#4a5c2f"];

const DIAGNOSTIC_LABELS: Record<string, string> = {
  word_count: "Words",
  avg_sentence_words: "Avg sentence length",
  long_sentence_share: "Share of sentences > 30 words",
  max_paragraph_words: "Longest paragraph (words)",
  flesch_reading_ease: "Flesch reading ease",
  flesch_kincaid_grade: "Flesch–Kincaid grade",
  jargon_candidates: "Jargon candidates",
  nominalisation_density: "Nominalisation density",
  indirection_phrases: "Indirection phrases",
  unresolved_references: "Unresolved references",
  heading_count: "Headings",
  causal_density_per_100w: "Causal markers / 100 words",
  repeated_trigrams: "Repeated trigrams",
  checklist_coverage_ratio: "Checklist coverage",
  terms_undefined_share: "Terms undefined at first use",
};

const JUDGE_LABELS: Record<string, string> = {
  clarity: "Clarity",
  logical_progression: "Logical progression",
  prerequisite_handling: "Prerequisite handling",
  mechanism_explanation: "Mechanism explanation",
  example_quality: "Example quality",
  audience_suitability: "Audience suitability",
  unnecessary_complexity: "No unnecessary complexity",
  information_loss: "No information loss",
  factual_fidelity: "Factual fidelity",
};

function shortLabel(label: string, max = 28): string {
  return label.length > max ? `${label.slice(0, max - 1)}…` : label;
}

/** Bar chart of one metric across conditions, with bootstrap error bars. */
export function MetricBars({
  rows,
  title,
  description,
  evidenceClass,
  domain,
}: {
  rows: { label: string; summary: StatSummary; synthetic?: boolean }[];
  title: string;
  description?: string;
  evidenceClass: string;
  domain?: [number, number];
}) {
  const data = rows
    .filter((row) => row.summary?.mean !== null && row.summary?.mean !== undefined)
    .map((row, index) => {
      const mean = row.summary.mean!;
      const low = row.summary.ci_low;
      const high = row.summary.ci_high;
      return {
        name: shortLabel(row.label),
        fullName: row.label,
        mean,
        n: row.summary.n,
        // Recharts ErrorBar takes [downwards, upwards] offsets.
        error:
          low !== null && high !== null ? [mean - low, high - mean] : undefined,
        synthetic: row.synthetic ?? false,
        color: SERIES_COLORS[index % SERIES_COLORS.length],
      };
    });

  if (data.length === 0) return null;

  return (
    <Card>
      <CardHeader
        title={title}
        description={description}
        actions={<EvidenceLabel evidenceClass={evidenceClass} />}
      />
      <div className="px-2 py-4">
        <ResponsiveContainer width="100%" height={Math.max(200, data.length * 44 + 40)}>
          <BarChart data={data} layout="vertical" margin={{ left: 8, right: 24, top: 4, bottom: 4 }}>
            <CartesianGrid horizontal={false} stroke="#e5e4e0" />
            <XAxis
              type="number"
              domain={domain ?? ["auto", "auto"]}
              tick={{ fontSize: 11, fill: "#8a8a82" }}
              stroke="#d2d1cc"
            />
            <YAxis
              type="category"
              dataKey="name"
              width={190}
              tick={{ fontSize: 11, fill: "#5c5c57" }}
              stroke="#d2d1cc"
            />
            <Tooltip
              contentStyle={{
                fontSize: 12,
                borderRadius: 6,
                border: "1px solid #e5e4e0",
                boxShadow: "0 8px 24px rgba(26,26,24,0.10)",
              }}
              formatter={(value: unknown, _name, item) => {
                const payload = item?.payload as { n?: number } | undefined;
                return [`${value} (n=${payload?.n ?? "?"})`, "mean"];
              }}
              labelFormatter={(_label, payload) =>
                (payload?.[0]?.payload as { fullName?: string } | undefined)?.fullName ?? ""
              }
            />
            <Bar dataKey="mean" radius={[0, 3, 3, 0]} barSize={18}>
              {data.map((entry, index) => (
                <Cell key={index} fill={entry.color} fillOpacity={entry.synthetic ? 0.45 : 1} />
              ))}
              <ErrorBar dataKey="error" width={5} strokeWidth={1.25} stroke="#1a1a18" />
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
      <div className="border-t border-line px-4 py-2.5">
        <p className="text-2xs leading-relaxed text-ink-faint">
          Whiskers are 95% percentile-bootstrap intervals; a bar with no whisker has too few
          observations for an interval. Faded bars contain synthetic fixture data.
        </p>
      </div>
    </Card>
  );
}

/** Per-condition overview table for an experiment. */
export function ConditionSummaryTable({ summary }: { summary: ExperimentSummary }) {
  return (
    <Table
      head={[
        "Condition",
        "Source model",
        "Treatments",
        "Runs",
        "Words",
        "Avg sentence",
        "Fidelity",
        "Latency",
        "Cost",
      ]}
    >
      {summary.conditions.map((condition) => {
        const diagnostics = condition.automated_diagnostics.metrics;
        return (
          <Tr key={condition.condition_id}>
            <Td>
              <span className="flex flex-wrap items-center gap-1.5 text-xs font-medium">
                {condition.label}
                {condition.contains_synthetic ? <SyntheticBadge /> : null}
              </span>
            </Td>
            <Td className="font-mono text-2xs text-ink-muted">{condition.model_id}</Td>
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
                <span className="text-ink-faint">control</span>
              )}
            </Td>
            <Td className="whitespace-nowrap text-xs">
              <span className="text-accent">{condition.runs.succeeded}</span>
              {condition.runs.failed > 0 ? (
                <span className="text-danger"> / {condition.runs.failed} failed</span>
              ) : null}
            </Td>
            <Td className="text-xs">
              <StatValue summary={diagnostics.word_count ?? null} format={(v) => v.toFixed(0)} compact />
            </Td>
            <Td className="text-xs">
              <StatValue summary={diagnostics.avg_sentence_words ?? null} compact />
            </Td>
            <Td className="text-xs">
              {condition.fidelity.reports ? (
                <span className="flex flex-wrap items-center gap-1">
                  {Object.entries(condition.fidelity.by_verdict ?? {}).map(([verdict, count]) => (
                    <Badge
                      key={verdict}
                      tone={
                        verdict === "serious_concerns"
                          ? "danger"
                          : verdict === "warnings"
                            ? "warn"
                            : "neutral"
                      }
                    >
                      {verdict.replace(/_/g, " ")} {count}
                    </Badge>
                  ))}
                </span>
              ) : (
                <span className="text-ink-faint">—</span>
              )}
            </Td>
            <Td className="whitespace-nowrap text-xs tabular-nums">
              {condition.operations.latency_ms?.mean
                ? formatMs(condition.operations.latency_ms.mean)
                : "—"}
            </Td>
            <Td className="whitespace-nowrap text-xs tabular-nums">
              {formatUsd(condition.operations.total_cost_usd)}
            </Td>
          </Tr>
        );
      })}
    </Table>
  );
}

/** Metric selector plus bar chart for an experiment's conditions. */
export function DiagnosticsComparison({ summary }: { summary: ExperimentSummary }) {
  const availableDiagnostics = React.useMemo(() => {
    const keys = new Set<string>();
    for (const condition of summary.conditions) {
      Object.keys(condition.automated_diagnostics.metrics ?? {}).forEach((k) => keys.add(k));
    }
    return [...keys];
  }, [summary]);

  const availableJudge = React.useMemo(() => {
    const keys = new Set<string>();
    for (const condition of summary.conditions) {
      Object.keys(condition.ai_judge.metrics ?? {}).forEach((k) => keys.add(k));
    }
    return [...keys];
  }, [summary]);

  const [metric, setMetric] = React.useState<string>(
    availableDiagnostics.includes("avg_sentence_words") ? "avg_sentence_words" : availableDiagnostics[0] ?? "",
  );
  const [judgeMetric, setJudgeMetric] = React.useState<string>(
    availableJudge.includes("clarity") ? "clarity" : availableJudge[0] ?? "",
  );

  const judgeModels = [
    ...new Set(summary.conditions.flatMap((c) => c.ai_judge.judge_models ?? [])),
  ];

  return (
    <div className="space-y-5">
      {availableDiagnostics.length > 0 ? (
        <div>
          <div className="mb-2 flex flex-wrap items-center gap-2">
            <label className="text-xs font-medium">Diagnostic metric</label>
            <Select
              className="w-auto text-xs"
              value={metric}
              onChange={(e) => setMetric(e.target.value)}
            >
              {availableDiagnostics.map((key) => (
                <option key={key} value={key}>
                  {DIAGNOSTIC_LABELS[key] ?? key}
                </option>
              ))}
            </Select>
          </div>
          <MetricBars
            title={DIAGNOSTIC_LABELS[metric] ?? metric}
            description="Deterministic surface measure, by condition"
            evidenceClass="automated_diagnostic"
            rows={summary.conditions.map((condition) => ({
              label: condition.label,
              summary: condition.automated_diagnostics.metrics[metric],
              synthetic: condition.contains_synthetic,
            }))}
          />
          <Caveat className="mt-2">
            {summary.conditions[0]?.automated_diagnostics.caveat ??
              "Surface diagnostics describe a text; they do not measure understanding."}
          </Caveat>
        </div>
      ) : null}

      {availableJudge.length > 0 ? (
        <div>
          <div className="mb-2 flex flex-wrap items-center gap-2">
            <label className="text-xs font-medium">AI judge dimension</label>
            <Select
              className="w-auto text-xs"
              value={judgeMetric}
              onChange={(e) => setJudgeMetric(e.target.value)}
            >
              {availableJudge.map((key) => (
                <option key={key} value={key}>
                  {JUDGE_LABELS[key] ?? key}
                </option>
              ))}
            </Select>
            {judgeModels.length > 0 ? (
              <span className="text-2xs text-ink-faint">judge: {judgeModels.join(", ")}</span>
            ) : null}
          </div>
          <MetricBars
            title={JUDGE_LABELS[judgeMetric] ?? judgeMetric}
            description="Blinded judge rating on a 1–5 anchored scale"
            evidenceClass="ai_judge_opinion"
            domain={[1, 5]}
            rows={summary.conditions.map((condition) => ({
              label: condition.label,
              summary: condition.ai_judge.metrics[judgeMetric],
              synthetic: condition.contains_synthetic,
            }))}
          />
          <Caveat tone="warn" className="mt-2">
            A higher judge score is not evidence that a model teaches better. Judge models show
            position, verbosity and self-enhancement bias; this platform blinds them to model
            identity, but that mitigates rather than removes the problem.
          </Caveat>
        </div>
      ) : (
        <Caveat>
          No AI judge evaluations yet. Run them from the comparison workspace — they are an
          opinion, useful for triage, and never a substitute for a human study.
        </Caveat>
      )}
    </div>
  );
}

/**
 * Study results: comprehension and perceived clarity side by side, never
 * combined. The juxtaposition is the point — the fluency literature predicts
 * they can move in opposite directions.
 */
export function StudyResultsView({ results }: { results: StudyResults }) {
  const comprehensionRows = results.conditions.map((condition) => ({
    label: condition.label,
    summary: condition.human_comprehension.overall,
    synthetic: condition.contains_synthetic_stimulus,
  }));
  const clarityRows = results.conditions.map((condition) => ({
    label: condition.label,
    summary: condition.human_preference.perceived_clarity,
    synthetic: condition.contains_synthetic_stimulus,
  }));
  const effortRows = results.conditions.map((condition) => ({
    label: condition.label,
    summary: condition.human_preference.cognitive_effort,
    synthetic: condition.contains_synthetic_stimulus,
  }));

  // Clarity against comprehension: the dissociation check.
  const scatter = results.conditions
    .filter(
      (c) =>
        c.human_comprehension.overall.mean !== null &&
        c.human_preference.perceived_clarity.mean !== null,
    )
    .map((c, index) => ({
      name: c.label,
      comprehension: c.human_comprehension.overall.mean,
      clarity: c.human_preference.perceived_clarity.mean,
      n: c.human_comprehension.overall.n,
      color: SERIES_COLORS[index % SERIES_COLORS.length],
    }));

  return (
    <div className="space-y-6">
      <Caveat tone="accent">{results.evidence_note}</Caveat>

      {results.warnings.length > 0 ? (
        <Card>
          <CardHeader title="Read these first" description="Limits on what these numbers support" />
          <ul className="space-y-1.5 px-4 py-3 text-xs leading-relaxed text-ink-muted">
            {results.warnings.map((warning, i) => (
              <li key={i} className="flex gap-2">
                <span aria-hidden className="text-warn">
                  ▲
                </span>
                <span>{warning}</span>
              </li>
            ))}
          </ul>
        </Card>
      ) : null}

      <MetricBars
        title="Comprehension score"
        description="Proportion of available comprehension points earned. The primary evidence."
        evidenceClass="human_comprehension"
        domain={[0, 1]}
        rows={comprehensionRows}
      />

      <div className="grid gap-5 lg:grid-cols-2">
        <MetricBars
          title="Perceived clarity"
          description="Participant self-report, 1–7"
          evidenceClass="human_preference"
          domain={[1, 7]}
          rows={clarityRows}
        />
        <MetricBars
          title="Cognitive effort"
          description="Participant self-report, 1–7 (higher = more demanding)"
          evidenceClass="human_preference"
          domain={[1, 7]}
          rows={effortRows}
        />
      </div>

      {scatter.length > 1 ? (
        <Card>
          <CardHeader
            title="Perceived clarity against measured comprehension"
            description="If these diverge, that is a finding — not an error"
          />
          <div className="px-2 py-4">
            <ResponsiveContainer width="100%" height={280}>
              <ScatterChart margin={{ left: 8, right: 24, top: 8, bottom: 24 }}>
                <CartesianGrid stroke="#e5e4e0" />
                <XAxis
                  type="number"
                  dataKey="clarity"
                  name="Perceived clarity"
                  domain={[1, 7]}
                  tick={{ fontSize: 11, fill: "#8a8a82" }}
                  stroke="#d2d1cc"
                  label={{
                    value: "Perceived clarity (1–7)",
                    position: "insideBottom",
                    offset: -14,
                    style: { fontSize: 11, fill: "#5c5c57" },
                  }}
                />
                <YAxis
                  type="number"
                  dataKey="comprehension"
                  name="Comprehension"
                  domain={[0, 1]}
                  tick={{ fontSize: 11, fill: "#8a8a82" }}
                  stroke="#d2d1cc"
                  label={{
                    value: "Comprehension",
                    angle: -90,
                    position: "insideLeft",
                    style: { fontSize: 11, fill: "#5c5c57" },
                  }}
                />
                <Tooltip
                  contentStyle={{ fontSize: 12, borderRadius: 6, border: "1px solid #e5e4e0" }}
                  formatter={(value: unknown, name) => [String(value), String(name)]}
                  labelFormatter={() => ""}
                />
                <Legend wrapperStyle={{ fontSize: 11 }} />
                <Scatter name="Condition" data={scatter} fill="#2f5d50">
                  {scatter.map((point, index) => (
                    <Cell key={index} fill={point.color} />
                  ))}
                </Scatter>
              </ScatterChart>
            </ResponsiveContainer>
          </div>
          <div className="border-t border-line px-4 py-2.5">
            <p className="text-2xs leading-relaxed text-ink-faint">
              A condition high on clarity but low on comprehension is the illusion-of-fluency
              pattern: it felt easy and taught less. That is exactly the outcome a blended
              &ldquo;quality score&rdquo; would hide.
            </p>
          </div>
        </Card>
      ) : null}

      <Table
        head={[
          "Condition",
          "Submitted",
          "Comprehension",
          "Misconception rate",
          "Clarity",
          "Effort",
          "Reading time",
          "Ungraded",
        ]}
      >
        {results.conditions.map((condition) => (
          <Tr key={condition.condition_id}>
            <Td>
              <span className="flex flex-wrap items-center gap-1.5 text-xs font-medium">
                {condition.label}
                {condition.contains_synthetic_stimulus ? <SyntheticBadge /> : null}
              </span>
              {condition.treatments.length ? (
                <span className="mt-1 flex flex-wrap gap-1">
                  {condition.treatments.map((t) => (
                    <Badge key={t} tone="accent">
                      {t}
                    </Badge>
                  ))}
                </span>
              ) : null}
            </Td>
            <Td className="tabular-nums text-xs">
              {condition.participants.submitted} / {condition.participants.assigned}
              {condition.participants.withdrawn > 0 ? (
                <span className="text-ink-faint"> ({condition.participants.withdrawn} withdrew)</span>
              ) : null}
            </Td>
            <Td className="text-xs">
              <StatValue
                summary={condition.human_comprehension.overall}
                format={(v) => `${Math.round(v * 100)}%`}
              />
            </Td>
            <Td className="tabular-nums text-xs">
              {condition.human_comprehension.misconception_rate === null
                ? "—"
                : `${Math.round(condition.human_comprehension.misconception_rate * 100)}%`}
            </Td>
            <Td className="text-xs">
              <StatValue summary={condition.human_preference.perceived_clarity} compact />
            </Td>
            <Td className="text-xs">
              <StatValue summary={condition.human_preference.cognitive_effort} compact />
            </Td>
            <Td className="text-xs">
              <StatValue
                summary={condition.time.reading_seconds}
                format={(v) => `${Math.round(v)}s`}
                compact
              />
            </Td>
            <Td className="tabular-nums text-xs">
              {condition.human_comprehension.pending_grading_items > 0 ? (
                <Badge tone="warn">{condition.human_comprehension.pending_grading_items}</Badge>
              ) : (
                <span className="text-ink-faint">0</span>
              )}
            </Td>
          </Tr>
        ))}
      </Table>

      <Caveat tone="warn">
        {results.conditions[0]?.human_preference.caveat ??
          "Self-reported clarity is not a measure of comprehension."}
      </Caveat>
    </div>
  );
}
