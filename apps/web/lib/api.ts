/** Typed client for the ExplanationLab API, via the server-side proxy. */

export class ApiError extends Error {
  status: number;
  errorType?: string;
  detail: unknown;

  constructor(status: number, detail: unknown) {
    super(ApiError.describe(detail, status));
    this.status = status;
    this.detail = detail;
    const record = detail as Record<string, unknown> | undefined;
    const inner = record?.detail as Record<string, unknown> | undefined;
    this.errorType = (inner?.error_type ?? record?.error_type) as string | undefined;
  }

  /** Turn FastAPI's several error shapes into one readable sentence. */
  static describe(detail: unknown, status: number): string {
    if (typeof detail === "string") return detail;
    const record = detail as Record<string, unknown> | undefined;
    const inner = record?.detail;
    if (typeof inner === "string") return inner;
    if (inner && typeof inner === "object") {
      const message = (inner as Record<string, unknown>).message;
      if (typeof message === "string") return message;
    }
    if (Array.isArray(inner)) {
      // Pydantic validation errors.
      return inner
        .map((item) => {
          const e = item as Record<string, unknown>;
          const loc = Array.isArray(e.loc) ? e.loc.slice(1).join(".") : "";
          return `${loc}: ${e.msg}`;
        })
        .join("; ");
    }
    return `Request failed (HTTP ${status})`;
  }
}

async function request<T>(
  path: string,
  options: { method?: string; body?: unknown; signal?: AbortSignal } = {},
): Promise<T> {
  const response = await fetch(`/api/proxy/${path}`, {
    method: options.method ?? "GET",
    headers: options.body !== undefined ? { "content-type": "application/json" } : undefined,
    body: options.body !== undefined ? JSON.stringify(options.body) : undefined,
    signal: options.signal,
    cache: "no-store",
  });

  const text = await response.text();
  const isJson = (response.headers.get("content-type") ?? "").includes("application/json");
  const payload = isJson && text ? JSON.parse(text) : text;

  if (!response.ok) throw new ApiError(response.status, payload);
  return payload as T;
}

export const api = {
  get: <T>(path: string, signal?: AbortSignal) => request<T>(path, { signal }),
  post: <T>(path: string, body?: unknown) => request<T>(path, { method: "POST", body }),
  patch: <T>(path: string, body?: unknown) => request<T>(path, { method: "PATCH", body }),
  del: <T>(path: string) => request<T>(path, { method: "DELETE" }),
  /** Download URL for an export; goes through the same proxy. */
  downloadUrl: (path: string) => `/api/proxy/${path}`,
};

// ---------------------------------------------------------------------------
// Shared types (mirrors packages/shared-schemas/types.ts)
// ---------------------------------------------------------------------------

export type Provider = "openai" | "anthropic" | "gemini" | "manual";
export type TreatmentKey = "T1" | "T2" | "T3" | "T4" | "T5" | "T6";
export type EvidenceClass =
  | "automated_diagnostic"
  | "ai_judge_opinion"
  | "human_preference"
  | "human_comprehension";

export interface SystemStatus {
  demo_mode: boolean;
  providers: Record<string, { configured: boolean }>;
  auth_enabled: boolean;
  limits: {
    max_batch_requests: number;
    cost_confirmation_threshold_usd: number;
    daily_spend_cap_usd: number;
    max_input_chars: number;
  };
  response_cache_enabled: boolean;
  provider_status: { provider: string; configured: boolean; mode: string }[];
  model_catalog_entries: number;
  pricing_verified_on: string;
  demo_mode_notice: string | null;
}

export interface Question {
  id: string;
  text: string;
  domain: string;
  topic: string;
  conceptual_difficulty: string;
  factual_checklist: string[];
  checklist_reviewed_by: string | null;
  notes: string;
  is_seed: boolean;
  created_at: string;
}

export interface LearnerProfile {
  id: string;
  name: string;
  level: string;
  description: string;
  assumed_prior_knowledge: string[];
  unfamiliar_with: string[];
  is_builtin: boolean;
}

export interface ModelEntry {
  id: string;
  provider: string;
  model_id: string;
  display_name: string;
  tier: string;
  input_cost_per_mtok: number | null;
  output_cost_per_mtok: number | null;
  context_window: number | null;
  supports_temperature: boolean;
  supports_effort: boolean;
  supports_max_output_tokens: boolean;
  supports_structured_output: boolean;
  default_effort: string | null;
  is_enabled: boolean;
  verified_live: boolean;
  last_verified_at: string | null;
  notes: string;
  pricing_source: string;
}

export interface PromptVersion {
  id: string;
  version: number;
  system_text: string;
  user_template: string;
  changelog: string;
  is_active: boolean;
  created_at: string;
}

export interface PromptTemplate {
  id: string;
  key: string;
  name: string;
  condition: string;
  description: string;
  is_builtin: boolean;
  versions: PromptVersion[];
}

export interface Strategy {
  id: string;
  key: TreatmentKey;
  name: string;
  description: string;
  category: string;
  boundary_note: string;
  versions: {
    id: string;
    version: number;
    is_active: boolean;
    default_params: Record<string, unknown>;
    instruction_template: string;
  }[];
}

export interface Experiment {
  id: string;
  name: string;
  type: string;
  status: string;
  objective: string;
  hypothesis: string;
  researcher_notes: string;
  seed: number;
  repetitions: number;
  estimated_cost_usd: number;
  config: Record<string, any>;
  error: string | null;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
}

export interface Estimate {
  total_model_calls: number;
  total_runs: number;
  condition_count: number;
  estimated_cost_usd: number;
  per_condition: {
    label: string;
    calls_per_run: number;
    runs: number;
    total_calls: number;
    estimated_cost_usd: number;
  }[];
  max_batch_requests: number;
  exceeds_batch_limit: boolean;
  requires_confirmation: boolean;
  confirmation_threshold_usd: number;
  demo_mode: boolean;
  note: string;
}

export interface Job {
  id: string;
  kind: string;
  status: string;
  progress_done: number;
  progress_total: number;
  error: string | null;
  experiment_id: string | null;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
}

export interface ResponseRow {
  id: string;
  kind: string;
  origin: string;
  run_id: string | null;
  parent_response_id: string | null;
  question_id: string | null;
  learner_profile_id: string | null;
  prompt_version_id: string | null;
  provider: string;
  model_id: string;
  label: string;
  text: string;
  system_prompt_snapshot: string;
  user_prompt_snapshot: string;
  applied_treatments: string[];
  control_limitations: string[];
  generation_settings: Record<string, unknown>;
  requested_settings: Record<string, unknown>;
  input_tokens: number | null;
  output_tokens: number | null;
  latency_ms: number | null;
  cost_usd: number;
  finish_reason: string | null;
  served_from_cache: boolean;
  is_synthetic: boolean;
  created_at: string;
}

export interface Metrics {
  metrics_version: string;
  surface: Record<string, number>;
  readability: { flesch_reading_ease: number; flesch_kincaid_grade: number; gunning_fog: number; caveat: string };
  repetition: { repeated_trigram_count: number; top_repeated_trigrams: [string, number][]; most_frequent_content_words: [string, number][] };
  jargon: { candidate_count: number; candidates: string[]; nominalisation_count: number; nominalisation_density: number; indirection_phrase_count: number; indirection_phrases: string[]; method: string };
  terminology_introduction: { terms_checked: number; defined_near_first_use: number; undefined_share: number | null; terms: { term: string; defined_near_first_use: boolean }[]; method: string };
  unresolved_references: { count: number; examples: { sentence_index: number; excerpt: string }[]; method: string };
  structure: { heading_count: number; max_heading_depth: number; heading_levels_used: number[]; has_skipped_heading_level: boolean; list_item_count: number; table_row_count: number; code_block_count: number; headings: { level: number; text: string }[] };
  explanation_steps: { causal_marker_total: number; causal_markers: Record<string, number>; causal_density_per_100w: number; sequence_marker_total: number; sequence_markers: Record<string, number> };
  hedging: { hedge_count: number; hedge_density_per_100w: number };
  concept_coverage: { checklist_size: number; covered: number; coverage_ratio: number | null; items: { claim: string; match_ratio?: number; likely_present: boolean }[]; method: string };
  interpretation_warning: string;
}

export interface JudgeScore {
  metric: string;
  score: number;
  rationale: string;
  evidence: string;
  confidence: string;
  improvement_suggestion: string;
  evidence_class: string;
}

export interface FidelityWarning {
  type: string;
  severity: string;
  detail: string;
  source_excerpt?: string;
  transformed_excerpt?: string;
  detector?: string;
}

export interface ResponseDetail {
  response: ResponseRow;
  question: { id: string; text: string; domain: string; factual_checklist: string[] } | null;
  learner_profile: { id: string; name: string; level: string } | null;
  source_response: { id: string; text: string; model_id: string } | null;
  transformation_meta: Record<string, any>;
  automated_diagnostics: { evidence_class: string; metrics: Metrics | null };
  ai_judge_evaluations: {
    id: string;
    provider: string;
    model_id: string;
    rubric: string;
    blinded: boolean;
    scores: JudgeScore[];
    overall_notes: string;
    is_synthetic: boolean;
    evidence_class: string;
    created_at: string;
  }[];
  fidelity_reports: {
    id: string;
    verdict: string;
    warnings: FidelityWarning[];
    numeric_drift: { source_value: string; transformed_value: string; context?: string }[];
    checklist_coverage: unknown[];
    reviewed_by_human: boolean;
    provisional: boolean;
  }[];
  concept_graphs: ConceptGraphPayload[];
  annotations: { id: string; author: string; label: string; body: string; quoted_excerpt: string; created_at: string }[];
}

export interface GraphNode {
  id: string;
  label: string;
  importance?: string;
  introduced_in_text?: boolean;
  explained_in_text?: boolean;
}
export interface GraphEdge {
  source: string;
  target: string;
  relation: string;
  confidence?: string;
}
export interface ConceptGraphPayload {
  id?: string;
  nodes: GraphNode[];
  edges: GraphEdge[];
  teaching_order: string[];
  cycles_detected?: string[][];
  cycles?: string[][];
  dropped_edges?: unknown[];
  warnings?: string[];
  model_id?: string;
  is_hypothesis: boolean;
  is_synthetic?: boolean;
  disclaimer?: string;
  sequencing_analysis?: {
    edges_checked: number;
    violation_count: number;
    violations: { prerequisite: string; dependent: string; detail: string }[];
    violation_rate: number | null;
    concepts_not_located_in_text: string[];
    mention_order: string[];
    teaching_order: string[];
    note: string;
  };
}

export interface TransformResult {
  variant_response_id: string | null;
  text: string;
  applied_treatments: string[];
  treatment_order: string[];
  analysis: Record<string, any> | null;
  plan: Record<string, any> | null;
  fidelity: {
    verdict: string;
    warnings: FidelityWarning[];
    numeric_drift: unknown[];
    provisional: boolean;
    llm_review_ran: boolean;
    deterministic_warning_count?: number;
    llm_warning_count?: number;
    notes?: string;
  } | null;
  changes: {
    treatment: string;
    name: string;
    stats: Record<string, number>;
    unified_diff: string;
    text_after: string;
  }[];
  stages: {
    stage: string;
    label: string;
    provider: string;
    model_id: string;
    input_tokens: number | null;
    output_tokens: number | null;
    latency_ms: number | null;
    cost_usd: number;
    served_from_cache: boolean;
    notes: string[];
  }[];
  total_cost_usd: number;
  is_synthetic: boolean;
  control_limitations: string[];
}

export interface StatSummary {
  n: number;
  mean: number | null;
  sd: number | null;
  median: number | null;
  min: number | null;
  max: number | null;
  ci_low: number | null;
  ci_high: number | null;
  ci_method: string | null;
  warnings: string[];
}

export interface ExperimentSummary {
  experiment: Partial<Experiment> & { id: string; name: string };
  conditions: {
    condition_id: string;
    label: string;
    provider: string;
    model_id: string;
    treatments: string[];
    transform_model_id: string | null;
    runs: { total: number; succeeded: number; failed: number; pending: number };
    response_count: number;
    contains_synthetic: boolean;
    automated_diagnostics: { evidence_class: string; n: number; metrics: Record<string, StatSummary>; caveat?: string };
    ai_judge: { evidence_class: string; n: number; judge_models?: string[]; metrics: Record<string, StatSummary>; independence_warnings?: string[]; caveat?: string };
    fidelity: { reports: number; by_verdict?: Record<string, number>; warning_counts_by_type?: Record<string, number>; high_severity_warnings?: number; numeric_drift_reports?: number; human_reviewed?: number; caveat?: string };
    operations: { latency_ms: StatSummary | null; total_cost_usd: number; output_tokens: StatSummary | null; cache_hits: number };
    control_limitations: string[];
  }[];
  contains_synthetic_data: boolean;
  evidence_note: string;
  questions: { id: string; text: string; domain: string; conceptual_difficulty: string }[];
}

export interface Study {
  id: string;
  name: string;
  status: string;
  question_id: string | null;
  experiment_id: string | null;
  intro_text: string;
  consent_text: string;
  collect_prior_knowledge: boolean;
  seed: number;
  balance_conditions: boolean;
  max_per_condition: number | null;
  access_token: string;
  created_at: string;
}

export interface StudyResults {
  study: { id: string; name: string; status: string; seed: number; balance_conditions: boolean; question_id: string | null };
  conditions: {
    condition_id: string;
    label: string;
    response_id: string;
    model_id: string;
    treatments: string[];
    contains_synthetic_stimulus: boolean;
    participants: { assigned: number; submitted: number; withdrawn: number };
    human_comprehension: {
      evidence_class: string;
      overall: StatSummary;
      by_dimension: Record<string, StatSummary>;
      misconception_rate: number | null;
      pending_grading_items: number;
    };
    human_preference: {
      evidence_class: string;
      perceived_clarity: StatSummary;
      cognitive_effort: StatSummary;
      caveat: string;
    };
    time: { reading_seconds: StatSummary; assessment_seconds: StatSummary };
  }[];
  totals: { assigned: number; submitted: number; pending_grading_items: number };
  warnings: string[];
  contains_synthetic_data: boolean;
  evidence_note: string;
}

export interface Overview {
  experiments: { total: number; by_status: Record<string, number> };
  runs: { completed: number; failed: number };
  responses: { total: number; synthetic: number; real: number };
  models_evaluated: number;
  human_studies: { active: number; submissions: number };
  usage: { input_tokens: number; output_tokens: number; estimated_cost_usd: number; calls: number; errors: number; cache_hits: number };
  evaluation_coverage: {
    responses_with_diagnostics: number;
    responses_with_judge_opinion: number;
    diagnostic_coverage: number | null;
    judge_coverage: number | null;
  };
  recent_experiments: { id: string; name: string; type: string; status: string; created_at: string }[];
  contains_synthetic_data: boolean;
}

export interface UsagePayload {
  window_days: number;
  by_purpose: { purpose: string; calls: number; input_tokens: number; output_tokens: number; estimated_cost_usd: number }[];
  by_model: { provider: string; model_id: string; calls: number; estimated_cost_usd: number; avg_latency_ms: number | null }[];
  errors: {
    by_type: { error_type: string; count: number }[];
    recent: { created_at: string; provider: string; model_id: string; purpose: string; error_type: string; error_message: string }[];
  };
  cache: { hits: number; total_calls: number; hit_rate: number | null };
  spend_controls: { spent_today_usd: number; daily_cap_usd: number; remaining_today_usd: number; cap_reached: boolean };
  note: string;
}

export interface ParticipantSession {
  study: { id: string; name: string; intro_text: string; consent_text: string; collect_prior_knowledge: boolean };
  participant_code: string;
  assignment_id: string;
  explanation: { text: string };
  contains_synthetic_stimulus: boolean;
  items: {
    id: string;
    format: string;
    prompt: string;
    options: string[];
    is_required: boolean;
    dimension: string;
  }[];
}
