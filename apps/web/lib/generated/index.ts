/**
 * GENERATED FILE — do not edit.
 *
 * Produced by `python -m explanationlab.export_schemas` from the backend
 * enums and strategy definitions, so the two cannot drift apart.
 */

import catalog from "./catalog.json";

export { catalog };

export type Provider = "openai" | "anthropic" | "manual";
export type ExperimentType = "baseline" | "prompt_intervention" | "ablation" | "cross_model" | "human_study";
export type ExperimentStatus = "draft" | "configured" | "running" | "completed" | "failed" | "evaluated" | "reported";
export type ResponseKind = "source" | "transformed";
export type ResponseOrigin = "api" | "manual_import" | "demo_fixture";
export type LearnerLevel = "beginner" | "intermediate" | "advanced";
export type PromptCondition = "default" | "generic_tutor" | "structured_pedagogical" | "custom";
export type Treatment = "T1" | "T2" | "T3" | "T4" | "T5" | "T6";
export type RunStatus = "pending" | "running" | "succeeded" | "failed" | "skipped";
export type ItemFormat = "multiple_choice" | "short_answer" | "scenario" | "likert";
export type EvalDimension = "A_immediate_comprehension" | "B_mechanistic_understanding" | "C_transfer" | "D_perceived_clarity" | "E_cognitive_effort" | "F_misconception" | "G_time" | "H_delayed_retention";
export type GradingMode = "manual" | "ai_assisted" | "auto_objective";
export type StudyStatus = "draft" | "open" | "closed";
export type EvidenceClass = "automated_diagnostic" | "ai_judge_opinion" | "human_preference" | "human_comprehension";

export interface TreatmentDefinition {
  key: Treatment;
  name: string;
  category: string;
  description: string;
  /** What this treatment must NOT do. Checked in pipeline stage D. */
  boundary_note: string;
  default_params: Record<string, unknown>;
  version: number;
}

export const TREATMENTS = catalog.treatments as TreatmentDefinition[];

export const EVIDENCE_CLASS_MEANING = catalog.evidence_class_meaning as Record<
  EvidenceClass,
  string
>;

/** Canonical composition order when several treatments are combined. */
export const TREATMENT_ORDER: Treatment[] = [
  "T3",
  "T4",
  "T6",
  "T1",
  "T2",
  "T5",
];
