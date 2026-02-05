/**
 * 聊天状态管理 Store
 */

import { create } from "zustand";
import {
  type TimelineState,
  type TimelineItem,
  type ChatEvent,
  createInitialState,
  addUserMessage,
  startAssistantTurn,
  clearTurn,
  endTurn,
  historyToTimeline,
  ChatClient,
} from "@embedease/chat-sdk";
import { timelineReducer, type BusinessTimelineItem } from "@/lib/sdk-extensions";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const chatClient = new ChatClient({ baseUrl: API_BASE_URL });

interface StreamController {
  abort: () => void;
}

interface ChatState {
  timelineState: TimelineState;
  isLoading: boolean;
  error: string | null;
  streamController: StreamController | null;
  isStreaming: boolean;
  conversationId: string | null;

  timeline: () => (TimelineItem | BusinessTimelineItem)[];
  currentTurnId: () => string | null;

  sendMessage: (content: string) => Promise<void>;
  clearMessages: () => void;
  abortStream: () => void;
  setConversationId: (id: string | null) => void;
  loadHistory: (
    messages: Array<{ id: string; role: string; content: string }>
  ) => void;

  _handleEvent: (event: ChatEvent | Record<string, unknown>) => void;
  _reset: () => void;
}

export const useChatStore = create<ChatState>()((set, get) => ({
  timelineState: createInitialState(),
  isLoading: false,
  error: null,
  streamController: null,
  isStreaming: false,
  conversationId: null,

  timeline: () => get().timelineState.timeline,
  currentTurnId: () => get().timelineState.activeTurn.turnId,

  loadHistory: (messages) => {
    const typedMessages = messages.map((m) => ({
      id: m.id,
      role: m.role as "user" | "assistant" | "system",
      content: m.content,
    }));
    const newState = historyToTimeline(typedMessages);
    set({ timelineState: newState });
  },

  sendMessage: async (content: string) => {
    if (!content.trim()) return;

    const currentConversationId = get().conversationId;
    set({ error: null });

    const userMessageId = crypto.randomUUID();
    set((state) => ({
      timelineState: addUserMessage(
        state.timelineState,
        userMessageId,
        content.trim()
      ),
    }));

    const assistantTurnId = crypto.randomUUID();
    set((state) => ({
      timelineState: startAssistantTurn(state.timelineState, assistantTurnId),
      isStreaming: true,
    }));

    const controller: StreamController = { abort: () => {} };
    set({ streamController: controller });

    try {
      let aborted = false;
      controller.abort = () => {
        aborted = true;
      };

      for await (const event of chatClient.stream({
        user_id: "default_user",
        conversation_id: currentConversationId || crypto.randomUUID(),
        message: content.trim(),
      })) {
        if (aborted) break;

        // 更新 conversationId
        if (event.type === "meta.start" && event.conversation_id) {
          set({ conversationId: event.conversation_id });
        }

        get()._handleEvent(event);
      }

      if (!aborted) {
        set((state) => ({
          timelineState: endTurn(state.timelineState),
          isStreaming: false,
        }));
      }
    } catch (err) {
      if (err instanceof Error && err.name !== "AbortError") {
        set({ error: err.message });
        set((state) => ({
          timelineState: clearTurn(state.timelineState, assistantTurnId),
        }));
      }
    } finally {
      set({ streamController: null, isStreaming: false });
    }
  },

  clearMessages: () => {
    set({
      timelineState: createInitialState(),
      error: null,
      conversationId: null,
    });
  },

  abortStream: () => {
    const controller = get().streamController;
    if (controller) {
      controller.abort();
      const currentTurnId = get().timelineState.activeTurn.turnId;
      if (currentTurnId) {
        set((state) => ({
          timelineState: clearTurn(state.timelineState, currentTurnId),
        }));
      }
      set({ streamController: null, isStreaming: false });
    }
  },

  setConversationId: (id) => {
    set({ conversationId: id });
  },

  _handleEvent: (event: ChatEvent | Record<string, unknown>) => {
    set((state) => ({
      timelineState: timelineReducer(state.timelineState, event as ChatEvent),
    }));
  },

  _reset: () => {
    const controller = get().streamController;
    if (controller) {
      controller.abort();
    }
    set({
      timelineState: createInitialState(),
      isLoading: false,
      error: null,
      streamController: null,
      isStreaming: false,
      conversationId: null,
    });
  },
}));
