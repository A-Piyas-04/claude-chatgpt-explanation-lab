"use client";

/**
 * Pedagogical analysis workspace.
 *
 * The concept dependency graph is the centrepiece, and every surface here
 * repeats that its edges are *inferred hypotheses*. The genuinely objective
 * part is the sequencing analysis: given a hypothesised dependency, whether the
 * text actually introduces the prerequisite first is a checkable fact about the
 * text, and that is what makes H2 testable.
 */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Background,
  Controls,
  Edge,
  MarkerType,
  Node,
  Position,
  ReactFlow,
  ReactFlowProvider,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import React from "react";

import {
  Badge,
  Button,
  Caveat,
  Card,
  CardHeader,
  EmptyState,
  ErrorState,
  Field,
  KeyValue,
  Loading,
  Mono,
  PageHeader,
  Select,
  SyntheticBadge,
  Table,
  Td,
  Tr,
} from "@/components/ui";
import { ConceptGraphPayload, ResponseDetail, api } from "@/lib/api";
import { groupModels, modelKey, parseModelKey, useModels, useQuestions, useResponses } from "@/lib/hooks";

const IMPORTANCE_STYLE: Record<string, { bg: string; border: string }> = {
  core: { bg: "#eef3f1", border: "#2f5d50" },
  supporting: { bg: "#fdf6e7", border: "#8a5a00" },
  optional: { bg: "#fbfbfa", border: "#d2d1cc" },
};

/**
 * Lay the graph out in dependency layers.
 *
 * A layered layout is the right choice here because the thing we want to see is
 * teaching order: depth in the graph *is* the pedagogical sequence.
 */
function layout(payload: ConceptGraphPayload): { nodes: Node[]; edges: Edge[] } {
  const depth = new Map<string, number>();
  for (const id of payload.teaching_order ?? []) depth.set(id, 0);

  // Longest-path depth, iterated to a fixed point over a small graph.
  const prerequisiteEdges = (payload.edges ?? []).filter((e) =>
    ["prerequisite_for", "motivates"].includes(e.relation),
  );
  for (let pass = 0; pass < (payload.nodes?.length ?? 0) + 1; pass += 1) {
    let changed = false;
    for (const edge of prerequisiteEdges) {
      const next = (depth.get(edge.source) ?? 0) + 1;
      if (next > (depth.get(edge.target) ?? 0)) {
        depth.set(edge.target, next);
        changed = true;
      }
    }
    if (!changed) break;
  }

  const byDepth = new Map<number, string[]>();
  for (const node of payload.nodes ?? []) {
    const d = depth.get(node.id) ?? 0;
    byDepth.set(d, [...(byDepth.get(d) ?? []), node.id]);
  }

  const nodes: Node[] = (payload.nodes ?? []).map((node) => {
    const d = depth.get(node.id) ?? 0;
    const column = byDepth.get(d) ?? [];
    const index = column.indexOf(node.id);
    const style = IMPORTANCE_STYLE[node.importance ?? "core"] ?? IMPORTANCE_STYLE.core;
    return {
      id: node.id,
      position: { x: d * 230, y: index * 92 - ((column.length - 1) * 92) / 2 },
      sourcePosition: Position.Right,
      targetPosition: Position.Left,
      data: {
        label: (
          <div className="px-1 py-0.5 text-left">
            <div className="text-[11px] font-semibold leading-tight">{node.label}</div>
            <div className="mt-0.5 text-[9px] uppercase tracking-wide opacity-60">
              {node.importance ?? "core"}
              {node.explained_in_text === false ? " · not explained" : ""}
            </div>
          </div>
        ),
      },
      style: {
        background: style.bg,
        border: `1px solid ${style.border}`,
        borderRadius: 6,
        padding: 4,
        width: 190,
        fontSize: 11,
      },
    };
  });

  const edges: Edge[] = (payload.edges ?? []).map((edge, index) => ({
    id: `e${index}`,
    source: edge.source,
    target: edge.target,
    label: edge.relation === "prerequisite_for" ? undefined : edge.relation.replace(/_/g, " "),
    labelStyle: { fontSize: 9, fill: "#5c5c57" },
    animated: false,
    style: {
      stroke: edge.confidence === "low" ? "#d2d1cc" : "#8a8a82",
      strokeWidth: edge.confidence === "high" ? 1.6 : 1,
      strokeDasharray: edge.confidence === "low" ? "4 3" : undefined,
    },
    markerEnd: { type: MarkerType.ArrowClosed, width: 14, height: 14, color: "#8a8a82" },
  }));

  return { nodes, edges };
}

export default function AnalysisPage() {
  const searchParams = useSearchParams();
  const initialResponse = searchParams.get("response") ?? "";
  const queryClient = useQueryClient();

  const questions = useQuestions();
  const models = useModels();
  const [questionId, setQuestionId] = React.useState("");
  const [responseId, setResponseId] = React.useState(initialResponse);
  const [extractKey, setExtractKey] = React.useState("");

  const responses = useResponses({ questionId: questionId || undefined, enabled: !!questionId });

  React.useEffect(() => {
    if (!questionId && questions.data?.length && !initialResponse) {
      setQuestionId(questions.data[0].id);
    }
  }, [questions.data, questionId, initialResponse]);

  React.useEffect(() => {
    if (!responseId && responses.data?.length) setResponseId(responses.data[0].id);
  }, [responses.data, responseId]);

  const detail = useQuery({
    queryKey: ["response", responseId],
    queryFn: () => api.get<ResponseDetail>(`responses/${responseId}`),
    enabled: !!responseId,
  });

  const extract = useMutation({
    mutationFn: () => {
      const { provider, model_id } = parseModelKey(extractKey);
      return api.post<ConceptGraphPayload>(
        `responses/${responseId}/concept-graph?provider=${provider}&model_id=${encodeURIComponent(
          model_id,
        )}`,
      );
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["response", responseId] }),
  });

  const grouped = groupModels(models.data);
  const latestGraph: ConceptGraphPayload | undefined =
    extract.data ?? detail.data?.concept_graphs?.[detail.data.concept_graphs.length - 1];
  const analysis = detail.data?.transformation_meta?.analysis as Record<string, any> | undefined;
  const plan = detail.data?.transformation_meta?.plan as Record<string, any> | undefined;

  return (
    <>
      <PageHeader
        eyebrow="Pedagogical analysis"
        title="Concepts, prerequisites and comprehension risks"
        description="What an explanation assumes, what it introduces, and in what order. Inferred dependency relationships are hypotheses about conceptual structure, not established fact."
      />

      <Card className="mb-5">
        <div className="flex flex-wrap items-end gap-4 px-4 py-3">
          <Field label="Research question" className="min-w-[20rem] flex-1">
            <Select
              value={questionId}
              onChange={(e) => {
                setQuestionId(e.target.value);
                setResponseId("");
              }}
            >
              <option value="">All questions</option>
              {(questions.data ?? []).map((q) => (
                <option key={q.id} value={q.id}>
                  {q.text}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="Explanation" className="min-w-[18rem] flex-1">
            <Select value={responseId} onChange={(e) => setResponseId(e.target.value)}>
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
          <Field label="Extraction model">
            <Select value={extractKey} onChange={(e) => setExtractKey(e.target.value)}>
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
            variant="primary"
            disabled={!responseId || !extractKey}
            loading={extract.isPending}
            onClick={() => extract.mutate()}
          >
            Extract concept graph
          </Button>
        </div>
      </Card>

      {extract.error ? <ErrorState error={extract.error} /> : null}

      {!responseId ? (
        <EmptyState title="Select an explanation to analyse">
          Pick a question and one of its stored explanations, then extract a concept graph.
        </EmptyState>
      ) : detail.isLoading ? (
        <Loading label="Loading explanation" />
      ) : (
        <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_380px]">
          <div className="space-y-5">
            <Card>
              <CardHeader
                title="Concept dependency graph"
                description="Left to right is dependency depth: a concept sits to the right of everything it needs"
                actions={
                  <>
                    <Badge tone="warn" title="These edges are model-inferred.">
                      hypothesis
                    </Badge>
                    {latestGraph?.is_synthetic ? <SyntheticBadge /> : null}
                  </>
                }
              />
              {latestGraph && latestGraph.nodes.length > 0 ? (
                <>
                  <div className="h-[460px] border-b border-line">
                    <ReactFlowProvider>
                      <GraphCanvas payload={latestGraph} />
                    </ReactFlowProvider>
                  </div>
                  <div className="space-y-2 px-4 py-3">
                    <Caveat tone="warn">
                      <strong>These prerequisite relationships are AI-inferred hypotheses.</strong>{" "}
                      A validated concept dependency graph is normally expert-authored. Treat each
                      edge as a claim to check, not a fact. Low-confidence edges are drawn dashed.
                    </Caveat>
                    {(latestGraph.warnings ?? []).length > 0 ? (
                      <ul className="space-y-1 text-2xs text-warn">
                        {(latestGraph.warnings ?? []).map((warning, i) => (
                          <li key={i}>▲ {warning}</li>
                        ))}
                      </ul>
                    ) : null}
                  </div>
                </>
              ) : (
                <div className="px-4 py-8">
                  <EmptyState title="No concept graph yet">
                    Choose an extraction model above and run it. One model call per extraction.
                  </EmptyState>
                </div>
              )}
            </Card>

            {latestGraph?.sequencing_analysis ? (
              <Card>
                <CardHeader
                  title="Sequencing analysis"
                  description="Does the text introduce each prerequisite before the concept that needs it?"
                />
                <div className="px-4 py-3">
                  <KeyValue
                    columns={3}
                    items={[
                      {
                        label: "Dependencies checked",
                        value: latestGraph.sequencing_analysis.edges_checked,
                      },
                      {
                        label: "Order violations",
                        value: (
                          <span
                            className={
                              latestGraph.sequencing_analysis.violation_count > 0
                                ? "font-semibold text-warn"
                                : "font-semibold text-accent"
                            }
                          >
                            {latestGraph.sequencing_analysis.violation_count}
                          </span>
                        ),
                      },
                      {
                        label: "Violation rate",
                        value:
                          latestGraph.sequencing_analysis.violation_rate === null
                            ? "—"
                            : `${Math.round(
                                latestGraph.sequencing_analysis.violation_rate * 100,
                              )}%`,
                      },
                    ]}
                  />

                  {latestGraph.sequencing_analysis.violations.length > 0 ? (
                    <div className="mt-3">
                      <p className="mb-1.5 text-2xs font-semibold uppercase tracking-wide text-ink-faint">
                        Prerequisites introduced too late
                      </p>
                      <ul className="space-y-1.5">
                        {latestGraph.sequencing_analysis.violations.map((violation, i) => (
                          <li
                            key={i}
                            className="rounded border border-warn/25 bg-warn-soft px-2.5 py-2 text-2xs text-warn"
                          >
                            {violation.detail}
                          </li>
                        ))}
                      </ul>
                    </div>
                  ) : (
                    <Caveat className="mt-3">
                      No ordering violations against the inferred dependencies. That is evidence
                      about this text relative to this hypothesis, not proof the sequence is
                      optimal.
                    </Caveat>
                  )}

                  <div className="mt-4 grid gap-4 sm:grid-cols-2">
                    <div>
                      <p className="mb-1 text-2xs font-semibold uppercase tracking-wide text-ink-faint">
                        Derived teaching order
                      </p>
                      <ol className="space-y-0.5 text-2xs text-ink-muted">
                        {latestGraph.sequencing_analysis.teaching_order.map((id, i) => (
                          <li key={id}>
                            {i + 1}. <Mono>{id}</Mono>
                          </li>
                        ))}
                      </ol>
                    </div>
                    <div>
                      <p className="mb-1 text-2xs font-semibold uppercase tracking-wide text-ink-faint">
                        Order actually used in the text
                      </p>
                      <ol className="space-y-0.5 text-2xs text-ink-muted">
                        {latestGraph.sequencing_analysis.mention_order.map((id, i) => (
                          <li key={id}>
                            {i + 1}. <Mono>{id}</Mono>
                          </li>
                        ))}
                      </ol>
                    </div>
                  </div>

                  {latestGraph.sequencing_analysis.concepts_not_located_in_text.length > 0 ? (
                    <Caveat tone="warn" className="mt-3">
                      {latestGraph.sequencing_analysis.concepts_not_located_in_text.length} concept(s)
                      could not be located in the text by label match, so they are excluded from the
                      ordering check: {latestGraph.sequencing_analysis.concepts_not_located_in_text.join(", ")}.
                    </Caveat>
                  ) : null}
                </div>
              </Card>
            ) : null}
          </div>

          <div className="space-y-5">
            {latestGraph ? (
              <Card>
                <CardHeader title="Concepts" description={`${latestGraph.nodes.length} extracted`} />
                <Table head={["Concept", "Role", "Explained"]} className="rounded-none border-0">
                  {latestGraph.nodes.map((node) => (
                    <Tr key={node.id}>
                      <Td className="text-xs font-medium">{node.label}</Td>
                      <Td>
                        <Badge
                          tone={
                            node.importance === "core"
                              ? "accent"
                              : node.importance === "supporting"
                                ? "warn"
                                : "neutral"
                          }
                        >
                          {node.importance ?? "core"}
                        </Badge>
                      </Td>
                      <Td className="text-xs">
                        {node.explained_in_text === false ? (
                          <span className="text-warn">no</span>
                        ) : (
                          <span className="text-ink-faint">yes</span>
                        )}
                      </Td>
                    </Tr>
                  ))}
                </Table>
              </Card>
            ) : null}

            {analysis ? (
              <Card>
                <CardHeader
                  title="Stage A — input analysis"
                  description="Extracted when this variant was transformed"
                />
                <div className="space-y-3 px-4 py-3 text-xs">
                  <AnalysisList label="Primary claims" items={analysis.primary_claims} />
                  <AnalysisList label="Prerequisite concepts" items={analysis.prerequisite_concepts} />
                  <AnalysisList
                    label="Assumed prior knowledge"
                    items={analysis.assumed_prior_knowledge}
                  />
                  <AnalysisList
                    label="Missing intermediate steps"
                    items={analysis.missing_intermediate_steps}
                    tone="warn"
                  />
                  <AnalysisList
                    label="Possible sources of confusion"
                    items={analysis.possible_confusions}
                    tone="warn"
                  />
                  <AnalysisList
                    label="Ambiguous references"
                    items={analysis.ambiguous_references}
                    tone="warn"
                  />
                  {Array.isArray(analysis.technical_vocabulary) ? (
                    <div>
                      <p className="mb-1 text-2xs font-semibold uppercase tracking-wide text-ink-faint">
                        Technical vocabulary
                      </p>
                      <div className="flex flex-wrap gap-1">
                        {analysis.technical_vocabulary.map((term: any, i: number) => (
                          <Badge
                            key={i}
                            tone={term.explained_in_text ? "neutral" : "warn"}
                            title={term.explained_in_text ? "Explained in the text" : "Not explained"}
                          >
                            {term.term}
                          </Badge>
                        ))}
                      </div>
                    </div>
                  ) : null}
                </div>
              </Card>
            ) : null}

            {plan ? (
              <Card>
                <CardHeader
                  title="Stage B — selected teaching strategy"
                  description="Which techniques this explanation was judged to need"
                />
                <div className="space-y-3 px-4 py-3 text-xs">
                  <KeyValue
                    columns={1}
                    items={[
                      { label: "Learner level", value: plan.learner_level },
                      { label: "Detail level", value: plan.detail_level },
                      {
                        label: "Needs concrete example",
                        value: plan.needs_concrete_example ? "yes" : "no",
                      },
                      { label: "Needs analogy", value: plan.needs_analogy ? "yes" : "no" },
                      { label: "Needs diagram", value: plan.needs_diagram ? "yes" : "no" },
                    ]}
                  />
                  <AnalysisList label="Learning objectives" items={plan.learning_objectives} />
                  <AnalysisList label="Prerequisite order" items={plan.prerequisite_order} />
                  <AnalysisList label="Explanation sequence" items={plan.explanation_sequence} />
                  <AnalysisList
                    label="Techniques judged unnecessary here"
                    items={plan.techniques_not_needed}
                  />
                  <Caveat>
                    Not every explanation needs every technique. A plan that declines a technique is
                    a valid plan, and recording that decision is what makes the ablation
                    interpretable.
                  </Caveat>
                </div>
              </Card>
            ) : null}

            <Card>
              <CardHeader title="Next steps" />
              <div className="flex flex-wrap gap-2 px-4 py-3">
                <Link href={`/transform?response=${responseId}`}>
                  <Button size="sm" variant="primary">
                    Apply T2 sequencing
                  </Button>
                </Link>
                <Link href="/compare">
                  <Button size="sm">Back to comparison</Button>
                </Link>
              </div>
            </Card>
          </div>
        </div>
      )}
    </>
  );
}

function GraphCanvas({ payload }: { payload: ConceptGraphPayload }) {
  const { nodes, edges } = React.useMemo(() => layout(payload), [payload]);
  return (
    <ReactFlow
      nodes={nodes}
      edges={edges}
      fitView
      fitViewOptions={{ padding: 0.2 }}
      proOptions={{ hideAttribution: true }}
      nodesDraggable
      nodesConnectable={false}
      elementsSelectable
      minZoom={0.2}
      maxZoom={1.75}
    >
      <Background color="#e5e4e0" gap={18} size={1} />
      <Controls showInteractive={false} />
    </ReactFlow>
  );
}

function AnalysisList({
  label,
  items,
  tone = "neutral",
}: {
  label: string;
  items: unknown;
  tone?: "neutral" | "warn";
}) {
  if (!Array.isArray(items) || items.length === 0) return null;
  return (
    <div>
      <p className="mb-1 text-2xs font-semibold uppercase tracking-wide text-ink-faint">{label}</p>
      <ul className="space-y-1">
        {items.map((item, i) => (
          <li
            key={i}
            className={
              "flex gap-1.5 leading-relaxed " + (tone === "warn" ? "text-warn" : "text-ink-muted")
            }
          >
            <span aria-hidden className="text-ink-faint">
              ·
            </span>
            <span>{String(item)}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
