/**
 * 文档管理状态 Store
 */

import { create } from "zustand";
import {
  listDocuments,
  listFolders,
  getDocument,
  deleteDocument as apiDeleteDocument,
  convertToSkill as apiConvertToSkill,
  type Document,
  type DocumentFolder,
} from "@/lib/api/documents";

interface DocumentState {
  // 数据
  documents: Document[];
  folders: DocumentFolder[];
  selectedDocument: Document | null;
  currentFolderId: string | null;

  // 加载状态
  isLoading: boolean;
  isConverting: boolean;

  // Actions
  loadDocuments: (folderId?: string | null) => Promise<void>;
  loadFolders: () => Promise<void>;
  loadAll: (folderId?: string | null) => Promise<void>;
  selectDocument: (doc: Document | null) => void;
  setCurrentFolder: (folderId: string | null) => void;
  deleteDocument: (id: string) => Promise<boolean>;
  convertToSkill: (id: string) => Promise<boolean>;
  refreshDocument: (id: string) => Promise<void>;
  reset: () => void;
}

export const useDocumentStore = create<DocumentState>()((set, get) => ({
  documents: [],
  folders: [],
  selectedDocument: null,
  currentFolderId: null,
  isLoading: false,
  isConverting: false,

  loadDocuments: async (folderId?: string | null) => {
    set({ isLoading: true });
    try {
      const res = await listDocuments({ folder_id: folderId || undefined });
      set({ documents: res.items, isLoading: false });
    } catch (error) {
      console.error("加载文档失败:", error);
      set({ isLoading: false });
    }
  },

  loadFolders: async () => {
    try {
      const folders = await listFolders();
      set({ folders });
    } catch (error) {
      console.error("加载文件夹失败:", error);
    }
  },

  loadAll: async (folderId?: string | null) => {
    set({ isLoading: true, currentFolderId: folderId || null });
    try {
      const [docsRes, folders] = await Promise.all([
        listDocuments({ folder_id: folderId || undefined }),
        listFolders(),
      ]);
      set({ documents: docsRes.items, folders, isLoading: false });
    } catch (error) {
      console.error("加载数据失败:", error);
      set({ isLoading: false });
    }
  },

  selectDocument: (doc: Document | null) => {
    set({ selectedDocument: doc });
  },

  setCurrentFolder: (folderId: string | null) => {
    set({ currentFolderId: folderId });
    get().loadDocuments(folderId);
  },

  deleteDocument: async (id: string) => {
    try {
      await apiDeleteDocument(id);
      // 从列表中移除
      set((state) => ({
        documents: state.documents.filter((d) => d.id !== id),
        selectedDocument:
          state.selectedDocument?.id === id ? null : state.selectedDocument,
      }));
      return true;
    } catch (error) {
      console.error("删除文档失败:", error);
      return false;
    }
  },

  convertToSkill: async (id: string) => {
    set({ isConverting: true });
    try {
      const result = await apiConvertToSkill(id);
      if (result.success) {
        // 刷新文档
        await get().refreshDocument(id);
      }
      set({ isConverting: false });
      return result.success;
    } catch (error) {
      console.error("转换失败:", error);
      set({ isConverting: false });
      return false;
    }
  },

  refreshDocument: async (id: string) => {
    try {
      const doc = await getDocument(id);
      if (doc) {
        set((state) => ({
          documents: state.documents.map((d) => (d.id === id ? doc : d)),
          selectedDocument:
            state.selectedDocument?.id === id ? doc : state.selectedDocument,
        }));
      }
    } catch (error) {
      console.error("刷新文档失败:", error);
    }
  },

  reset: () => {
    set({
      documents: [],
      folders: [],
      selectedDocument: null,
      currentFolderId: null,
      isLoading: false,
      isConverting: false,
    });
  },
}));
