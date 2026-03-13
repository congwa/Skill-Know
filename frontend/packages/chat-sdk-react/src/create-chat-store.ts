/**
 * Zustand Chat Store Factory
 *
 * 提供开箱即用的聊天状态管理，消除各项目重复的 store 代码。
 *
 * 最简用法：
 * ```typescript
 * import { create } from "zustand";
 * import { createChatStoreSlice } from "@embedease/chat-sdk-react";
 *
 * export const useChatStore = create(createChatStoreSlice({ baseUrl: "/api" }));
 * ```
 *
 * 自定义事件：
 * ```typescript
 * import { create } from "zustand";
 * import { createChatStoreSlice, composeReducers } from "@embedease/chat-sdk-react";
 *
 * export const useChatStore = create(
 *   createChatStoreSlice({
 *     baseUrl: "/api",
 *     reducer: composeReducers(myBusinessReducer),
 *     onEvent: (event, api) => { ... },
 *     onStreamEnd: (result, api) => { ... },
 *   })
 * );
 * ```
 */

import {
  ChatClient,
  createInitialState,
  addUserMessage as sdkAddUserMessage,
  startAssistantTurn as sdkStartAssistantTurn,
  timelineReducer as sdkTimelineReducer,
  endTurn as sdkEndTurn,
  clearTurn as sdkClearTurn,
  historyToTimeline as sdkHistoryToTimeline,
  type ChatEvent,
  type ChatRequest,
  type ImageAttachment,
  type HistoryMessage,
  type TimelineState,
  type TimelineItemBase,
  type TimelineItem,
} from "@embedease/chat-sdk";

// ==================== 类型定义 ====================

export interface ChatStoreApi<T extends TimelineItemBase = TimelineItem> {
  getState: () => ChatStoreState<T>;
  setState: (partial: Partial<ChatStoreState<T>>) => void;
}

export interface StreamEndResult {
  conversationId: string;
  assistantMessageId: string;
  fullContent: string;
}

export interface CreateChatStoreOptions<T extends TimelineItemBase = TimelineItem> {
  /** API 基础 URL */
  baseUrl: string | (() => string);
  /** 自定义请求头 */
  headers?: Record<string, string> | (() => Record<string, string>);
  /**
   * 自定义 reducer（默认使用 SDK 内置 reducer）
   * 推荐使用 composeReducers() 组合自定义 reducer
   */
  reducer?: (
    state: TimelineState<T>,
    event: ChatEvent | Record<string, unknown>
  ) => TimelineState<T>;
  /**
   * 事件中间件：每个 SSE 事件到达时调用
   * 可用于：提取 conversation_id、注入自定义字段等
   * 返回 event 继续处理，返回 null 跳过此事件的 reducer 处理
   */
  onEvent?: (event: ChatEvent, api: ChatStoreApi<T>) => ChatEvent | null;
  /**
   * 流结束回调
   * 可用于：落库、通知等
   */
  onStreamEnd?: (
    result: StreamEndResult,
    api: ChatStoreApi<T>
  ) => void | Promise<void>;
  /**
   * 错误回调
   */
  onError?: (error: Error, api: ChatStoreApi<T>) => void;
  /**
   * 构建 ChatRequest 的钩子
   * 默认行为：{ user_id, conversation_id, message, images }
   * 可用于：添加自定义字段等
   */
  buildRequest?: (params: {
    message: string;
    conversationId: string;
    userId: string;
    images?: ImageAttachment[];
  }) => ChatRequest;
  /** 初始 user_id（默认 "default_user"） */
  userId?: string;
  /** 自定义聊天 API 路径（默认 "/api/v1/chat"） */
  chatEndpoint?: string;
}

export interface ChatStoreState<T extends TimelineItemBase = TimelineItem> {
  /** Timeline 状态 */
  timelineState: TimelineState<T>;
  /** 当前会话 ID */
  conversationId: string;
  /** 当前用户 ID */
  userId: string;
  /** 是否正在流式传输 */
  isStreaming: boolean;
  /** 错误信息 */
  error: string | null;

  /** 发送消息（添加到 timeline + 触发 API 请求） */
  sendMessage: (message: string, images?: ImageAttachment[]) => Promise<void>;
  /** 仅添加用户消息到 timeline（不触发 API 请求，适用于 WebSocket 等外部通道） */
  addUserMessageOnly: (message: string) => void;
  /** 中止当前流 */
  abortStream: () => void;
  /** 清空消息 */
  clearMessages: () => void;
  /** 设置会话 ID */
  setConversationId: (id: string) => void;
  /** 设置用户 ID */
  setUserId: (id: string) => void;
  /** 从历史消息初始化 */
  initFromHistory: (messages: HistoryMessage[]) => void;
  /** 直接设置 timeline 状态 */
  setTimelineState: (state: TimelineState<T>) => void;
}

// ==================== Store Factory ====================

/**
 * 创建聊天 Store Slice
 *
 * 返回一个符合 zustand create() API 的 state creator 函数。
 *
 * @example
 * ```typescript
 * import { create } from "zustand";
 * import { createChatStoreSlice } from "@embedease/chat-sdk-react";
 *
 * export const useChatStore = create(createChatStoreSlice({ baseUrl: "/api" }));
 * ```
 */
export function createChatStoreSlice<
  T extends TimelineItemBase = TimelineItem,
>(options: CreateChatStoreOptions<T>) {
  type State = ChatStoreState<T>;
  type SetFn = (
    partial:
      | Partial<State>
      | ((state: State) => Partial<State>)
  ) => void;
  type GetFn = () => State;

  return (set: SetFn, get: GetFn): State => {
    let client: ChatClient | null = null;
    let currentTurnId: string | null = null;

    function getClient(): ChatClient {
      const baseUrl =
        typeof options.baseUrl === "function"
          ? options.baseUrl()
          : options.baseUrl;
      const headers =
        typeof options.headers === "function"
          ? options.headers()
          : options.headers;
      client = new ChatClient({ baseUrl, headers, chatEndpoint: options.chatEndpoint });
      return client;
    }

    const reducer =
      options.reducer ??
      ((state: TimelineState<T>, event: ChatEvent | Record<string, unknown>) => {
        return sdkTimelineReducer(
          state as TimelineState,
          event as ChatEvent
        ) as unknown as TimelineState<T>;
      });

    const api: ChatStoreApi<T> = {
      getState: get,
      setState: (partial) => set(partial),
    };

    return {
      timelineState: createInitialState() as TimelineState<T>,
      conversationId: "",
      userId: options.userId || "default_user",
      isStreaming: false,
      error: null,

      sendMessage: async (message: string, images?: ImageAttachment[]) => {
        const state = get();
        if (state.isStreaming) return;

        const userId = state.userId;
        const conversationId = state.conversationId || crypto.randomUUID();
        const userMessageId = crypto.randomUUID();
        const assistantTurnId = crypto.randomUUID();
        currentTurnId = assistantTurnId;

        let timelineState = state.timelineState;
        timelineState = sdkAddUserMessage(
          timelineState,
          userMessageId,
          message,
          images
        );
        timelineState = sdkStartAssistantTurn(timelineState, assistantTurnId);

        set({
          timelineState,
          conversationId,
          isStreaming: true,
          error: null,
        } as Partial<State>);

        const request: ChatRequest = options.buildRequest
          ? options.buildRequest({ message, conversationId, userId, images })
          : {
              user_id: userId,
              conversation_id: conversationId,
              message,
              ...(images && images.length > 0 ? { images } : {}),
            };

        let fullContent = "";
        let finalConversationId = conversationId;
        let assistantMessageId: string = assistantTurnId;

        try {
          const chatClient = getClient();

          for await (const event of chatClient.stream(request)) {
            if (event.type === "meta.start") {
              const payload = event.payload as Record<string, unknown>;
              if (payload.assistant_message_id) {
                assistantMessageId = payload.assistant_message_id as string;
                currentTurnId = assistantMessageId;
              }
              if (event.conversation_id) {
                finalConversationId = event.conversation_id;
              }
            }

            if (event.type === "assistant.delta") {
              const payload = event.payload as { delta?: string };
              fullContent += payload.delta || "";
            } else if (event.type === "assistant.final") {
              const payload = event.payload as { content?: string };
              fullContent = payload.content || fullContent;
            }

            let processedEvent: ChatEvent | null = event;
            if (options.onEvent) {
              processedEvent = options.onEvent(event, api);
            }

            if (processedEvent) {
              set((s) => ({
                timelineState: reducer(s.timelineState, processedEvent!),
                conversationId: finalConversationId,
              }));
            }
          }

          currentTurnId = null;
          set((s) => ({
            timelineState: sdkEndTurn(s.timelineState) as TimelineState<T>,
            isStreaming: false,
          }));

          if (options.onStreamEnd) {
            await options.onStreamEnd(
              {
                conversationId: finalConversationId,
                assistantMessageId,
                fullContent,
              },
              api
            );
          }
        } catch (error) {
          const turnToClean = currentTurnId;
          currentTurnId = null;
          if (error instanceof Error && error.name === "AbortError") {
            if (turnToClean) {
              set((s) => ({
                timelineState: sdkClearTurn(s.timelineState, turnToClean) as TimelineState<T>,
                isStreaming: false,
              }));
            } else {
              set({ isStreaming: false } as Partial<State>);
            }
            return;
          }
          const errorMessage =
            error instanceof Error ? error.message : String(error);
          if (turnToClean) {
            set((s) => ({
              timelineState: sdkClearTurn(s.timelineState, turnToClean) as TimelineState<T>,
              isStreaming: false,
              error: errorMessage,
            }));
          } else {
            set({
              error: errorMessage,
              isStreaming: false,
            } as Partial<State>);
          }
          if (options.onError && error instanceof Error) {
            options.onError(error, api);
          }
        }
      },

      abortStream: () => {
        if (client) {
          client.abort();
        }
        const turnToClean = currentTurnId;
        currentTurnId = null;
        if (turnToClean) {
          set((s) => ({
            timelineState: sdkClearTurn(s.timelineState, turnToClean) as TimelineState<T>,
            isStreaming: false,
          }));
        } else {
          set({ isStreaming: false } as Partial<State>);
        }
      },

      clearMessages: () => {
        set({
          timelineState: createInitialState() as TimelineState<T>,
          error: null,
        } as Partial<State>);
      },

      setConversationId: (id: string) => {
        set({ conversationId: id } as Partial<State>);
      },

      setUserId: (id: string) => {
        set({ userId: id } as Partial<State>);
      },

      initFromHistory: (messages: HistoryMessage[]) => {
        set({
          timelineState: sdkHistoryToTimeline(messages) as unknown as TimelineState<T>,
        } as Partial<State>);
      },

      setTimelineState: (timelineState: TimelineState<T>) => {
        set({ timelineState } as Partial<State>);
      },

      addUserMessageOnly: (message: string) => {
        const userMessageId = crypto.randomUUID();
        set((s) => ({
          timelineState: sdkAddUserMessage(
            s.timelineState,
            userMessageId,
            message
          ) as TimelineState<T>,
        }));
      },
    };
  };
}

// ==================== Extended Store Helper ====================

/**
 * 创建带扩展字段的聊天 Store
 *
 * 解决消费方在 `create<ExtendedState>()` 时需要 `as any` 类型断言的问题。
 *
 * @example
 * ```typescript
 * import { create } from "zustand";
 * import { createExtendedChatStore } from "@embedease/chat-sdk-react";
 *
 * interface MyState extends ChatStoreState {
 *   customField: string;
 *   setCustomField: (v: string) => void;
 * }
 *
 * export const useChatStore = create<MyState>(
 *   createExtendedChatStore(
 *     { baseUrl: "/api" },
 *     (sdkSlice, set) => ({
 *       customField: "",
 *       setCustomField: (v) => set({ customField: v }),
 *     })
 *   )
 * );
 * ```
 */
export function createExtendedChatStore<
  T extends TimelineItemBase = TimelineItem,
  Extra extends Record<string, unknown> = Record<string, never>,
>(
  options: CreateChatStoreOptions<T>,
  extend: (
    sdkSlice: ChatStoreState<T>,
    set: (partial: Partial<ChatStoreState<T> & Extra> | ((state: ChatStoreState<T> & Extra) => Partial<ChatStoreState<T> & Extra>)) => void,
    get: () => ChatStoreState<T> & Extra
  ) => Extra
) {
  const sliceCreator = createChatStoreSlice<T>(options);

  return (
    set: (partial: Partial<ChatStoreState<T> & Extra> | ((state: ChatStoreState<T> & Extra) => Partial<ChatStoreState<T> & Extra>)) => void,
    get: () => ChatStoreState<T> & Extra
  ): ChatStoreState<T> & Extra => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const sdkSlice = sliceCreator(set as any, get as any);
    const extra = extend(sdkSlice, set, get);
    return { ...sdkSlice, ...extra } as ChatStoreState<T> & Extra;
  };
}
