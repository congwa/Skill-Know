/**
 * Timeline 状态操作函数
 */

import type { TimelineState, UserMessageItem, WaitingItem } from "./types";
import { createInitialState, insertItem } from "./helpers";

/** 添加用户消息 */
export function addUserMessage(
  state: TimelineState,
  messageId: string,
  content: string
): TimelineState {
  const turnId = messageId;
  const userItem: UserMessageItem = {
    type: "user.message",
    id: messageId,
    turnId,
    content,
    ts: Date.now(),
  };
  return insertItem(state, userItem);
}

/** 开始助手回复轮次 */
export function startAssistantTurn(
  state: TimelineState,
  turnId: string
): TimelineState {
  const waitingItem: WaitingItem = {
    type: "waiting",
    id: `waiting-${turnId}`,
    turnId,
    ts: Date.now(),
  };
  const newState = insertItem(state, waitingItem);
  return {
    ...newState,
    activeTurn: {
      turnId,
      currentLlmCallId: null,
      currentToolCallId: null,
      isStreaming: true,
    },
  };
}

/** 结束当前轮次 */
export function endTurn(state: TimelineState): TimelineState {
  return {
    ...state,
    activeTurn: {
      turnId: null,
      currentLlmCallId: null,
      currentToolCallId: null,
      isStreaming: false,
    },
  };
}

/** 清除指定轮次（中止时使用） */
export function clearTurn(state: TimelineState, turnId: string): TimelineState {
  const timeline = state.timeline.filter((item) => item.turnId !== turnId);
  const indexById: Record<string, number> = {};
  timeline.forEach((item, i) => {
    indexById[item.id] = i;
  });
  return {
    ...state,
    timeline,
    indexById,
    activeTurn: {
      turnId: null,
      currentLlmCallId: null,
      currentToolCallId: null,
      isStreaming: false,
    },
  };
}

/** 从历史消息构建 timeline */
export function historyToTimeline(
  messages: Array<{
    id: string;
    role: "user" | "assistant" | "system";
    content: string;
  }>
): TimelineState {
  let state = createInitialState();

  for (const msg of messages) {
    if (msg.role === "user") {
      const userItem: UserMessageItem = {
        type: "user.message",
        id: msg.id,
        turnId: msg.id,
        content: msg.content,
        ts: Date.now(),
      };
      state = insertItem(state, userItem);
    } else if (msg.role === "assistant") {
      // 助手消息作为已完成的 LLM cluster
      const clusterId = `cluster-${msg.id}`;
      state = insertItem(state, {
        type: "llm.call.cluster",
        id: clusterId,
        turnId: msg.id,
        status: "success",
        children: [
          {
            type: "content",
            id: `content-${msg.id}`,
            text: msg.content,
            ts: Date.now(),
          },
        ],
        childIndexById: { [`content-${msg.id}`]: 0 },
        ts: Date.now(),
      });
    }
  }

  return state;
}

export { createInitialState };
