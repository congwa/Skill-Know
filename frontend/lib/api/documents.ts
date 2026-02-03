/**
 * 文档 API
 */

import { apiGet, apiPost, apiPut, apiDelete, getApiBaseUrl } from "@/lib/api/client";

export type DocumentStatus = "pending" | "processing" | "completed" | "failed";

export interface Document {
  id: string;
  title: string;
  description: string | null;
  filename: string;
  file_path: string;
  file_size: number;
  file_type: string;
  content: string | null;
  status: DocumentStatus;
  error_message: string | null;
  category: string | null;
  tags: string[];
  folder_id: string | null;
  metadata: Record<string, unknown>;
  // 技能转化相关
  skill_id: string | null;
  is_converted: boolean;
  converted_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface DocumentFolder {
  id: string;
  name: string;
  description: string | null;
  parent_id: string | null;
  sort_order: number;
  is_system: boolean;
  created_at: string;
  updated_at: string;
}

export interface DocumentListResponse {
  items: Document[];
  total: number;
  page: number;
  page_size: number;
}

export interface DocumentFolderCreate {
  name: string;
  description?: string;
  parent_id?: string;
}

export interface DocumentFolderUpdate {
  name?: string;
  description?: string;
  parent_id?: string;
  sort_order?: number;
}

export interface DocumentUpdate {
  title?: string;
  description?: string;
  folder_id?: string | null;
  category?: string;
  tags?: string[];
}

// 文件夹 API
export function listFolders(parentId?: string): Promise<DocumentFolder[]> {
  const query = parentId ? `?parent_id=${parentId}` : "";
  return apiGet<DocumentFolder[]>(`/documents/folders${query}`);
}

export function getFolder(folderId: string): Promise<DocumentFolder> {
  return apiGet<DocumentFolder>(`/documents/folders/${folderId}`);
}

export function createFolder(data: DocumentFolderCreate): Promise<DocumentFolder> {
  return apiPost<DocumentFolder>("/documents/folders", data);
}

export function updateFolder(folderId: string, data: DocumentFolderUpdate): Promise<DocumentFolder> {
  return apiPut<DocumentFolder>(`/documents/folders/${folderId}`, data);
}

export function deleteFolder(folderId: string): Promise<{ success: boolean }> {
  return apiDelete<{ success: boolean }>(`/documents/folders/${folderId}`);
}

// 文档 API
export function listDocuments(params?: {
  folder_id?: string;
  category?: string;
  status?: DocumentStatus;
  is_converted?: boolean;
  page?: number;
  page_size?: number;
}): Promise<DocumentListResponse> {
  const searchParams = new URLSearchParams();
  if (params?.folder_id) searchParams.set("folder_id", params.folder_id);
  if (params?.category) searchParams.set("category", params.category);
  if (params?.status) searchParams.set("status", params.status);
  if (params?.is_converted !== undefined) searchParams.set("is_converted", String(params.is_converted));
  if (params?.page) searchParams.set("page", String(params.page));
  if (params?.page_size) searchParams.set("page_size", String(params.page_size));
  
  const query = searchParams.toString();
  return apiGet<DocumentListResponse>(`/documents${query ? `?${query}` : ""}`);
}

export function getDocument(documentId: string): Promise<Document> {
  return apiGet<Document>(`/documents/${documentId}`);
}

export async function uploadDocument(
  file: File,
  options?: { title?: string; folder_id?: string }
): Promise<Document> {
  const formData = new FormData();
  formData.append("file", file);
  if (options?.title) formData.append("title", options.title);
  if (options?.folder_id) formData.append("folder_id", options.folder_id);

  const response = await fetch(`${getApiBaseUrl()}/documents/upload`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "上传失败" }));
    throw new Error(error.detail || "上传失败");
  }

  return response.json();
}

export function updateDocument(documentId: string, data: DocumentUpdate): Promise<Document> {
  return apiPut<Document>(`/documents/${documentId}`, data);
}

export function deleteDocument(documentId: string): Promise<{ success: boolean }> {
  return apiDelete<{ success: boolean }>(`/documents/${documentId}`);
}

export function moveDocument(documentId: string, folderId: string | null): Promise<{ success: boolean }> {
  return apiPost<{ success: boolean }>(`/documents/${documentId}/move`, { folder_id: folderId });
}

export function searchDocuments(query: string, limit?: number): Promise<{ items: Document[]; total: number }> {
  const params = new URLSearchParams({ q: query });
  if (limit) params.set("limit", String(limit));
  return apiGet<{ items: Document[]; total: number }>(`/documents/search?${params}`);
}

export interface ConvertToSkillResult {
  success: boolean;
  skill: {
    id: string;
    name: string;
    description: string;
    category: string;
    trigger_keywords: string[];
  } | null;
  analysis: {
    doc_type: string;
    word_count: number;
    complexity: string;
    concepts: string[];
  } | null;
}

export function convertToSkill(
  documentId: string,
  options?: { use_llm?: boolean; folder_id?: string }
): Promise<ConvertToSkillResult> {
  const params = new URLSearchParams();
  if (options?.use_llm !== undefined) params.set("use_llm", String(options.use_llm));
  if (options?.folder_id) params.set("folder_id", options.folder_id);
  const query = params.toString();
  return apiPost<ConvertToSkillResult>(
    `/documents/${documentId}/convert-to-skill${query ? `?${query}` : ""}`,
    {}
  );
}
