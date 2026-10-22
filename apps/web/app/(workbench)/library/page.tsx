"use client";

/**
 * Research library: the persisted research objects.
 *
 * Questions (with their reviewed factual checklists), learner profiles, the
 * versioned prompt templates, the transformation strategies with their
 * boundaries, the model catalogue with its capability records, and generated
 * reports.
 */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
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
  Table,
  Tabs,
  Td,
  Textarea,
  Tr,
} from "@/components/ui";
import { ModelEntry, PromptTemplate, Question, api } from "@/lib/api";
import { useModels, useProfiles, usePrompts, useQuestions, useStrategies } from "@/lib/hooks";

export default function LibraryPage() {
  const [tab, setTab] = React.useState("questions");
  const questions = useQuestions();
  const profiles = useProfiles();
  const prompts = usePrompts();
  const strategies = useStrategies();
  const models = useModels();

  const reports = useQuery({
    queryKey: ["reports"],
    queryFn: () =>
      api.get<
        {
          id: string;
          title: string;
          kind: string;
          experiment_id: string | null;
          study_id: string | null;
          contains_synthetic_data: boolean;
          created_at: string;
        }[]
      >("reports"),
  });

  return (
    <>
      <PageHeader
        eyebrow="Research library"
        title="Persisted research objects"
        description="Questions, audiences, versioned prompts, transformation strategies, the model catalogue and generated reports."
      />

      <Tabs
        tabs={[
          { id: "questions", label: "Questions", count: questions.data?.length },
          { id: "profiles", label: "Learner profiles", count: profiles.data?.length },
          { id: "prompts", label: "Prompt templates", count: prompts.data?.length },
          { id: "strategies", label: "Transformations", count: strategies.data?.length },
          { id: "models", label: "Model catalogue", count: models.data?.length },
          { id: "reports", label: "Reports", count: reports.data?.length },
        ]}
        active={tab}
        onChange={setTab}
      />

      {tab === "questions" ? <QuestionsTab /> : null}
      {tab === "profiles" ? (
        profiles.isLoading ? (
          <Loading />
        ) : (
          <div className="space-y-3">
            {(profiles.data ?? []).map((profile) => (
              <Card key={profile.id}>
                <CardHeader
                  title={
                    <span className="flex flex-wrap items-center gap-2">
                      {profile.name}
                      <Badge tone="accent">{profile.level}</Badge>
                      {profile.is_builtin ? <Badge>built-in</Badge> : null}
                    </span>
                  }
                  description={profile.description}
                />
                <div className="px-4 py-3">
                  <KeyValue
                    columns={2}
                    items={[
                      {
                        label: "Can be assumed to know",
                        value: profile.assumed_prior_knowledge.join(", ") || "—",
                      },
                      {
                        label: "Probably unfamiliar with",
                        value: profile.unfamiliar_with.join(", ") || "—",
                      },
                    ]}
                  />
                </div>
              </Card>
            ))}
            <Caveat>
              Learner level is an experimental factor, not a setting to optimise. Scaffolding that
              helps a beginner can hurt an expert (the expertise-reversal effect), so a single
              &ldquo;best&rdquo; explanation is not expected to exist.
            </Caveat>
          </div>
        )
      ) : null}
      {tab === "prompts" ? <PromptsTab /> : null}
      {tab === "strategies" ? (
        strategies.isLoading ? (
          <Loading />
        ) : (
          <div className="space-y-3">
            {(strategies.data ?? []).map((strategy) => {
              const active = strategy.versions.find((v) => v.is_active) ?? strategy.versions[0];
              return (
                <Card key={strategy.id}>
                  <CardHeader
                    title={
                      <span className="flex flex-wrap items-center gap-2">
                        <Badge tone="accent">{strategy.key}</Badge>
                        {strategy.name}
                        <Badge>v{active?.version ?? 1}</Badge>
                        <Badge>{strategy.category}</Badge>
                      </span>
                    }
                    description={strategy.description}
                  />
                  <div className="space-y-3 px-4 py-3">
                    <div>
                      <p className="text-2xs font-semibold uppercase tracking-wide text-ink-faint">
                        Boundary — what this treatment must not do
                      </p>
                      <p className="mt-1 text-xs leading-relaxed text-ink-muted">
                        {strategy.boundary_note}
                      </p>
                    </div>
                    {active?.default_params && Object.keys(active.default_params).length > 0 ? (
                      <div>
                        <p className="text-2xs font-semibold uppercase tracking-wide text-ink-faint">
                          Parameters
                        </p>
                        <Mono>{JSON.stringify(active.default_params)}</Mono>
                      </div>
                    ) : null}
                    <Disclosure summary="Versioned instruction template">
                      <pre className="max-h-96 overflow-auto whitespace-pre-wrap rounded border border-line bg-canvas p-3 font-mono text-2xs leading-relaxed">
                        {active?.instruction_template}
                      </pre>
                    </Disclosure>
                  </div>
                </Card>
              );
            })}
            <Caveat>
              Treatment boundaries are enforced in two places: the instruction tells the model what
              not to do, and Stage D checks the output for boundary violations. Without both, a
              &ldquo;vocabulary only&rdquo; variant that also restructured the text would silently
              invalidate the ablation.
            </Caveat>
          </div>
        )
      ) : null}
      {tab === "models" ? <ModelsTab /> : null}
      {tab === "reports" ? (
        reports.isLoading ? (
          <Loading />
        ) : (reports.data ?? []).length === 0 ? (
          <EmptyState title="No reports generated yet">
            Generate one from an experiment or a study page.
          </EmptyState>
        ) : (
          <Table head={["Report", "Kind", "Created", "Source"]}>
            {(reports.data ?? []).map((report) => (
              <Tr key={report.id}>
                <Td>
                  <span className="flex flex-wrap items-center gap-2 text-xs font-medium">
                    {report.title}
                    {report.contains_synthetic_data ? (
                      <Badge tone="synthetic">contains synthetic data</Badge>
                    ) : null}
                  </span>
                </Td>
                <Td className="text-xs">{report.kind.replace(/_/g, " ")}</Td>
                <Td className="text-2xs text-ink-faint">
                  {new Date(report.created_at).toLocaleString()}
                </Td>
                <Td className="text-xs">
                  {report.experiment_id ? (
                    <Link href={`/experiments/${report.experiment_id}`} className="text-accent underline">
                      experiment
                    </Link>
                  ) : report.study_id ? (
                    <Link href={`/studies/${report.study_id}`} className="text-accent underline">
                      study
                    </Link>
                  ) : (
                    "—"
                  )}
                </Td>
              </Tr>
            ))}
          </Table>
        )
      ) : null}
    </>
  );
}

function QuestionsTab() {
  const queryClient = useQueryClient();
  const questions = useQuestions();
  const [search, setSearch] = React.useState("");
  const [adding, setAdding] = React.useState(false);
  const [draft, setDraft] = React.useState({
    text: "",
    domain: "software_engineering",
    topic: "",
    conceptual_difficulty: "moderate",
    checklist: "",
  });

  const create = useMutation({
    mutationFn: () =>
      api.post<Question>("questions", {
        text: draft.text,
        domain: draft.domain,
        topic: draft.topic,
        conceptual_difficulty: draft.conceptual_difficulty,
        factual_checklist: draft.checklist
          .split("\n")
          .map((line) => line.trim())
          .filter(Boolean),
        checklist_reviewed_by: "researcher",
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["questions"] });
      setAdding(false);
      setDraft({ text: "", domain: "software_engineering", topic: "", conceptual_difficulty: "moderate", checklist: "" });
    },
  });

  const duplicate = useMutation({
    mutationFn: (id: string) => api.post(`questions/${id}/duplicate`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["questions"] }),
  });

  const filtered = (questions.data ?? []).filter((q) =>
    search ? q.text.toLowerCase().includes(search.toLowerCase()) : true,
  );

  return (
    <>
      <div className="mb-4 flex flex-wrap items-end gap-3">
        <Field label="Search" className="min-w-[18rem] flex-1">
          <Input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Filter questions…"
          />
        </Field>
        <Button variant="primary" onClick={() => setAdding((open) => !open)}>
          {adding ? "Cancel" : "Add question"}
        </Button>
      </div>

      {adding ? (
        <Card className="mb-5">
          <CardHeader
            title="New research question"
            description="The factual checklist is the set of essential claims a correct explanation should contain. It drives coverage diagnostics and the fidelity audit."
          />
          <div className="grid gap-4 px-4 py-3 sm:grid-cols-2">
            <Field label="Question" className="sm:col-span-2">
              <Textarea
                rows={2}
                value={draft.text}
                onChange={(e) => setDraft({ ...draft, text: e.target.value })}
                placeholder="How does a write-ahead log make a database crash-safe?"
              />
            </Field>
            <Field label="Domain">
              <Input
                value={draft.domain}
                onChange={(e) => setDraft({ ...draft, domain: e.target.value })}
              />
            </Field>
            <Field label="Topic">
              <Input
                value={draft.topic}
                onChange={(e) => setDraft({ ...draft, topic: e.target.value })}
              />
            </Field>
            <Field
              label="Conceptual difficulty"
              hint="Recorded because questions are not equally hard; do not average across them."
            >
              <Select
                value={draft.conceptual_difficulty}
                onChange={(e) => setDraft({ ...draft, conceptual_difficulty: e.target.value })}
              >
                <option value="low">low</option>
                <option value="moderate">moderate</option>
                <option value="high">high</option>
                <option value="unrated">unrated</option>
              </Select>
            </Field>
            <Field
              label="Factual checklist — one claim per line"
              className="sm:col-span-2"
              hint="Reviewed claims a correct explanation should include."
            >
              <Textarea
                rows={6}
                value={draft.checklist}
                onChange={(e) => setDraft({ ...draft, checklist: e.target.value })}
                placeholder={"Changes are written to a log before the data pages.\nThe log entry is durable before the transaction commits."}
              />
            </Field>
          </div>
          <div className="flex items-center gap-3 border-t border-line px-4 py-3">
            <Button
              variant="primary"
              disabled={draft.text.trim().length < 5}
              loading={create.isPending}
              onClick={() => create.mutate()}
            >
              Create question
            </Button>
            {create.error ? <ErrorState error={create.error} /> : null}
          </div>
        </Card>
      ) : null}

      {questions.isLoading ? (
        <Loading />
      ) : (
        <div className="space-y-3">
          {filtered.map((question) => (
            <Card key={question.id}>
              <CardHeader
                title={question.text}
                description={
                  <span className="flex flex-wrap items-center gap-2">
                    <Badge>{question.domain.replace(/_/g, " ")}</Badge>
                    {question.topic ? <Badge>{question.topic}</Badge> : null}
                    <Badge
                      tone={
                        question.conceptual_difficulty === "high"
                          ? "warn"
                          : question.conceptual_difficulty === "low"
                            ? "neutral"
                            : "accent"
                      }
                    >
                      difficulty: {question.conceptual_difficulty}
                    </Badge>
                    {question.is_seed ? <Badge>seed</Badge> : null}
                  </span>
                }
                actions={
                  <>
                    <Button size="sm" onClick={() => duplicate.mutate(question.id)}>
                      Duplicate
                    </Button>
                    <Link href={`/compare?question=${question.id}`}>
                      <Button size="sm">Answers</Button>
                    </Link>
                  </>
                }
              />
              {question.factual_checklist.length > 0 ? (
                <div className="px-4 py-3">
                  <Disclosure
                    summary={`Factual checklist — ${question.factual_checklist.length} claim(s), reviewed by ${
                      question.checklist_reviewed_by ?? "nobody recorded"
                    }`}
                  >
                    <ol className="space-y-1 text-xs text-ink-muted">
                      {question.factual_checklist.map((claim, i) => (
                        <li key={i} className="flex gap-2">
                          <span className="text-ink-faint">{i + 1}.</span>
                          <span>{claim}</span>
                        </li>
                      ))}
                    </ol>
                  </Disclosure>
                </div>
              ) : (
                <div className="px-4 py-3">
                  <Caveat tone="warn">
                    No factual checklist. Coverage diagnostics and checklist-aware fidelity checks
                    will be unavailable for this question.
                  </Caveat>
                </div>
              )}
            </Card>
          ))}
        </div>
      )}
    </>
  );
}

function PromptsTab() {
  const queryClient = useQueryClient();
  const prompts = usePrompts();
  const [editing, setEditing] = React.useState<string | null>(null);
  const [systemText, setSystemText] = React.useState("");
  const [userTemplate, setUserTemplate] = React.useState("");
  const [changelog, setChangelog] = React.useState("");

  const addVersion = useMutation({
    mutationFn: (key: string) =>
      api.post<PromptTemplate>(`prompts/${key}/versions`, {
        system_text: systemText,
        user_template: userTemplate,
        changelog,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["prompts"] });
      setEditing(null);
      setChangelog("");
    },
  });

  if (prompts.isLoading) return <Loading />;

  return (
    <div className="space-y-3">
      <Caveat tone="accent">
        Editing a template appends a new version; earlier versions are immutable. Every response
        stores the exact rendered prompt it was generated from, so a completed experiment&apos;s
        record can never be changed by a later edit.
      </Caveat>

      {(prompts.data ?? []).map((template) => {
        const active = template.versions.find((v) => v.is_active) ?? template.versions[0];
        const isEditing = editing === template.key;
        return (
          <Card key={template.id}>
            <CardHeader
              title={
                <span className="flex flex-wrap items-center gap-2">
                  {template.name}
                  <Badge tone="accent">{template.condition.replace(/_/g, " ")}</Badge>
                  <Badge>v{active?.version ?? 1}</Badge>
                  <Badge>{template.versions.length} version(s)</Badge>
                  {template.is_builtin ? <Badge>built-in</Badge> : null}
                </span>
              }
              description={template.description}
              actions={
                <Button
                  size="sm"
                  onClick={() => {
                    if (isEditing) {
                      setEditing(null);
                    } else {
                      setEditing(template.key);
                      setSystemText(active?.system_text ?? "");
                      setUserTemplate(active?.user_template ?? "{question}");
                    }
                  }}
                >
                  {isEditing ? "Cancel" : "New version"}
                </Button>
              }
            />

            {isEditing ? (
              <div className="space-y-3 px-4 py-3">
                <Field
                  label="System prompt"
                  hint="Variables: {learner_level}, {learner_description}, {assumed_prior_knowledge}, {unfamiliar_with}, {domain}, {topic}"
                >
                  <Textarea
                    rows={14}
                    className="font-mono text-xs"
                    value={systemText}
                    onChange={(e) => setSystemText(e.target.value)}
                  />
                </Field>
                <Field label="User template" hint="{question} is wrapped as untrusted content.">
                  <Textarea
                    rows={2}
                    className="font-mono text-xs"
                    value={userTemplate}
                    onChange={(e) => setUserTemplate(e.target.value)}
                  />
                </Field>
                <Field label="Changelog">
                  <Input
                    value={changelog}
                    onChange={(e) => setChangelog(e.target.value)}
                    placeholder="What changed and why"
                  />
                </Field>
                <div className="flex items-center gap-3">
                  <Button
                    variant="primary"
                    loading={addVersion.isPending}
                    onClick={() => addVersion.mutate(template.key)}
                  >
                    Save as version {(active?.version ?? 1) + 1}
                  </Button>
                  {addVersion.error ? <ErrorState error={addVersion.error} /> : null}
                </div>
              </div>
            ) : (
              <div className="space-y-3 px-4 py-3">
                {active?.system_text ? (
                  <Disclosure summary="System prompt">
                    <pre className="max-h-96 overflow-auto whitespace-pre-wrap rounded border border-line bg-canvas p-3 font-mono text-2xs leading-relaxed">
                      {active.system_text}
                    </pre>
                  </Disclosure>
                ) : (
                  <Caveat>
                    No system prompt — this is the default condition, deliberately empty so it
                    captures default model behaviour. A prompt-injection guard sentence is still
                    appended in every condition, identically, and that deviation is recorded on
                    each response.
                  </Caveat>
                )}
                <Disclosure summary={`Version history (${template.versions.length})`}>
                  <Table head={["Version", "Active", "Changelog", "Created"]} className="border-0">
                    {template.versions
                      .slice()
                      .reverse()
                      .map((version) => (
                        <Tr key={version.id}>
                          <Td className="text-xs">v{version.version}</Td>
                          <Td className="text-xs">
                            {version.is_active ? <Badge tone="success">active</Badge> : "—"}
                          </Td>
                          <Td className="text-xs text-ink-muted">{version.changelog || "—"}</Td>
                          <Td className="text-2xs text-ink-faint">
                            {new Date(version.created_at).toLocaleString()}
                          </Td>
                        </Tr>
                      ))}
                  </Table>
                </Disclosure>
              </div>
            )}
          </Card>
        );
      })}
    </div>
  );
}

function ModelsTab() {
  const queryClient = useQueryClient();
  const models = useModels();

  const refresh = useMutation({
    mutationFn: () =>
      api.post<{
        providers: Record<string, { status: string; reason?: string; live_model_count?: number }>;
        discovered: string[];
        unverified: string[];
        note: string;
      }>("models/refresh"),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["models"] }),
  });

  const toggle = useMutation({
    mutationFn: ({ id, enabled }: { id: string; enabled: boolean }) =>
      api.patch<ModelEntry>(`models/${id}`, { is_enabled: enabled }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["models"] }),
  });

  if (models.isLoading) return <Loading />;

  return (
    <>
      <Card className="mb-4">
        <CardHeader
          title="Model catalogue"
          description="Capability records, not just names — because current models reject parameters older ones accepted"
          actions={
            <Button loading={refresh.isPending} onClick={() => refresh.mutate()}>
              Refresh from providers
            </Button>
          }
        />
        <div className="px-4 py-3">
          <Caveat>
            Refreshing asks each configured provider for its live model list, marks what it
            confirms, and flags catalogue entries the provider no longer lists — so a retired model
            is discovered here rather than as a mid-batch failure. Newly discovered models are
            added disabled, without pricing, and with conservative capability flags.
          </Caveat>
          {refresh.data ? (
            <div className="mt-3 space-y-2 text-xs">
              {Object.entries(refresh.data.providers).map(([provider, info]) => (
                <div key={provider} className="flex flex-wrap items-center gap-2">
                  <Badge tone={info.status === "ok" ? "success" : "warn"}>{provider}</Badge>
                  <span className="text-ink-muted">
                    {info.status === "ok"
                      ? `${info.live_model_count} live model(s)`
                      : `${info.status}: ${info.reason}`}
                  </span>
                </div>
              ))}
              {refresh.data.discovered.length > 0 ? (
                <p className="text-ink-muted">
                  Discovered (added disabled): {refresh.data.discovered.join(", ")}
                </p>
              ) : null}
              {refresh.data.unverified.length > 0 ? (
                <p className="text-warn">
                  Not in the provider&apos;s live list: {refresh.data.unverified.join(", ")}
                </p>
              ) : null}
            </div>
          ) : null}
          {refresh.error ? <ErrorState error={refresh.error} /> : null}
        </div>
      </Card>

      <Table
        head={["Model", "Tier", "Price in/out per MTok", "Temperature", "Effort", "Verified", "Enabled"]}
      >
        {(models.data ?? []).map((model) => (
          <Tr key={model.id}>
            <Td>
              <span className="font-mono text-xs">{model.model_id}</span>
              <span className="block text-2xs text-ink-faint">{model.provider}</span>
              {model.notes ? (
                <span className="mt-0.5 block max-w-md text-2xs leading-relaxed text-ink-muted">
                  {model.notes}
                </span>
              ) : null}
            </Td>
            <Td className="text-xs">{model.tier}</Td>
            <Td className="whitespace-nowrap text-xs tabular-nums">
              {model.input_cost_per_mtok !== null ? (
                `$${model.input_cost_per_mtok} / $${model.output_cost_per_mtok}`
              ) : (
                <Badge tone="warn">unknown</Badge>
              )}
            </Td>
            <Td className="text-xs">
              {model.supports_temperature ? (
                <Badge tone="success">accepted</Badge>
              ) : (
                <Badge tone="warn" title="Sending temperature to this model returns an error.">
                  rejected
                </Badge>
              )}
            </Td>
            <Td className="text-xs">
              {model.supports_effort ? (
                <span>
                  yes
                  {model.default_effort ? (
                    <span className="text-ink-faint"> (default {model.default_effort})</span>
                  ) : null}
                </span>
              ) : (
                <span className="text-ink-faint">no</span>
              )}
            </Td>
            <Td className="text-2xs">
              {model.verified_live ? (
                <Badge tone="success">live</Badge>
              ) : model.last_verified_at ? (
                <Badge tone="warn">not listed</Badge>
              ) : (
                <span className="text-ink-faint">unchecked</span>
              )}
            </Td>
            <Td>
              <Button
                size="sm"
                variant={model.is_enabled ? "secondary" : "ghost"}
                onClick={() => toggle.mutate({ id: model.id, enabled: !model.is_enabled })}
              >
                {model.is_enabled ? "Enabled" : "Disabled"}
              </Button>
            </Td>
          </Tr>
        ))}
      </Table>

      <Caveat className="mt-3">
        Prices are an operator-configurable estimate used for pre-flight projections and cost
        tracking. Check your provider&apos;s dashboard for authoritative billing.
      </Caveat>
    </>
  );
}
