/**
 * 提示词 API
 */

import { apiGet, apiPut, apiPost } from "@/lib/api/client";

export type PromptCategory = "system" | "chat" | "skill" | "classification" | "search";
export type PromptSource = "default" | "custom";

export interface Prompt {
  key: string;
  category: PromptCategory;
  name: string;
  description: string | null;
  content: string;
  variables: string[];
  source: PromptSource;
  is_active: boolean;
  default_content: string | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface PromptListResponse {
  items: Prompt[];
  total: number;
}

export interface PromptUpdate {
  name?: string;
  description?: string;
  content?: string;
  is_active?: boolean;
}

export function listPrompts(params?: {
  category?: PromptCategory;
  include_inactive?: boolean;
}): Promise<PromptListResponse> {
  const searchParams = new URLSearchParams();
  if (params?.category) searchParams.set("category", params.category);
  if (params?.include_inactive) searchParams.set("include_inactive", "true");
  
  const query = searchParams.toString();
  return apiGet<PromptListResponse>(`/prompts${query ? `?${query}` : ""}`);
}

export function getPrompt(key: string): Promise<Prompt> {
  return apiGet<Prompt>(`/prompts/${encodeURIComponent(key)}`);
}

export function updatePrompt(key: string, data: PromptUpdate): Promise<Prompt> {
  return apiPut<Prompt>(`/prompts/${encodeURIComponent(key)}`, data);
}

export function resetPrompt(key: string): Promise<Prompt> {
  return apiPost<Prompt>(`/prompts/${encodeURIComponent(key)}/reset`);
}
