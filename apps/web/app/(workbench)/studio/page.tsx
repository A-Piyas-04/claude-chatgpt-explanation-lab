"use client";

/**
 * Experiment Studio — the primary workspace.
 *
 * The configuration surface changes with experiment type, because the five
 * experiments genuinely need different controls. Cost is estimated before the
 * run button becomes available, and an expensive batch needs an explicit
 * confirmation, so nobody discovers the bill afterwards.
 */

import { useMutation, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useRouter } from "next/navigation";
import React from "react";

import {
  Badge,
  Button,
  Caveat,
  Card,
  CardHeader,
  Checkbox,
  Disclosure,
  ErrorState,
  Field,
  Input,
  KeyValue,
  Loading,
  Mono,
  PageHeader,
  Select,
  Table,
  Td,
  Textarea,
  Tr,
  formatUsd,
} from "@/components/ui";
import { ApiError, Estimate, Experiment, ModelEntry, api } from "@/lib/api";
import {
  groupModels,
  modelKey,
  parseModelKey,
  useModels,
  useProfiles,
  usePrompts,
  useQuestions,
  useStrategies,
} from "@/lib/hooks";
import { useSystemStatus } from "@/components/shell";
import { TREATMENT_ORDER, TREATMENTS } from "@/lib/generated";

type ExperimentType =
  | "baseline"
  | "prompt_intervention"
  | "ablation"
  | "cross_model";

const TYPE_META: Record<
  ExperimentType,
  { title: string; blurb: string; experimentNumber: string }
> = {
  baseline: {
    experimentNumber: "Experiment 1",
    title: "Baseline model comparison",
    blurb:
      "Identical question, no pedagogical prompt, one arm per model. Captures default behaviour — adding any instruction here would contaminate the baseline.",
  },
  prompt_intervention: {
    experimentNumber: "Experiment 2",
    title: "Prompt intervention",
    blurb:
      "The three required conditions: default, a generic tutor prompt, and a structured pedagogical prompt that specifies a teaching process rather than a writing style.",
  },
  ablation: {
    experimentNumber: "Experiment 3",
    title: "Mechanism isolation / ablation",
    blurb:
      "One arm per treatment set, plus an untransformed control. Treatments are applied one at a time so each change is attributable.",
  },
  cross_model: {
    experimentNumber: "Experiment 4",
    title: "Cross-model transformation",
    blurb:
      "Generator × transformer grid, so improvement from the methodology can be told apart from improvement from the transforming model.",
  },
};

const TREATMENT_PRESETS: { label: string; sets: string[][] }[] = [
  {
    label: `Each treatment alone (${TREATMENT_ORDER.length} arms)`,
    // Derived from the generated contract, so adding a treatment in the
    // backend surfaces here without editing this file.
    sets: TREATMENTS.map((t) => [t.key]),
  },
  { label: "Language vs structure (T1, T5, T1+T5)", sets: [["T1"], ["T5"], ["T1", "T5"]] },
  { label: "Sequencing vs vocabulary (T1, T2)", sets: [["T1"], ["T2"]] },
  { label: "All treatments combined", sets: [["T1", "T2", "T3", "T4", "T5", "T6"]] },
];

export default function StudioPage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const status = useSystemStatus();

  const questions = useQuestions();
  const profiles = useProfiles();
  const models = useModels();
  const prompts = usePrompts();
  const strategies = useStrategies();

  const [type, setType] = React.useState<ExperimentType>("baseline");
  const [name, setName] = React.useState("");
  const [objective, setObjective] = React.useState("");
  const [hypothesis, setHypothesis] = React.useState("");
  const [questionIds, setQuestionIds] = React.useState<string[]>([]);
  const [profileId, setProfileId] = React.useState<string>("");
  const [sourceKeys, setSourceKeys] = React.useState<string[]>([]);
  const [transformKeys, setTransformKeys] = React.useState<string[]>([]);
  const [promptKeys, setPromptKeys] = React.useState<string[]>([]);
  const [treatmentSets, setTreatmentSets] = React.useState<string[][]>([["T1"]]);
  const [seed, setSeed] = React.useState(20261022);
  const [repetitions, setRepetitions] = React.useState(1);
  const [maxTokens, setMaxTokens] = React.useState(4096);
  const [temperature, setTemperature] = React.useState<string>("");
  const [effort, setEffort] = React.useState<string>("");
  const [runFidelity, setRunFidelity] = React.useState(true);
  const [runAnalysis, setRunAnalysis] = React.useState(true);
  const [runPlanning, setRunPlanning] = React.useState(true);
  const [buildGraph, setBuildGraph] = React.useState(false);
  const [includeControl, setIncludeControl] = React.useState(true);
  const [estimate, setEstimate] = React.useState<Estimate | null>(null);
  const [confirmCost, setConfirmCost] = React.useState(false);

  const grouped = groupModels(models.data);
  const selectedSources = sourceKeys.map(parseModelKey);
  const selectedTransforms = transformKeys.map(parseModelKey);

  // Any selected model that rejects temperature makes the control unavailable
  // for that arm. Say so here rather than letting the API silently drop it.
  const temperatureBlockers = React.useMemo(() => {
    const chosen = new Set([...sourceKeys, ...transformKeys]);
    return (models.data ?? []).filter(
      (m) => !m.supports_temperature && chosen.has(modelKey(m)),
    );
  }, [models.data, sourceKeys, transformKeys]);

  const buildSpec = React.useCallback(() => {
    const generation: Record<string, unknown> = { max_output_tokens: maxTokens };
    if (temperature !== "") generation.temperature = Number(temperature);
    if (effort !== "") generation.effort = effort;

    return {
      name: name.trim() || `${TYPE_META[type].title} — ${new Date().toLocaleDateString()}`,
      type,
      question_ids: questionIds,
      // Parsed here rather than closing over the derived arrays, so this
      // callback's dependencies are exactly the state it reads.
      source_models: sourceKeys.map(parseModelKey),
      transform_models: transformKeys.map(parseModelKey),
      prompt_template_keys: type === "prompt_intervention" ? promptKeys : [],
      treatment_sets: type === "ablation" || type === "cross_model" ? treatmentSets : [],
      learner_profile_id: profileId || null,
      generation_settings: generation,
      transform_settings: generation,
      objective,
      hypothesis,
      seed,
      repetitions,
      run_analysis: runAnalysis,
      run_planning: runPlanning,
      run_fidelity: runFidelity,
      build_concept_graph: buildGraph,
      include_untransformed_control: includeControl,
    };
  }, [
    name, type, questionIds, sourceKeys, transformKeys, promptKeys, treatmentSets,
    profileId, maxTokens, temperature, effort, objective, hypothesis, seed,
    repetitions, runAnalysis, runPlanning, runFidelity, buildGraph, includeControl,
  ]);

  const estimateMutation = useMutation({
    mutationFn: () => api.post<Estimate>("experiments/estimate", buildSpec()),
    onSuccess: (data) => {
      setEstimate(data);
      setConfirmCost(false);
    },
    onError: () => setEstimate(null),
  });

  const createAndRun = useMutation({
    mutationFn: async () => {
      const experiment = await api.post<Experiment>("experiments", buildSpec());
      await api.post(`experiments/${experiment.id}/run`, {
        confirm_cost: confirmCost || !estimate?.requires_confirmation,
        retry_failed_only: false,
      });
      return experiment;
    },
    onSuccess: (experiment) => {
      queryClient.invalidateQueries({ queryKey: ["experiments"] });
      queryClient.invalidateQueries({ queryKey: ["overview"] });
      router.push(`/experiments/${experiment.id}`);
    },
  });

  // Re-estimating is cheap and avoids running on a stale figure.
  React.useEffect(() => {
    setEstimate(null);
    setConfirmCost(false);
  }, [type, questionIds, sourceKeys, transformKeys, promptKeys, treatmentSets, repetitions,
      runAnalysis, runPlanning, runFidelity, buildGraph, includeControl]);

  React.useEffect(() => {
    if (type === "prompt_intervention" && promptKeys.length === 0 && prompts.data) {
      setPromptKeys([
        "condition_a_default",
        "condition_b_generic_tutor",
        "condition_c_structured_pedagogical",
      ]);
    }
  }, [type, prompts.data, promptKeys.length]);

  if (questions.isLoading || models.isLoading) return <Loading label="Loading configuration" />;
  if (questions.error) return <ErrorState error={questions.error} retry={questions.refetch} />;

  const canEstimate = questionIds.length > 0 && sourceKeys.length > 0;
  const needsTransformer = type === "cross_model";
  const specIsRunnable =
    canEstimate &&
    estimate !== null &&
    !estimate.exceeds_batch_limit &&
    (!estimate.requires_confirmation || confirmCost) &&
    (!needsTransformer || transformKeys.length > 0);

  return (
    <>
      <PageHeader
        eyebrow="Experiment studio"
        title={TYPE_META[type].title}
        description={TYPE_META[type].blurb}
        actions={
          <Link href="/library">
            <Button>Manage questions</Button>
          </Link>
        }
      />

      <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_360px]">
        <div className="space-y-5">
          {/* --- Experiment type ------------------------------------------- */}
          <Card>
            <CardHeader
              title="1 · Experiment"
              description="Which of the five experiments are you running?"
            />
            <div className="grid gap-2 px-4 py-3 sm:grid-cols-2">
              {(Object.keys(TYPE_META) as ExperimentType[]).map((key) => (
                <button
                  key={key}
                  onClick={() => setType(key)}
                  className={
                    "rounded-md border px-3 py-2.5 text-left transition " +
                    (type === key
                      ? "border-accent bg-accent-soft"
                      : "border-line hover:border-line-strong hover:bg-canvas")
                  }
                >
                  <span className="flex items-center gap-2">
                    <Badge tone={type === key ? "accent" : "neutral"}>
                      {TYPE_META[key].experimentNumber}
                    </Badge>
                  </span>
                  <span className="mt-1.5 block text-sm font-medium">{TYPE_META[key].title}</span>
                </button>
              ))}
            </div>
            <div className="border-t border-line px-4 py-3">
              <Caveat>
                Experiment 5 (blind human comprehension testing) is created from existing answer
                variants in{" "}
                <Link href="/studies" className="underline">
                  Human evaluation
                </Link>
                , because it evaluates answers rather than generating them.
              </Caveat>
            </div>
          </Card>

          {/* --- Questions -------------------------------------------------- */}
          <Card>
            <CardHeader
              title="2 · Research questions"
              description="Use a matched set — the same questions across every condition"
              actions={
                <>
                  <Button
                    size="sm"
                    onClick={() => setQuestionIds((questions.data ?? []).slice(0, 5).map((q) => q.id))}
                  >
                    First 5
                  </Button>
                  <Button size="sm" onClick={() => setQuestionIds([])}>
                    Clear
                  </Button>
                </>
              }
            />
            <div className="max-h-72 overflow-y-auto px-4 py-3">
              <div className="space-y-2">
                {(questions.data ?? []).map((question) => (
                  <Checkbox
                    key={question.id}
                    checked={questionIds.includes(question.id)}
                    onChange={(checked) =>
                      setQuestionIds((prev) =>
                        checked ? [...prev, question.id] : prev.filter((id) => id !== question.id),
                      )
                    }
                    label={question.text}
                    description={
                      <>
                        {question.domain.replace(/_/g, " ")} · difficulty:{" "}
                        {question.conceptual_difficulty} · {question.factual_checklist.length}{" "}
                        checklist claim(s)
                      </>
                    }
                  />
                ))}
              </div>
            </div>
            <div className="border-t border-line px-4 py-2.5">
              <p className="text-xs text-ink-muted">
                {questionIds.length} selected. Questions differ in conceptual difficulty, so
                compare conditions within a question rather than averaging across them.
              </p>
            </div>
          </Card>

          {/* --- Models ------------------------------------------------------ */}
          <Card>
            <CardHeader
              title="3 · Models"
              description={
                needsTransformer
                  ? "Source and transformation models are configured separately on purpose"
                  : "One arm per selected source model"
              }
            />
            <div className="space-y-4 px-4 py-3">
              <ModelPicker
                label="Source models — generate the explanation"
                grouped={grouped}
                selected={sourceKeys}
                onChange={setSourceKeys}
              />
              {(type === "ablation" || type === "cross_model") ? (
                <ModelPicker
                  label={
                    needsTransformer
                      ? "Transformation models — apply the treatments"
                      : "Transformation model (defaults to the source model if left empty)"
                  }
                  grouped={grouped}
                  selected={transformKeys}
                  onChange={setTransformKeys}
                  hint={
                    needsTransformer
                      ? "Every generator × transformer pair becomes a condition, which is what lets you separate the methodology's effect from the transforming model's capability."
                      : undefined
                  }
                />
              ) : null}
            </div>
          </Card>

          {/* --- Prompts / treatments ---------------------------------------- */}
          {type === "prompt_intervention" ? (
            <Card>
              <CardHeader
                title="4 · Prompt conditions"
                description="All three required conditions must be present"
              />
              <div className="space-y-2 px-4 py-3">
                {(prompts.data ?? []).map((template) => {
                  const active = template.versions.find((v) => v.is_active) ?? template.versions[0];
                  return (
                    <Checkbox
                      key={template.key}
                      checked={promptKeys.includes(template.key)}
                      onChange={(checked) =>
                        setPromptKeys((prev) =>
                          checked ? [...prev, template.key] : prev.filter((k) => k !== template.key),
                        )
                      }
                      label={
                        <span className="flex flex-wrap items-center gap-2">
                          {template.name}
                          <Badge>v{active?.version ?? 1}</Badge>
                          {template.is_builtin ? <Badge>built-in</Badge> : null}
                        </span>
                      }
                      description={template.description}
                    />
                  );
                })}
              </div>
              <div className="border-t border-line px-4 py-3">
                <Caveat>
                  Prompt templates are versioned. Each response stores the exact rendered prompt,
                  so editing a template later cannot rewrite the history of a completed experiment.{" "}
                  <Link href="/library" className="underline">
                    Edit templates
                  </Link>
                  .
                </Caveat>
              </div>
            </Card>
          ) : null}

          {type === "ablation" || type === "cross_model" ? (
            <Card>
              <CardHeader
                title="4 · Treatments"
                description="Each set becomes one condition"
                actions={
                  <Select
                    className="w-auto text-xs"
                    value=""
                    onChange={(e) => {
                      const preset = TREATMENT_PRESETS[Number(e.target.value)];
                      if (preset) setTreatmentSets(preset.sets);
                    }}
                  >
                    <option value="">Load a preset…</option>
                    {TREATMENT_PRESETS.map((preset, i) => (
                      <option key={preset.label} value={i}>
                        {preset.label}
                      </option>
                    ))}
                  </Select>
                }
              />
              <div className="px-4 py-3">
                <TreatmentSetEditor
                  sets={treatmentSets}
                  onChange={setTreatmentSets}
                  strategies={strategies.data ?? []}
                />
                <div className="mt-3">
                  <Checkbox
                    checked={includeControl}
                    onChange={setIncludeControl}
                    label="Include an untransformed control arm"
                    description="Without a control, an improvement cannot be distinguished from the baseline."
                  />
                </div>
              </div>
              <div className="border-t border-line px-4 py-3">
                <Caveat>
                  Not every explanation needs every technique — a short, already-clear answer may
                  need none. Treatments are applied one at a time in a fixed documented order
                  (T3 → T4 → T6 → T1 → T2 → T5) and each step&apos;s change is recorded separately.
                </Caveat>
              </div>
            </Card>
          ) : null}

          {/* --- Audience and settings --------------------------------------- */}
          <Card>
            <CardHeader title="5 · Audience and generation settings" />
            <div className="grid gap-4 px-4 py-3 sm:grid-cols-2">
              <Field
                label="Learner profile"
                hint="Supplied to pedagogical prompts and to the T6 audience treatment."
              >
                <Select value={profileId} onChange={(e) => setProfileId(e.target.value)}>
                  <option value="">None (no audience specified)</option>
                  {(profiles.data ?? []).map((profile) => (
                    <option key={profile.id} value={profile.id}>
                      {profile.name}
                    </option>
                  ))}
                </Select>
              </Field>
              <Field label="Max output tokens">
                <Input
                  type="number"
                  min={256}
                  max={32000}
                  value={maxTokens}
                  onChange={(e) => setMaxTokens(Number(e.target.value))}
                />
              </Field>
              <Field
                label="Effort"
                hint="Reasoning depth on models that support it. Recorded per response."
              >
                <Select value={effort} onChange={(e) => setEffort(e.target.value)}>
                  <option value="">Provider default</option>
                  {["low", "medium", "high", "xhigh", "max"].map((level) => (
                    <option key={level} value={level}>
                      {level}
                    </option>
                  ))}
                </Select>
              </Field>
              <Field
                label="Temperature"
                hint={
                  temperatureBlockers.length > 0
                    ? "Some selected models reject this parameter — see the warning below."
                    : "Leave empty to omit. Current frontier models reject it."
                }
              >
                <Input
                  type="number"
                  step="0.1"
                  min={0}
                  max={2}
                  placeholder="omit"
                  value={temperature}
                  onChange={(e) => setTemperature(e.target.value)}
                />
              </Field>
              <Field label="Randomisation seed" hint="Recorded for reproducibility.">
                <Input type="number" value={seed} onChange={(e) => setSeed(Number(e.target.value))} />
              </Field>
              <Field
                label="Replicates per cell"
                hint="More than one measures response variability for the same condition."
              >
                <Input
                  type="number"
                  min={1}
                  max={10}
                  value={repetitions}
                  onChange={(e) => setRepetitions(Number(e.target.value))}
                />
              </Field>
            </div>

            {temperature !== "" && temperatureBlockers.length > 0 ? (
              <div className="border-t border-line px-4 py-3">
                <Caveat tone="warn">
                  <strong>Conditions will not be temperature-matched.</strong> These selected models
                  reject the temperature parameter:{" "}
                  {temperatureBlockers.map((m) => m.model_id).join(", ")}. The platform omits it for
                  them and records the omission on every affected response, rather than pretending
                  the configurations are identical. To run a genuinely temperature-controlled
                  condition, use a model whose capability record allows it.
                </Caveat>
              </div>
            ) : null}

            {(type === "ablation" || type === "cross_model") ? (
              <div className="space-y-2 border-t border-line px-4 py-3">
                <Checkbox
                  checked={runAnalysis}
                  onChange={setRunAnalysis}
                  label="Stage A — input analysis"
                  description="Extract concepts, prerequisites, vocabulary and gaps before transforming."
                />
                <Checkbox
                  checked={runPlanning}
                  onChange={setRunPlanning}
                  label="Stage B — pedagogical planning"
                  description="Decide which techniques this explanation actually needs."
                />
                <Checkbox
                  checked={runFidelity}
                  onChange={setRunFidelity}
                  label="Stage D — fidelity verification"
                  description="Deterministic checks always run; this adds the LLM reviewer. Strongly recommended."
                />
                <Checkbox
                  checked={buildGraph}
                  onChange={setBuildGraph}
                  label="Extract a concept dependency graph"
                  description="One extra call per run. Inferred edges are hypotheses, not ground truth."
                />
              </div>
            ) : null}
          </Card>

          <Card>
            <CardHeader title="6 · Record keeping" description="Stored with the experiment and every export" />
            <div className="space-y-4 px-4 py-3">
              <Field label="Experiment name">
                <Input
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder={`${TYPE_META[type].title} — ${new Date().toLocaleDateString()}`}
                />
              </Field>
              <Field label="Objective" hint="What question is this run meant to answer?">
                <Textarea
                  rows={2}
                  value={objective}
                  onChange={(e) => setObjective(e.target.value)}
                  placeholder="Compare default explanation styles for a caching question at intermediate level."
                />
              </Field>
              <Field label="Hypothesis" hint="State it before running, so the result can disconfirm it.">
                <Textarea
                  rows={2}
                  value={hypothesis}
                  onChange={(e) => setHypothesis(e.target.value)}
                  placeholder="H2 — prerequisite-aware sequencing improves comprehension without simplifying vocabulary."
                />
              </Field>
            </div>
          </Card>
        </div>

        {/* --- Run panel ------------------------------------------------------ */}
        <div className="space-y-5 lg:sticky lg:top-20 lg:self-start">
          <Card>
            <CardHeader title="Run controls" description="Cost is estimated before anything executes" />
            <div className="space-y-3 px-4 py-3">
              <KeyValue
                columns={1}
                items={[
                  { label: "Questions", value: questionIds.length },
                  { label: "Source models", value: sourceKeys.length },
                  ...(type === "cross_model" || type === "ablation"
                    ? [{ label: "Transform models", value: transformKeys.length || "same as source" }]
                    : []),
                  ...(type === "prompt_intervention"
                    ? [{ label: "Prompt conditions", value: promptKeys.length }]
                    : []),
                  ...(type === "ablation" || type === "cross_model"
                    ? [{ label: "Treatment sets", value: treatmentSets.length }]
                    : []),
                  { label: "Replicates", value: repetitions },
                ]}
              />

              <Button
                variant="secondary"
                className="w-full"
                disabled={!canEstimate}
                loading={estimateMutation.isPending}
                onClick={() => estimateMutation.mutate()}
              >
                Estimate cost and request count
              </Button>

              {estimateMutation.error ? (
                <ErrorState error={estimateMutation.error} />
              ) : null}

              {estimate ? (
                <div className="space-y-3 rounded-md border border-line bg-canvas px-3 py-3">
                  <KeyValue
                    columns={1}
                    items={[
                      { label: "Conditions", value: estimate.condition_count },
                      { label: "Runs", value: estimate.total_runs },
                      { label: "Model calls", value: estimate.total_model_calls },
                      {
                        label: "Estimated cost",
                        value: (
                          <span className="text-base font-semibold">
                            {estimate.demo_mode ? "$0.00 (demo mode)" : formatUsd(estimate.estimated_cost_usd)}
                          </span>
                        ),
                      },
                    ]}
                  />
                  <p className="text-2xs leading-relaxed text-ink-faint">{estimate.note}</p>

                  {estimate.exceeds_batch_limit ? (
                    <Caveat tone="danger">
                      {estimate.total_model_calls} calls exceeds the batch ceiling of{" "}
                      {estimate.max_batch_requests}. Reduce questions, conditions or replicates, or
                      raise <Mono>MAX_BATCH_REQUESTS</Mono>.
                    </Caveat>
                  ) : null}

                  {estimate.requires_confirmation && !estimate.demo_mode ? (
                    <div className="rounded-md border border-warn/30 bg-warn-soft px-3 py-2.5">
                      <Checkbox
                        checked={confirmCost}
                        onChange={setConfirmCost}
                        label={`I confirm this batch, estimated at ${formatUsd(
                          estimate.estimated_cost_usd,
                        )}`}
                        description={`Above the ${formatUsd(
                          estimate.confirmation_threshold_usd,
                        )} confirmation threshold.`}
                      />
                    </div>
                  ) : null}

                  <Disclosure summary={`Per-condition breakdown (${estimate.per_condition.length})`}>
                    <Table head={["Condition", "Calls", "Est. cost"]} className="border-0">
                      {estimate.per_condition.map((row) => (
                        <Tr key={row.label}>
                          <Td className="text-xs">{row.label}</Td>
                          <Td className="tabular-nums text-xs">{row.total_calls}</Td>
                          <Td className="tabular-nums text-xs">{formatUsd(row.estimated_cost_usd)}</Td>
                        </Tr>
                      ))}
                    </Table>
                  </Disclosure>
                </div>
              ) : null}

              <Button
                variant="primary"
                className="w-full"
                disabled={!specIsRunnable}
                loading={createAndRun.isPending}
                onClick={() => createAndRun.mutate()}
              >
                Create and run experiment
              </Button>

              {createAndRun.error ? (
                <ErrorState error={createAndRun.error} />
              ) : null}

              {!canEstimate ? (
                <p className="text-2xs text-ink-faint">
                  Select at least one question and one source model to estimate.
                </p>
              ) : !estimate ? (
                <p className="text-2xs text-ink-faint">
                  Estimate first — the run button stays disabled until the cost is known.
                </p>
              ) : null}

              {needsTransformer && transformKeys.length === 0 ? (
                <Caveat tone="warn">
                  A cross-model experiment needs at least one transformation model, chosen
                  separately from the source model.
                </Caveat>
              ) : null}
            </div>
          </Card>

          {status.data ? (
            <Card>
              <CardHeader title="Providers" />
              <div className="space-y-2 px-4 py-3">
                {status.data.provider_status.map((provider) => (
                  <div key={provider.provider} className="flex items-center justify-between text-sm">
                    <span className="font-medium">{provider.provider}</span>
                    <Badge tone={provider.configured ? "success" : "synthetic"}>
                      {provider.configured ? "live" : "demo fixtures"}
                    </Badge>
                  </div>
                ))}
                <p className="pt-1 text-2xs leading-relaxed text-ink-faint">
                  Model prices and capability flags were verified on{" "}
                  {status.data.pricing_verified_on}. Refresh the catalogue from{" "}
                  <Link href="/library" className="underline">
                    the library
                  </Link>{" "}
                  to reconcile against each provider&apos;s live model list.
                </p>
              </div>
            </Card>
          ) : null}
        </div>
      </div>
    </>
  );
}

function ModelPicker({
  label,
  grouped,
  selected,
  onChange,
  hint,
}: {
  label: string;
  grouped: Map<string, ModelEntry[]>;
  selected: string[];
  onChange: (keys: string[]) => void;
  hint?: string;
}) {
  return (
    <Field label={label} hint={hint}>
      <div className="space-y-3 rounded-md border border-line bg-canvas px-3 py-2.5">
        {[...grouped.entries()].map(([provider, entries]) => (
          <div key={provider}>
            <p className="mb-1.5 text-2xs font-semibold uppercase tracking-wide text-ink-faint">
              {provider}
            </p>
            <div className="space-y-1.5">
              {entries.map((model) => {
                const key = modelKey(model);
                return (
                  <Checkbox
                    key={key}
                    disabled={!model.is_enabled}
                    checked={selected.includes(key)}
                    onChange={(checked) =>
                      onChange(checked ? [...selected, key] : selected.filter((k) => k !== key))
                    }
                    label={
                      <span className="flex flex-wrap items-center gap-1.5">
                        <span className="font-mono text-xs">{model.model_id}</span>
                        {model.input_cost_per_mtok !== null ? (
                          <Badge title="Input / output price per million tokens">
                            ${model.input_cost_per_mtok}/${model.output_cost_per_mtok}
                          </Badge>
                        ) : (
                          <Badge tone="warn">no pricing</Badge>
                        )}
                        {!model.supports_temperature ? (
                          <Badge tone="warn" title="This model rejects the temperature parameter.">
                            no temperature
                          </Badge>
                        ) : null}
                        {!model.is_enabled ? <Badge tone="danger">disabled</Badge> : null}
                      </span>
                    }
                  />
                );
              })}
            </div>
          </div>
        ))}
      </div>
    </Field>
  );
}

function TreatmentSetEditor({
  sets,
  onChange,
  strategies,
}: {
  sets: string[][];
  onChange: (sets: string[][]) => void;
  strategies: { key: string; name: string; boundary_note: string; description: string }[];
}) {
  // Prefer live data (it carries the researcher's own versions); fall back to
  // the generated contract rather than a hardcoded list.
  const allKeys: string[] = strategies.length
    ? strategies.map((s) => s.key)
    : TREATMENT_ORDER;

  return (
    <div className="space-y-2">
      {sets.map((set, index) => (
        <div key={index} className="rounded-md border border-line bg-canvas px-3 py-2.5">
          <div className="mb-2 flex items-center justify-between">
            <span className="text-xs font-medium">
              Condition {index + 1}: {set.length ? set.join(" + ") : "none selected"}
            </span>
            <Button
              size="sm"
              variant="ghost"
              onClick={() => onChange(sets.filter((_, i) => i !== index))}
            >
              Remove
            </Button>
          </div>
          <div className="flex flex-wrap gap-1.5">
            {allKeys.map((key) => {
              const strategy = strategies.find((s) => s.key === key);
              const active = set.includes(key);
              return (
                <button
                  key={key}
                  title={strategy ? `${strategy.name}. ${strategy.boundary_note}` : key}
                  onClick={() =>
                    onChange(
                      sets.map((current, i) =>
                        i === index
                          ? active
                            ? current.filter((k) => k !== key)
                            : [...current, key]
                          : current,
                      ),
                    )
                  }
                  className={
                    "rounded border px-2 py-1 text-2xs font-medium transition " +
                    (active
                      ? "border-accent bg-accent text-white"
                      : "border-line-strong bg-surface text-ink-muted hover:bg-canvas")
                  }
                >
                  {key}
                </button>
              );
            })}
          </div>
        </div>
      ))}
      <Button size="sm" onClick={() => onChange([...sets, []])}>
        Add condition
      </Button>
      {strategies.length > 0 ? (
        <Disclosure summary="What each treatment does, and what it must not do" className="mt-2">
          <dl className="space-y-3 text-xs">
            {strategies.map((strategy) => (
              <div key={strategy.key}>
                <dt className="font-semibold">
                  {strategy.key} — {strategy.name}
                </dt>
                <dd className="mt-0.5 text-ink-muted">{strategy.description}</dd>
                <dd className="mt-0.5 text-ink-faint">
                  <span className="font-medium">Boundary:</span> {strategy.boundary_note}
                </dd>
              </div>
            ))}
          </dl>
        </Disclosure>
      ) : null}
    </div>
  );
}
