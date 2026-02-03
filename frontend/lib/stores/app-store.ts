/**
 * 全局应用状态 Store
 */

import { create } from "zustand";
import { getSetupState } from "@/lib/api/quick-setup";

interface LlmConfig {
  provider: string;
  model: string;
  baseUrl: string;
}

interface AppState {
  // 设置状态
  isSetupComplete: boolean;
  isCheckingSetup: boolean;
  
  // LLM 配置
  llmConfig: LlmConfig | null;
  
  // Actions
  checkSetupStatus: () => Promise<boolean>;
  setSetupComplete: (complete: boolean) => void;
  setLlmConfig: (config: LlmConfig | null) => void;
}

export const useAppStore = create<AppState>()((set, get) => ({
  isSetupComplete: false,
  isCheckingSetup: true,
  llmConfig: null,

  checkSetupStatus: async () => {
    set({ isCheckingSetup: true });
    try {
      const state = await getSetupState();
      const isComplete = state.essential_completed;
      set({ isSetupComplete: isComplete, isCheckingSetup: false });
      
      // 如果设置完成，保存 LLM 配置
      if (isComplete && state.data) {
        const data = state.data as Record<string, string>;
        set({
          llmConfig: {
            provider: data.llm_provider || "",
            model: data.llm_chat_model || "",
            baseUrl: data.llm_base_url || "",
          },
        });
      }
      
      return isComplete;
    } catch (error) {
      console.error("检查设置状态失败:", error);
      set({ isSetupComplete: false, isCheckingSetup: false });
      return false;
    }
  },

  setSetupComplete: (complete: boolean) => {
    set({ isSetupComplete: complete });
  },

  setLlmConfig: (config: LlmConfig | null) => {
    set({ llmConfig: config });
  },
}));
