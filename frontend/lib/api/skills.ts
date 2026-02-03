/**
 * 技能 API
 */

import { apiGet, apiPost, apiPut, apiDelete } from "@/lib/api/client";

export type SkillType = "system" | "document" | "user";
export type SkillCategory = "search" | "prompt" | "retrieval" | "tool" | "workflow";

export interface Skill {
  id: string;
  name: string;
  description: string;
  type: SkillType;
  category: SkillCategory;
  content: string;
  trigger_keywords: string[];
  trigger_intents: string[];
  always_apply: boolean;
  version: string;
  author: string | null;
  is_active: boolean;
  source_document_id: string | null;
  folder_id: string | null;
  priority: number;
  config: Record<string, unknown>;
  is_editable: boolean;
  is_deletable: boolean;
  created_at: string;
  updated_at: string;
}

export interface SkillListResponse {
  items: Skill[];
  total: number;
  page: number;
  page_size: number;
}

export interface SkillCreate {
  name: string;
  description: string;
  category?: SkillCategory;
  content: string;
  trigger_keywords?: string[];
  trigger_intents?: string[];
  always_apply?: boolean;
  folder_id?: string | null;
  priority?: number;
  config?: Record<string, unknown>;
}

export interface SkillUpdate {
  name?: string;
  description?: string;
  category?: SkillCategory;
  content?: string;
  trigger_keywords?: string[];
  trigger_intents?: string[];
  always_apply?: boolean;
  folder_id?: string | null;
  priority?: number;
  is_active?: boolean;
  config?: Record<string, unknown>;
}

export interface SkillSearchRequest {
  query: string;
  category?: SkillCategory;
  type?: SkillType;
  limit?: number;
}

export function listSkills(params?: {
  type?: SkillType;
  category?: SkillCategory;
  folder_id?: string;
  is_active?: boolean;
  page?: number;
  page_size?: number;
}): Promise<SkillListResponse> {
  const searchParams = new URLSearchParams();
  if (params?.type) searchParams.set("type", params.type);
  if (params?.category) searchParams.set("category", params.category);
  if (params?.folder_id) searchParams.set("folder_id", params.folder_id);
  if (params?.is_active !== undefined) searchParams.set("is_active", String(params.is_active));
  if (params?.page) searchParams.set("page", String(params.page));
  if (params?.page_size) searchParams.set("page_size", String(params.page_size));
  
  const query = searchParams.toString();
  return apiGet<SkillListResponse>(`/skills${query ? `?${query}` : ""}`);
}

export function getSkill(skillId: string): Promise<Skill> {
  return apiGet<Skill>(`/skills/${skillId}`);
}

export function createSkill(data: SkillCreate): Promise<Skill> {
  return apiPost<Skill>("/skills", data);
}

export function updateSkill(skillId: string, data: SkillUpdate): Promise<Skill> {
  return apiPut<Skill>(`/skills/${skillId}`, data);
}

export function deleteSkill(skillId: string): Promise<{ success: boolean }> {
  return apiDelete<{ success: boolean }>(`/skills/${skillId}`);
}

export function searchSkills(data: SkillSearchRequest): Promise<{ items: Skill[]; total: number }> {
  return apiPost<{ items: Skill[]; total: number }>("/skills/search", data);
}

export function moveSkill(skillId: string, folderId: string | null): Promise<{ success: boolean }> {
  return apiPost<{ success: boolean }>(`/skills/${skillId}/move`, { folder_id: folderId });
}
