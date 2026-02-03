/**
 * 搜索 API
 */

import { apiGet, apiPost } from "@/lib/api/client";

export interface SearchResult {
  query: string;
  skills: {
    id: string;
    name: string;
    description: string;
    type: string;
    category: string;
    content_preview: string;
  }[];
  documents: {
    id: string;
    title: string;
    description: string | null;
    category: string | null;
    content_preview: string | null;
  }[];
  total: number;
}

export interface SqlSearchResult {
  query: string;
  results: Record<string, unknown>[];
  count: number;
  error?: string;
}

export interface TableInfo {
  name: string;
  description: string;
  columns: string[];
}

export function unifiedSearch(
  query: string,
  options?: { type?: "skill" | "document" | "all"; limit?: number }
): Promise<SearchResult> {
  const params = new URLSearchParams({ q: query });
  if (options?.type) params.set("type", options.type);
  if (options?.limit) params.set("limit", String(options.limit));
  return apiGet<SearchResult>(`/search?${params}`);
}

export function sqlSearch(query: string): Promise<SqlSearchResult> {
  return apiPost<SqlSearchResult>(`/search/sql?query=${encodeURIComponent(query)}`);
}

export function listTables(): Promise<{ tables: TableInfo[] }> {
  return apiGet<{ tables: TableInfo[] }>("/search/tables");
}
