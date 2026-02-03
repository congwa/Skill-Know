/**
 * 搜索状态 Store
 */

import { create } from "zustand";
import {
  unifiedSearch,
  sqlSearch,
  listTables,
  type SearchResult,
  type SqlSearchResult,
} from "@/lib/api/search";

interface TableInfo {
  name: string;
  description: string;
  columns: string[];
}

type SearchType = "unified" | "sql";

interface SearchState {
  // 查询
  query: string;
  sqlQuery: string;
  searchType: SearchType;

  // 结果
  results: SearchResult | null;
  sqlResults: SqlSearchResult | null;

  // 状态
  isSearching: boolean;
  tables: TableInfo[];

  // Actions
  setQuery: (query: string) => void;
  setSqlQuery: (query: string) => void;
  setSearchType: (type: SearchType) => void;
  search: () => Promise<void>;
  executeSql: () => Promise<void>;
  loadTables: () => Promise<void>;
  clear: () => void;
}

export const useSearchStore = create<SearchState>()((set, get) => ({
  query: "",
  sqlQuery: "",
  searchType: "unified",
  results: null,
  sqlResults: null,
  isSearching: false,
  tables: [],

  setQuery: (query: string) => {
    set({ query });
  },

  setSqlQuery: (query: string) => {
    set({ sqlQuery: query });
  },

  setSearchType: (type: SearchType) => {
    set({ searchType: type });
  },

  search: async () => {
    const { query } = get();
    if (!query.trim()) return;

    set({ isSearching: true });
    try {
      const results = await unifiedSearch(query);
      set({ results, isSearching: false });
    } catch (error) {
      console.error("搜索失败:", error);
      set({ isSearching: false });
    }
  },

  executeSql: async () => {
    const { sqlQuery } = get();
    if (!sqlQuery.trim()) return;

    set({ isSearching: true });
    try {
      const sqlResults = await sqlSearch(sqlQuery);
      set({ sqlResults, isSearching: false });
    } catch (error) {
      console.error("SQL 查询失败:", error);
      set({ isSearching: false });
    }
  },

  loadTables: async () => {
    try {
      const result = await listTables();
      set({ tables: result.tables });
    } catch (error) {
      console.error("加载表信息失败:", error);
    }
  },

  clear: () => {
    set({
      query: "",
      sqlQuery: "",
      results: null,
      sqlResults: null,
    });
  },
}));
