/**
 * 业务扩展 Reducer
 *
 * 包装 SDK 的 timelineReducer，先处理业务特有事件，
 * 其他事件交给 SDK 处理。
 */

import {
  timelineReducer as sdkReducer,
  insertItem,
  removeWaitingItem,
  type TimelineState,
  type ChatEvent,
} from "@embedease/chat-sdk";
import type {
  IntentExtractedItem,
  SearchResultsItem,
  ToolsRegisteredItem,
  PhaseChangedItem,
} from "./types";

/** 业务事件基础结构 */
interface BusinessEvent {
  type: string;
  seq: number;
  payload: Record<string, unknown>;
}

/** 扩展的事件类型（包含业务事件） */
type ExtendedEvent = ChatEvent | BusinessEvent;

/**
 * 业务扩展 Reducer
 *
 * 处理 Skill-Know 特有的事件类型，其他事件交给 SDK 处理
 */
export function businessReducer(
  state: TimelineState,
  event: ExtendedEvent
): TimelineState {
  const turnId = state.activeTurn.turnId;
  const now = Date.now();
  const eventType = event.type;
  const eventSeq = event.seq;
  const eventPayload = event.payload as Record<string, unknown>;

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
      // 其他事件交给 SDK 处理
      return sdkReducer(state, event as ChatEvent);
  }
}

// 为了兼容性，也导出为 timelineReducer
export { businessReducer as timelineReducer };
