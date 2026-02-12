/**
 * 聊天状态管理 Store
 *
 * 使用 SDK createChatStoreSlice + 自定义 businessReducer
 */

import { create } from "zustand";
import {
  type TimelineState,
  type TimelineItem,
} from "@embedease/chat-sdk";
import {
  createChatStoreSlice,
  type ChatStoreState,
} from "@embedease/chat-sdk-react";
import { timelineReducer, type BusinessTimelineItem } from "@/lib/sdk-extensions";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/** 扩展 SDK store state，添加项目特有的派生 getters */
interface ChatState extends ChatStoreState {
  timeline: () => (TimelineItem | BusinessTimelineItem)[];
  currentTurnId: () => string | null;
  loadHistory: (
    messages: Array<{ id: string; role: string; content: string }>
  ) => void;
}

export const useChatStore = create<ChatState>()((set, get) => {
  // SDK slice 提供核心聊天功能
  const sdkSlice = createChatStoreSlice({
    baseUrl: API_BASE_URL,
    reducer: (state: TimelineState, event) => {
      return timelineReducer(state, event) as TimelineState;
    },
    onEvent: (event, api) => {
      // 从 meta.start 提取 conversationId
      if (event.type === "meta.start" && event.conversation_id) {
        api.setState({ conversationId: event.conversation_id });
      }
      return event;
    },
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  })(set as any, get as any);

  return {
    ...sdkSlice,

    // 派生 getters（向后兼容）
    timeline: () => get().timelineState.timeline,
    currentTurnId: () => get().timelineState.activeTurn.turnId,

    // 历史加载（委托给 SDK initFromHistory）
    loadHistory: (messages) => {
      const typedMessages = messages.map((m) => ({
        id: m.id,
        role: m.role as "user" | "assistant" | "system",
        content: m.content,
      }));
      get().initFromHistory(typedMessages);
    },
  };
});
