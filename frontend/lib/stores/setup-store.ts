/**
 * 快速设置状态 Store
 */

import { create } from "zustand";
import {
  getProviders,
  testConnection,
  completeEssentialSetup,
  type ProviderInfo,
  type ModelInfo,
} from "@/lib/api/quick-setup";
import { useAppStore } from "./app-store";

interface FormData {
  llm_provider: string;
  llm_api_key: string;
  llm_base_url: string;
  llm_chat_model: string;
}

interface TestResult {
  success: boolean;
  message: string;
}

interface SetupState {
  // 提供商数据
  providers: ProviderInfo[];
  selectedProvider: ProviderInfo | null;
  isLoadingProviders: boolean;

  // 表单数据
  formData: FormData;

  // 测试状态
  testResult: TestResult | null;
  isTesting: boolean;
  isSubmitting: boolean;

  // Actions
  loadProviders: () => Promise<void>;
  selectProvider: (providerId: string) => void;
  selectModel: (modelId: string) => void;
  setApiKey: (key: string) => void;
  setBaseUrl: (url: string) => void;
  testConnectionAction: () => Promise<boolean>;
  submitSetup: () => Promise<boolean>;
  reset: () => void;
}

const initialFormData: FormData = {
  llm_provider: "",
  llm_api_key: "",
  llm_base_url: "",
  llm_chat_model: "",
};

export const useSetupStore = create<SetupState>()((set, get) => ({
  providers: [],
  selectedProvider: null,
  isLoadingProviders: true,
  formData: { ...initialFormData },
  testResult: null,
  isTesting: false,
  isSubmitting: false,

  loadProviders: async () => {
    set({ isLoadingProviders: true });
    try {
      const res = await getProviders();
      set({ providers: res.providers });

      // 默认选择 OpenAI 或第一个提供商
      if (res.providers.length > 0) {
        const defaultProvider =
          res.providers.find((p) => p.id === "openai") || res.providers[0];
        get().selectProvider(defaultProvider.id);
      }
    } catch (error) {
      console.error("加载提供商失败:", error);
    } finally {
      set({ isLoadingProviders: false });
    }
  },

  selectProvider: (providerId: string) => {
    const { providers } = get();
    const provider = providers.find((p) => p.id === providerId);
    if (provider) {
      set({
        selectedProvider: provider,
        formData: {
          ...get().formData,
          llm_provider: provider.id,
          llm_base_url: provider.base_url,
          llm_chat_model:
            provider.models.length > 0 ? provider.models[0].id : "",
        },
        testResult: null,
      });
    }
  },

  selectModel: (modelId: string) => {
    set({
      formData: { ...get().formData, llm_chat_model: modelId },
      testResult: null,
    });
  },

  setApiKey: (key: string) => {
    set({
      formData: { ...get().formData, llm_api_key: key },
      testResult: null,
    });
  },

  setBaseUrl: (url: string) => {
    set({
      formData: { ...get().formData, llm_base_url: url },
      testResult: null,
    });
  },

  testConnectionAction: async () => {
    const { formData } = get();
    set({ isTesting: true, testResult: null });

    try {
      const result = await testConnection(formData);
      const testResult = {
        success: result.success,
        message:
          result.message +
          (result.latency_ms ? ` (${result.latency_ms}ms)` : ""),
      };
      set({ testResult, isTesting: false });
      return result.success;
    } catch (error) {
      set({
        testResult: {
          success: false,
          message: error instanceof Error ? error.message : "连接测试失败",
        },
        isTesting: false,
      });
      return false;
    }
  },

  submitSetup: async () => {
    const { formData } = get();
    set({ isSubmitting: true });

    try {
      await completeEssentialSetup(formData);

      // 更新全局应用状态
      useAppStore.getState().setSetupComplete(true);
      useAppStore.getState().setLlmConfig({
        provider: formData.llm_provider,
        model: formData.llm_chat_model,
        baseUrl: formData.llm_base_url,
      });

      set({ isSubmitting: false });
      return true;
    } catch (error) {
      console.error("保存设置失败:", error);
      set({ isSubmitting: false });
      return false;
    }
  },

  reset: () => {
    set({
      providers: [],
      selectedProvider: null,
      isLoadingProviders: true,
      formData: { ...initialFormData },
      testResult: null,
      isTesting: false,
      isSubmitting: false,
    });
  },
}));
