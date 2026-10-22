"use client";

/**
 * Overview dashboard.
 *
 * Deliberately not a wall of KPI cards: every number here is a real database
 * count, and where a count would be misleading on its own (responses that are
 * demo fixtures, evaluation coverage, failed runs) the breakdown sits next to
 * it rather than behind a drill-down.
 */

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";

import {
  Badge,
  Button,
  Caveat,
  Card,
  CardHeader,
  EmptyState,
  ErrorState,
  KeyValue,
  Loading,
  Mono,
  PageHeader,
  Section,
  StatusDot,
  SyntheticBadge,
  Table,
  Td,
  Tr,
  formatInt,
  formatUsd,
} from "@/components/ui";
import { api, UsagePayload } from "@/lib/api";
import { useOverview } from "@/lib/hooks";
import { useSystemStatus } from "@/components/shell";

function Metric({
  label,
  value,
  detail,
  tone = "neutral",
}: {
  label: string;
  value: React.ReactNode;
  detail?: React.ReactNode;
  tone?: "neutral" | "warn" | "synthetic";
}) {
  return (
    <div className="rounded-lg border border-line bg-surface px-4 py-3 shadow-card">
      <p className="text-2xs uppercase tracking-wide text-ink-faint">{label}</p>
      <p
        className={
          "mt-1 text-2xl font-semibold tabular-nums tracking-tight " +
          (tone === "warn" ? "text-warn" : tone === "synthetic" ? "text-synthetic" : "text-ink")
        }
      >
        {value}
      </p>
      {detail ? <div className="mt-1 text-xs leading-relaxed text-ink-muted">{detail}</div> : null}
    </div>
  );
}

export default function OverviewPage() {
  const overview = useOverview();
  const status = useSystemStatus();
  const usage = useQuery({
    queryKey: ["usage", 30],
    queryFn: () => api.get<UsagePayload>("usage?days=30"),
  });

  if (overview.isLoading) return <Loading label="Loading overview" />;
  if (overview.error) return <ErrorState error={overview.error} retry={overview.refetch} />;
  const data = overview.data!;

  const hasAnything = data.experiments.total > 0 || data.responses.total > 0;

  return (
    <>
      <PageHeader
        eyebrow="Overview"
        title="Research status"
        description="Every figure below is a count from the database. Nothing on this page is estimated or illustrative."
        actions={
          <>
            <Link href="/studio">
              <Button variant="primary">New experiment</Button>
            </Link>
            <Link href="/library">
              <Button>Research library</Button>
            </Link>
          </>
        }
      />

      {!hasAnything ? (
        <EmptyState
          title="No experiments yet"
          action={
            <Link href="/studio">
              <Button variant="primary">Open the experiment studio</Button>
            </Link>
          }
        >
          Start with Experiment 1 (baseline comparison): pick a question from the seeded bank,
          choose one OpenAI and one Anthropic model, and run it. In demo mode this costs nothing
          and produces clearly-labelled fixture output so you can see the whole workflow.
        </EmptyState>
      ) : null}

      <Section>
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
          <Metric
            label="Experiments"
            value={formatInt(data.experiments.total)}
            detail={
              <span className="flex flex-wrap gap-1.5">
                {Object.entries(data.experiments.by_status).map(([key, count]) => (
                  <span key={key} className="inline-flex items-center gap-1">
                    <StatusDot status={key} />
                    {key} {count}
                  </span>
                ))}
              </span>
            }
          />
          <Metric
            label="Completed runs"
            value={formatInt(data.runs.completed)}
            tone={data.runs.failed > 0 ? "warn" : "neutral"}
            detail={
              data.runs.failed > 0 ? (
                <span className="text-warn">
                  {data.runs.failed} failed — retryable without re-running successes
                </span>
              ) : (
                "No failures"
              )
            }
          />
          <Metric
            label="Models evaluated"
            value={formatInt(data.models_evaluated)}
            detail={`${status.data?.model_catalog_entries ?? 0} in the catalogue`}
          />
          <Metric
            label="Active human studies"
            value={formatInt(data.human_studies.active)}
            detail={`${formatInt(data.human_studies.submissions)} participant submission${
              data.human_studies.submissions === 1 ? "" : "s"
            }`}
          />
        </div>
      </Section>

      <div className="grid gap-5 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader
            title="Recent experiments"
            description="Most recently created first"
            actions={
              <Link href="/results">
                <Button size="sm">All results</Button>
              </Link>
            }
          />
          {data.recent_experiments.length === 0 ? (
            <p className="px-4 py-6 text-sm text-ink-muted">None yet.</p>
          ) : (
            <Table head={["Experiment", "Type", "Status", "Created"]} className="rounded-none border-0">
              {data.recent_experiments.map((experiment) => (
                <Tr key={experiment.id}>
                  <Td>
                    <Link
                      href={`/experiments/${experiment.id}`}
                      className="font-medium text-accent-strong underline-offset-2 hover:underline"
                    >
                      {experiment.name}
                    </Link>
                  </Td>
                  <Td className="text-ink-muted">{experiment.type.replace(/_/g, " ")}</Td>
                  <Td>
                    <span className="inline-flex items-center gap-1.5 text-xs">
                      <StatusDot status={experiment.status} />
                      {experiment.status}
                    </span>
                  </Td>
                  <Td className="text-2xs text-ink-faint">
                    {new Date(experiment.created_at).toLocaleString()}
                  </Td>
                </Tr>
              ))}
            </Table>
          )}
        </Card>

        <div className="space-y-5">
          <Card>
            <CardHeader title="Stored responses" description="Raw and transformed explanations" />
            <div className="px-4 py-3">
              <KeyValue
                columns={1}
                items={[
                  { label: "Total", value: formatInt(data.responses.total) },
                  {
                    label: "Real model output",
                    value: formatInt(data.responses.real),
                    hint: "Produced by a live provider call or manually imported",
                  },
                  {
                    label: "Synthetic fixtures",
                    value: (
                      <span className="flex items-center gap-2">
                        {formatInt(data.responses.synthetic)}
                        {data.responses.synthetic > 0 ? <SyntheticBadge /> : null}
                      </span>
                    ),
                  },
                ]}
              />
              {data.contains_synthetic_data ? (
                <Caveat tone="synthetic" className="mt-3">
                  Synthetic rows are excluded from results dashboards by default and are labelled
                  wherever they appear. They are never evidence.
                </Caveat>
              ) : null}
            </div>
          </Card>

          <Card>
            <CardHeader
              title="Evaluation coverage"
              description="How much stored output has been evaluated"
            />
            <div className="px-4 py-3">
              <KeyValue
                columns={1}
                items={[
                  {
                    label: "With automated diagnostics",
                    value: `${formatInt(data.evaluation_coverage.responses_with_diagnostics)}${
                      data.evaluation_coverage.diagnostic_coverage !== null
                        ? ` (${Math.round(data.evaluation_coverage.diagnostic_coverage * 100)}%)`
                        : ""
                    }`,
                  },
                  {
                    label: "With an AI judge opinion",
                    value: `${formatInt(data.evaluation_coverage.responses_with_judge_opinion)}${
                      data.evaluation_coverage.judge_coverage !== null
                        ? ` (${Math.round(data.evaluation_coverage.judge_coverage * 100)}%)`
                        : ""
                    }`,
                  },
                ]}
              />
              <Caveat className="mt-3">
                Neither measures comprehension. Human study results are the primary evidence; see{" "}
                <Link href="/studies" className="underline">
                  Human evaluation
                </Link>
                .
              </Caveat>
            </div>
          </Card>
        </div>
      </div>

      <Section
        title="API usage and estimated cost"
        description="Last 30 days, excluding demo-mode calls"
        className="mt-5"
      >
        {usage.isLoading ? (
          <Loading label="Loading usage" />
        ) : usage.error ? (
          <ErrorState error={usage.error} retry={usage.refetch} />
        ) : (
          <div className="grid gap-5 lg:grid-cols-3">
            <Card className="lg:col-span-2">
              <CardHeader title="Spend by purpose" description="Where the tokens went" />
              {usage.data!.by_purpose.length === 0 ? (
                <p className="px-4 py-6 text-sm text-ink-muted">
                  No billable calls recorded yet.
                </p>
              ) : (
                <Table
                  head={["Purpose", "Calls", "Input tokens", "Output tokens", "Est. cost"]}
                  className="rounded-none border-0"
                >
                  {usage.data!.by_purpose.map((row) => (
                    <Tr key={row.purpose}>
                      <Td className="font-medium">{row.purpose}</Td>
                      <Td className="tabular-nums">{formatInt(row.calls)}</Td>
                      <Td className="tabular-nums">{formatInt(row.input_tokens)}</Td>
                      <Td className="tabular-nums">{formatInt(row.output_tokens)}</Td>
                      <Td className="tabular-nums">{formatUsd(row.estimated_cost_usd)}</Td>
                    </Tr>
                  ))}
                </Table>
              )}
              <div className="border-t border-line px-4 py-3">
                <Caveat>{usage.data!.note}</Caveat>
              </div>
            </Card>

            <div className="space-y-5">
              <Card>
                <CardHeader title="Spend controls" />
                <div className="px-4 py-3">
                  <KeyValue
                    columns={1}
                    items={[
                      {
                        label: "Spent today",
                        value: formatUsd(usage.data!.spend_controls.spent_today_usd),
                      },
                      {
                        label: "Daily cap",
                        value: formatUsd(usage.data!.spend_controls.daily_cap_usd),
                      },
                      {
                        label: "Remaining",
                        value: formatUsd(usage.data!.spend_controls.remaining_today_usd),
                      },
                    ]}
                  />
                  {usage.data!.spend_controls.cap_reached ? (
                    <Caveat tone="danger" className="mt-3">
                      The daily cap has been reached. New model calls are refused until the cap is
                      raised in <Mono>.env</Mono>.
                    </Caveat>
                  ) : null}
                </div>
              </Card>

              <Card>
                <CardHeader title="Errors and caching" />
                <div className="px-4 py-3">
                  <KeyValue
                    columns={1}
                    items={[
                      {
                        label: "Failed calls",
                        value: (
                          <span className={data.usage.errors > 0 ? "text-warn" : undefined}>
                            {formatInt(data.usage.errors)}
                          </span>
                        ),
                      },
                      {
                        label: "Cache hits",
                        value: `${formatInt(usage.data!.cache.hits)} of ${formatInt(
                          usage.data!.cache.total_calls,
                        )}`,
                      },
                    ]}
                  />
                  {usage.data!.errors.by_type.length > 0 ? (
                    <div className="mt-3 flex flex-wrap gap-1.5">
                      {usage.data!.errors.by_type.map((row) => (
                        <Badge key={row.error_type} tone="warn">
                          {row.error_type} ×{row.count}
                        </Badge>
                      ))}
                    </div>
                  ) : null}
                </div>
              </Card>
            </div>
          </div>
        )}
      </Section>
    </>
  );
}
