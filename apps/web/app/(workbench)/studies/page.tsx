"use client";

/**
 * Human evaluation workspace — researcher side.
 *
 * The study builder enforces the design constraints that matter: every arm must
 * answer the same question, and the item set must cover comprehension rather
 * than only perception. The default item template reflects the required
 * evaluation dimensions so a researcher does not have to remember them.
 */

import { useMutation, useQueryClient } from "@tanstack/react-query";
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
  Input,
  Loading,
  Mono,
  PageHeader,
  Section,
  Select,
  StatusDot,
  SyntheticBadge,
  Table,
  Td,
  Textarea,
  Tr,
} from "@/components/ui";
import { Study, api } from "@/lib/api";
import { useQuestions, useResponses, useStudies } from "@/lib/hooks";

type ItemDraft = {
  format: "multiple_choice" | "short_answer" | "scenario" | "likert";
  dimension: string;
  prompt: string;
  options: string[];
  correct_option_index: number | null;
  misconception_option_indexes: number[];
  rubric_key: string | null;
  max_score: number;
  is_required: boolean;
};

const DIMENSIONS = [
  { value: "A_immediate_comprehension", label: "A · Immediate comprehension" },
  { value: "B_mechanistic_understanding", label: "B · Mechanistic understanding" },
  { value: "C_transfer", label: "C · Transfer to a new situation" },
  { value: "D_perceived_clarity", label: "D · Perceived clarity" },
  { value: "E_cognitive_effort", label: "E · Cognitive effort" },
  { value: "F_misconception", label: "F · Misconception detection" },
];

function defaultItems(): ItemDraft[] {
  return [
    {
      format: "multiple_choice",
      dimension: "A_immediate_comprehension",
      prompt: "Which statement best matches what the explanation said?",
      options: ["", "", ""],
      correct_option_index: 0,
      misconception_option_indexes: [],
      rubric_key: null,
      max_score: 1,
      is_required: true,
    },
    {
      format: "short_answer",
      dimension: "B_mechanistic_understanding",
      prompt: "In your own words, explain how and why this works.",
      options: [],
      correct_option_index: null,
      misconception_option_indexes: [],
      rubric_key: "mechanism_short_answer",
      max_score: 2,
      is_required: true,
    },
    {
      format: "scenario",
      dimension: "C_transfer",
      prompt:
        "Here is a situation the explanation did not cover. What would happen, and why?",
      options: [],
      correct_option_index: null,
      misconception_option_indexes: [],
      rubric_key: "transfer_scenario",
      max_score: 2,
      is_required: true,
    },
  ];
}

export default function StudiesPage() {
  const searchParams = useSearchParams();
  const queryClient = useQueryClient();
  const studies = useStudies();
  const questions = useQuestions();

  const [building, setBuilding] = React.useState(false);
  const [questionId, setQuestionId] = React.useState("");
  const [name, setName] = React.useState("");
  const [responseIds, setResponseIds] = React.useState<string[]>([]);
  const [items, setItems] = React.useState<ItemDraft[]>(defaultItems());
  const [seed, setSeed] = React.useState(20261022);
  const [balance, setBalance] = React.useState(true);
  const [collectPrior, setCollectPrior] = React.useState(true);
  const [maxPerCondition, setMaxPerCondition] = React.useState<string>("");

  const responses = useResponses({ questionId: questionId || undefined, enabled: !!questionId });

  // Arriving from the transformation workbench with ?response=… opens the
  // builder with that variant preselected. Runs once per distinct id.
  const preselect = searchParams.get("response");
  React.useEffect(() => {
    if (!preselect) return;
    setBuilding(true);
    setResponseIds((prev) => (prev.includes(preselect) ? prev : [...prev, preselect]));
  }, [preselect]);

  const create = useMutation({
    mutationFn: () =>
      api.post<Study>("studies", {
        name: name.trim() || `Comprehension study — ${new Date().toLocaleDateString()}`,
        question_id: questionId || null,
        response_ids: responseIds,
        collect_prior_knowledge: collectPrior,
        seed,
        balance_conditions: balance,
        max_per_condition: maxPerCondition ? Number(maxPerCondition) : null,
        items: items.map((item) => ({
          format: item.format,
          dimension: item.dimension,
          prompt: item.prompt,
          options: item.options.filter((o) => o.trim()),
          correct_option_index:
            item.format === "multiple_choice" ? item.correct_option_index : null,
          misconception_option_indexes: item.misconception_option_indexes,
          rubric_key: item.rubric_key,
          max_score: item.max_score,
          is_required: item.is_required,
        })),
      }),
    onSuccess: (study) => {
      queryClient.invalidateQueries({ queryKey: ["studies"] });
      setBuilding(false);
      setResponseIds([]);
      setItems(defaultItems());
      window.location.href = `/studies/${study.id}`;
    },
  });

  if (studies.isLoading) return <Loading label="Loading studies" />;

  const invalidItems = items.filter(
    (item) =>
      !item.prompt.trim() ||
      (item.format === "multiple_choice" &&
        (item.options.filter((o) => o.trim()).length < 2 || item.correct_option_index === null)),
  );
  const canCreate = responseIds.length >= 2 && items.length > 0 && invalidItems.length === 0;

  return (
    <>
      <PageHeader
        eyebrow="Human evaluation · Experiment 5"
        title="Blind comprehension studies"
        description="The only measurement in this platform that is evidence of understanding. Participants read one explanation without knowing its source, then are assessed."
        actions={
          <Button variant="primary" onClick={() => setBuilding((open) => !open)}>
            {building ? "Cancel" : "New study"}
          </Button>
        }
      />

      <Caveat tone="accent" className="mb-5">
        Start by <Link href="/compare" className="underline">importing real ChatGPT and Claude
        answers in Comparison</Link>. Then build a study from those answers. On its <strong>AI
        proxy</strong> tab, Gemini can check answerability without participants. The separate
        participant link and <strong>Results</strong> tab measure human comprehension only when
        real people submit answers. AI proxy scores do not count as human results.
      </Caveat>

      {building ? (
        <Card className="mb-6">
          <CardHeader
            title="Study builder"
            description="All arms must answer the same research question, so differences are not confounded with question difficulty."
          />

          <div className="space-y-5 px-4 py-4">
            <div className="grid gap-4 sm:grid-cols-2">
              <Field label="Study name">
                <Input
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="T1 vs untransformed — caching, intermediate"
                />
              </Field>
              <Field label="Research question">
                <Select
                  value={questionId}
                  onChange={(e) => {
                    setQuestionId(e.target.value);
                    setResponseIds([]);
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
            </div>

            <div>
              <p className="mb-2 text-xs font-medium">
                Conditions — select at least two answer variants
              </p>
              {!questionId ? (
                <p className="text-xs text-ink-muted">Choose a question first.</p>
              ) : responses.isLoading ? (
                <Loading />
              ) : (responses.data ?? []).length < 2 ? (
                <Caveat tone="warn">
                  This question has fewer than two stored answers. Import real web-chat answers in
                  Comparison, then return here.
                </Caveat>
              ) : (
                <div className="max-h-56 space-y-1.5 overflow-y-auto rounded-md border border-line bg-canvas px-3 py-2.5">
                  {(responses.data ?? []).map((response) => (
                    <Checkbox
                      key={response.id}
                      checked={responseIds.includes(response.id)}
                      onChange={(checked) =>
                        setResponseIds((prev) =>
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
                          {response.is_synthetic ? <SyntheticBadge /> : null}
                        </span>
                      }
                      description={response.label || undefined}
                    />
                  ))}
                </div>
              )}
              <p className="mt-1.5 text-2xs text-ink-faint">
                Participants never see these labels, the model name, or the treatment set.
              </p>
            </div>

            <div className="grid gap-4 sm:grid-cols-3">
              <Field label="Randomisation seed" hint="Makes the allocation sequence replayable.">
                <Input type="number" value={seed} onChange={(e) => setSeed(Number(e.target.value))} />
              </Field>
              <Field label="Cap per condition" hint="Optional. Blank means no cap.">
                <Input
                  type="number"
                  min={1}
                  value={maxPerCondition}
                  onChange={(e) => setMaxPerCondition(e.target.value)}
                  placeholder="unlimited"
                />
              </Field>
              <div className="space-y-2 pt-5">
                <Checkbox
                  checked={balance}
                  onChange={setBalance}
                  label="Balance arms"
                  description="Assign the least-filled arm first."
                />
                <Checkbox
                  checked={collectPrior}
                  onChange={setCollectPrior}
                  label="Ask prior knowledge"
                  description="A short self-report before reading."
                />
              </div>
            </div>

            <div>
              <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
                <p className="text-xs font-medium">
                  Assessment items ({items.length}) — cover comprehension, not just perception
                </p>
                <div className="flex gap-2">
                  <Button size="sm" onClick={() => setItems(defaultItems())}>
                    Reset to template
                  </Button>
                  <Button
                    size="sm"
                    onClick={() =>
                      setItems((prev) => [
                        ...prev,
                        {
                          format: "multiple_choice",
                          dimension: "A_immediate_comprehension",
                          prompt: "",
                          options: ["", ""],
                          correct_option_index: 0,
                          misconception_option_indexes: [],
                          rubric_key: null,
                          max_score: 1,
                          is_required: true,
                        },
                      ])
                    }
                  >
                    Add item
                  </Button>
                </div>
              </div>

              <div className="space-y-3">
                {items.map((item, index) => (
                  <ItemEditor
                    key={index}
                    item={item}
                    index={index}
                    onChange={(next) =>
                      setItems((prev) => prev.map((current, i) => (i === index ? next : current)))
                    }
                    onRemove={() => setItems((prev) => prev.filter((_, i) => i !== index))}
                  />
                ))}
              </div>

              <Caveat className="mt-3">
                Clarity and cognitive-effort ratings are collected automatically on every
                submission, so you do not need items for dimensions D and E. Free-text mechanism
                and transfer items are presented after the multiple-choice items, because writing
                an explanation is itself a learning intervention and would otherwise change the
                later answers.
              </Caveat>
            </div>

            <div className="flex flex-wrap items-center gap-3 border-t border-line pt-4">
              <Button
                variant="primary"
                disabled={!canCreate}
                loading={create.isPending}
                onClick={() => create.mutate()}
              >
                Create study
              </Button>
              {responseIds.length < 2 ? (
                <span className="text-2xs text-ink-faint">Select at least two conditions.</span>
              ) : invalidItems.length > 0 ? (
                <span className="text-2xs text-warn">
                  {invalidItems.length} item(s) need a prompt, and multiple-choice items need at
                  least two options plus a correct answer.
                </span>
              ) : null}
              {create.error ? <ErrorState error={create.error} /> : null}
            </div>
          </div>
        </Card>
      ) : null}

      <Section title="Studies">
        {(studies.data ?? []).length === 0 ? (
          <EmptyState
            title="No studies yet"
            action={
              <Button variant="primary" onClick={() => setBuilding(true)}>
                Create your first study
              </Button>
            }
          >
            A study takes two or more answer variants for the same question, assigns participants
            to them at random, and measures what each participant actually understood.
          </EmptyState>
        ) : (
          <Table head={["Study", "Status", "Seed", "Participant link", "Created"]}>
            {(studies.data ?? []).map((study) => (
              <Tr key={study.id}>
                <Td>
                  <Link
                    href={`/studies/${study.id}`}
                    className="font-medium text-accent-strong underline-offset-2 hover:underline"
                  >
                    {study.name}
                  </Link>
                </Td>
                <Td>
                  <span className="inline-flex items-center gap-1.5 text-xs">
                    <StatusDot status={study.status} />
                    {study.status}
                  </span>
                </Td>
                <Td>
                  <Mono>{study.seed}</Mono>
                </Td>
                <Td className="text-xs">
                  {study.status === "open" ? (
                    <Link href={`/p/${study.access_token}`} className="text-accent underline">
                      /p/{study.access_token.slice(0, 10)}…
                    </Link>
                  ) : (
                    <span className="text-ink-faint">not open</span>
                  )}
                </Td>
                <Td className="text-2xs text-ink-faint">
                  {new Date(study.created_at).toLocaleDateString()}
                </Td>
              </Tr>
            ))}
          </Table>
        )}
      </Section>
    </>
  );
}

function ItemEditor({
  item,
  index,
  onChange,
  onRemove,
}: {
  item: ItemDraft;
  index: number;
  onChange: (item: ItemDraft) => void;
  onRemove: () => void;
}) {
  const isChoice = item.format === "multiple_choice";
  return (
    <Card className="bg-canvas">
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-line px-3 py-2">
        <span className="text-xs font-medium">Item {index + 1}</span>
        <div className="flex items-center gap-2">
          <Select
            className="w-auto text-xs"
            value={item.format}
            onChange={(e) =>
              onChange({
                ...item,
                format: e.target.value as ItemDraft["format"],
                options: e.target.value === "multiple_choice" ? item.options.length ? item.options : ["", ""] : [],
                correct_option_index: e.target.value === "multiple_choice" ? 0 : null,
              })
            }
          >
            <option value="multiple_choice">Multiple choice</option>
            <option value="short_answer">Short answer</option>
            <option value="scenario">Scenario application</option>
          </Select>
          <Select
            className="w-auto text-xs"
            value={item.dimension}
            onChange={(e) => onChange({ ...item, dimension: e.target.value })}
          >
            {DIMENSIONS.map((dimension) => (
              <option key={dimension.value} value={dimension.value}>
                {dimension.label}
              </option>
            ))}
          </Select>
          <Button size="sm" variant="ghost" onClick={onRemove}>
            Remove
          </Button>
        </div>
      </div>

      <div className="space-y-3 px-3 py-3">
        <Field label="Question shown to the participant">
          <Textarea
            rows={2}
            value={item.prompt}
            onChange={(e) => onChange({ ...item, prompt: e.target.value })}
          />
        </Field>

        {isChoice ? (
          <div>
            <p className="mb-1.5 text-xs font-medium">
              Options — mark the correct answer, and tag any distractor that reveals a specific
              misconception
            </p>
            <div className="space-y-1.5">
              {item.options.map((option, optionIndex) => (
                <div key={optionIndex} className="flex items-center gap-2">
                  <input
                    type="radio"
                    name={`correct-${index}`}
                    checked={item.correct_option_index === optionIndex}
                    onChange={() => onChange({ ...item, correct_option_index: optionIndex })}
                    title="Correct answer"
                    className="h-3.5 w-3.5 text-accent"
                  />
                  <Input
                    value={option}
                    onChange={(e) =>
                      onChange({
                        ...item,
                        options: item.options.map((current, i) =>
                          i === optionIndex ? e.target.value : current,
                        ),
                      })
                    }
                    placeholder={`Option ${optionIndex + 1}`}
                  />
                  <label className="flex shrink-0 items-center gap-1 text-2xs text-ink-muted">
                    <input
                      type="checkbox"
                      checked={item.misconception_option_indexes.includes(optionIndex)}
                      onChange={(e) =>
                        onChange({
                          ...item,
                          misconception_option_indexes: e.target.checked
                            ? [...item.misconception_option_indexes, optionIndex]
                            : item.misconception_option_indexes.filter((i) => i !== optionIndex),
                        })
                      }
                      className="h-3.5 w-3.5"
                    />
                    misconception
                  </label>
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() =>
                      onChange({
                        ...item,
                        options: item.options.filter((_, i) => i !== optionIndex),
                        correct_option_index:
                          item.correct_option_index === optionIndex ? 0 : item.correct_option_index,
                      })
                    }
                  >
                    ×
                  </Button>
                </div>
              ))}
            </div>
            <Button
              size="sm"
              className="mt-2"
              onClick={() => onChange({ ...item, options: [...item.options, ""] })}
            >
              Add option
            </Button>
          </div>
        ) : (
          <div className="grid gap-3 sm:grid-cols-2">
            <Field label="Grading rubric" hint="Stored with the grade, including its version.">
              <Select
                value={item.rubric_key ?? ""}
                onChange={(e) => onChange({ ...item, rubric_key: e.target.value || null })}
              >
                <option value="">None (free-form grading)</option>
                <option value="mechanism_short_answer">Mechanistic understanding (0–2)</option>
                <option value="transfer_scenario">Transfer (0–2)</option>
              </Select>
            </Field>
            <Field label="Maximum score">
              <Input
                type="number"
                min={0}
                max={10}
                step="0.5"
                value={item.max_score}
                onChange={(e) => onChange({ ...item, max_score: Number(e.target.value) })}
              />
            </Field>
          </div>
        )}

        <Checkbox
          checked={item.is_required}
          onChange={(checked) => onChange({ ...item, is_required: checked })}
          label="Required"
        />
      </div>
    </Card>
  );
}
