/**
 * 业务扩展 Reducer
 *
 * 包装 SDK 的 timelineReducer，先处理业务特有事件，
 * 其他事件交给 SDK 处理。
 */

import {
  composeReducers as sdkComposeReducers,
  insertItem,
  removeWaitingItem,
  type TimelineState,
  type TimelineItemBase,
  type ChatEvent,
  type CustomReducer,
} from "@embedease/chat-sdk";
import type {
  IntentExtractedItem,
  SearchResultsItem,
  ToolsRegisteredItem,
  PhaseChangedItem,
} from "./types";

/**
 * 业务扩展 Reducer
 *
 * 符合 SDK CustomReducer 协议：
 * - 处理 Skill-Know 特有的事件类型，返回 TimelineState
 * - 未识别的事件返回 null，交给 SDK 内置 reducer 兜底
 */
export const businessReducer: CustomReducer<TimelineItemBase> = (state, event) => {
  const turnId = state.activeTurn.turnId;
  const now = Date.now();
  const evt = event as Record<string, unknown>;
  const eventType = evt.type as string;
  const eventSeq = evt.seq as number;
  const eventPayload = evt.payload as Record<string, unknown>;

  switch (eventType) {
    case "intent.extracted": {
      if (!turnId) return state;
      const stateWithoutWaiting = removeWaitingItem(state, turnId);
      const item: IntentExtractedItem = {
        type: "intent.extracted",
        id: `intent:${eventSeq}`,
        turnId,
        keywords: (eventPayload.keywords as string[]) || [],
        originalQuery: (eventPayload.original_query as string) || "",
        ts: now,
      };
      // 使用类型断言，因为业务类型不在 SDK 的 TimelineItem 联合类型中
      return insertItem(stateWithoutWaiting, item as unknown as Parameters<typeof insertItem>[1]);
    }

    case "search.results.found": {
      if (!turnId) return state;
      const item: SearchResultsItem = {
        type: "search.results",
        id: `search:${eventSeq}`,
        turnId,
        count: (eventPayload.count as number) || 0,
        skills: (eventPayload.skills as SearchResultsItem["skills"]) || [],
        ts: now,
      };
      return insertItem(state, item as unknown as Parameters<typeof insertItem>[1]);
    }

    case "tools.registered": {
      if (!turnId) return state;
      const item: ToolsRegisteredItem = {
        type: "tools.registered",
        id: `tools:${eventSeq}`,
        turnId,
        baseTools: (eventPayload.base_tools as string[]) || [],
        skillTools: (eventPayload.skill_tools as ToolsRegisteredItem["skillTools"]) || [],
        totalCount: (eventPayload.total_count as number) || 0,
        ts: now,
      };
      return insertItem(state, item as unknown as Parameters<typeof insertItem>[1]);
    }

    case "phase.changed": {
      if (!turnId) return state;
      const item: PhaseChangedItem = {
        type: "phase.changed",
        id: `phase:${eventSeq}`,
        turnId,
        fromPhase: (eventPayload.from_phase as string) || "",
        toPhase: (eventPayload.to_phase as string) || "",
        keywords: eventPayload.keywords as string[] | undefined,
        skillCount: eventPayload.skill_count as number | undefined,
        skillIds: eventPayload.skill_ids as string[] | undefined,
        ts: now,
      };
      return insertItem(state, item as unknown as Parameters<typeof insertItem>[1]);
    }

    default:
      // 未识别的事件，交给 SDK 内置 reducer 兜底
      return null;
  }
};

// 使用 SDK composeReducers 组合：businessReducer → SDK 内置 timelineReducer
const _composedReducer = sdkComposeReducers<TimelineItemBase>(businessReducer);

/**
 * 组合后的 Timeline reducer
 *
 * 内部使用 SDK composeReducers，对外保持 TimelineState 类型兼容
 */
export function timelineReducer(
  state: TimelineState,
  event: ChatEvent | Record<string, unknown>
): TimelineState {
  // ChatEvent 联合类型需要先转为 Record 以满足 composeReducers 签名
  const evt = event as Record<string, unknown>;
  return _composedReducer(state, evt) as TimelineState;
}
