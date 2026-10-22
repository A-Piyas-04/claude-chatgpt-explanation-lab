"use client";

import { useQuery } from "@tanstack/react-query";

import {
  api,
  Experiment,
  LearnerProfile,
  ModelEntry,
  Overview,
  PromptTemplate,
  Question,
  ResponseRow,
  Strategy,
  Study,
} from "./api";

export const useQuestions = (params?: { domain?: string; search?: string }) =>
  useQuery({
    queryKey: ["questions", params],
    queryFn: () => {
      const search = new URLSearchParams();
      if (params?.domain) search.set("domain", params.domain);
      if (params?.search) search.set("search", params.search);
      const qs = search.toString();
      return api.get<Question[]>(`questions${qs ? `?${qs}` : ""}`);
    },
  });

export const useProfiles = () =>
  useQuery({
    queryKey: ["learner-profiles"],
    queryFn: () => api.get<LearnerProfile[]>("learner-profiles"),
    staleTime: 300_000,
  });

export const useModels = () =>
  useQuery({
    queryKey: ["models"],
    queryFn: () => api.get<ModelEntry[]>("models"),
    staleTime: 300_000,
  });

export const usePrompts = () =>
  useQuery({
    queryKey: ["prompts"],
    queryFn: () => api.get<PromptTemplate[]>("prompts"),
    staleTime: 300_000,
  });

export const useStrategies = () =>
  useQuery({
    queryKey: ["strategies"],
    queryFn: () => api.get<Strategy[]>("transformations/strategies"),
    staleTime: 300_000,
  });

export const useExperiments = () =>
  useQuery({
    queryKey: ["experiments"],
    queryFn: () => api.get<Experiment[]>("experiments"),
  });

export const useStudies = () =>
  useQuery({
    queryKey: ["studies"],
    queryFn: () => api.get<Study[]>("studies"),
  });

export const useOverview = () =>
  useQuery({
    queryKey: ["overview"],
    queryFn: () => api.get<Overview>("analytics/overview"),
  });

export const useResponses = (params?: {
  questionId?: string;
  kind?: string;
  includeSynthetic?: boolean;
  enabled?: boolean;
}) =>
  useQuery({
    queryKey: ["responses", params],
    enabled: params?.enabled ?? true,
    queryFn: () => {
      const search = new URLSearchParams();
      if (params?.questionId) search.set("question_id", params.questionId);
      if (params?.kind) search.set("kind", params.kind);
      if (params?.includeSynthetic === false) search.set("include_synthetic", "false");
      const qs = search.toString();
      return api.get<ResponseRow[]>(`responses${qs ? `?${qs}` : ""}`);
    },
  });

/** Models grouped by provider, enabled first — the shape the pickers need. */
export function groupModels(models: ModelEntry[] | undefined) {
  const byProvider = new Map<string, ModelEntry[]>();
  for (const model of models ?? []) {
    const list = byProvider.get(model.provider) ?? [];
    list.push(model);
    byProvider.set(model.provider, list);
  }
  for (const list of byProvider.values()) {
    list.sort((a, b) => Number(b.is_enabled) - Number(a.is_enabled) || a.model_id.localeCompare(b.model_id));
  }
  return byProvider;
}

export function modelKey(model: { provider: string; model_id: string }) {
  return `${model.provider}::${model.model_id}`;
}

export function parseModelKey(key: string): { provider: string; model_id: string } {
  const [provider, model_id] = key.split("::");
  return { provider, model_id };
}
