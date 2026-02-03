/**
 * 快速设置 API
 */

import { apiGet, apiPost } from "@/lib/api/client";

export interface SetupStep {
  index: number;
  key: string;
  title: string;
  description: string | null;
  status: "pending" | "completed" | "skipped";
  is_required: boolean;
}

export interface QuickSetupState {
  current_step: number;
  steps: SetupStep[];
  essential_completed: boolean;
  setup_level: string;
  data: Record<string, unknown>;
}

export interface ChecklistItem {
  key: string;
  label: string;
  category: string;
  status: "ok" | "default" | "missing" | "error";
  current_value: string | null;
  default_value: string | null;
  description: string | null;
}

export interface ChecklistResponse {
  items: ChecklistItem[];
  total: number;
  ok_count: number;
  default_count: number;
  missing_count: number;
}

export interface EssentialSetupRequest {
  llm_provider: string;
  llm_api_key: string;
  llm_base_url: string;
  llm_chat_model: string;
}

export interface TestConnectionRequest {
  llm_provider: string;
  llm_api_key: string;
  llm_base_url: string;
  llm_chat_model: string;
}

export interface TestConnectionResponse {
  success: boolean;
  message: string;
  latency_ms: number | null;
}

export function getSetupState(): Promise<QuickSetupState> {
  return apiGet<QuickSetupState>("/quick-setup/state");
}

export function getChecklist(): Promise<ChecklistResponse> {
  return apiGet<ChecklistResponse>("/quick-setup/checklist");
}

export function completeEssentialSetup(
  data: EssentialSetupRequest
): Promise<QuickSetupState> {
  return apiPost<QuickSetupState>("/quick-setup/essential", data);
}

export function testConnection(
  data: TestConnectionRequest
): Promise<TestConnectionResponse> {
  return apiPost<TestConnectionResponse>("/quick-setup/test-connection", data);
}

export function resetSetup(): Promise<QuickSetupState> {
  return apiPost<QuickSetupState>("/quick-setup/reset");
}

export interface ModelInfo {
  id: string;
  name: string;
  provider: string;
  tool_calling: boolean;
  structured_output: boolean;
  reasoning: boolean;
  max_input_tokens: number;
  max_output_tokens: number;
}

export interface ProviderInfo {
  id: string;
  name: string;
  base_url: string;
  models: ModelInfo[];
}

export interface ProvidersResponse {
  providers: ProviderInfo[];
}

export interface ProviderModelsResponse {
  provider_id: string;
  base_url: string;
  models: ModelInfo[];
}

export function getProviders(): Promise<ProvidersResponse> {
  return apiGet<ProvidersResponse>("/quick-setup/providers");
}

export function getProviderModels(providerId: string): Promise<ProviderModelsResponse> {
  return apiGet<ProviderModelsResponse>(`/quick-setup/providers/${providerId}/models`);
}
