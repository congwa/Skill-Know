/**
 * Timeline reducer 函数
 */

import type {
  ChatEvent,
  TimelineState,
  LLMCallClusterItem,
  ToolCallItem,
  ErrorItem,
  FinalItem,
  SkillActivatedItem,
  IntentExtractedItem,
  SearchResultsItem,
  ToolsRegisteredItem,
  PhaseChangedItem,
  ReasoningSubItem,
  ContentSubItem,
} from "./types";
import {
  getToolLabel,
  insertItem,
  updateItemById,
  getCurrentLlmCluster,
  appendSubItemToCurrentCluster,
  updateSubItemInCurrentCluster,
  getLastSubItemOfType,
  removeWaitingItem,
} from "./helpers";

export function timelineReducer(
  state: TimelineState,
  event: ChatEvent
): TimelineState {
  const turnId = state.activeTurn.turnId;
  const now = Date.now();

  if (!turnId && event.type !== "meta.start") return state;

  switch (event.type) {
    case "meta.start": {
      const payload = event.payload as { assistant_message_id?: string };
      const oldTurnId = turnId;
      const newTurnId = payload.assistant_message_id || event.message_id;

      if (newTurnId && newTurnId !== oldTurnId) {
        const timeline = state.timeline.map((item) => {
          if (item.turnId === oldTurnId) {
            if (item.type === "waiting") {
              return { ...item, id: `waiting-${newTurnId}`, turnId: newTurnId };
            }
            return { ...item, turnId: newTurnId };
          }
          return item;
        });
        const indexById: Record<string, number> = {};
        timeline.forEach((item, i) => {
          indexById[item.id] = i;
        });
        return {
          ...state,
          timeline,
          indexById,
          activeTurn: { ...state.activeTurn, turnId: newTurnId },
        };
      }
      return state;
    }

    case "llm.call.start": {
      if (!turnId) return state;
      const stateWithoutWaiting = removeWaitingItem(state, turnId);

      const payload = event.payload as {
        llm_call_id?: string;
        message_count?: number;
      };
      const llmCallId = payload.llm_call_id || crypto.randomUUID();
      const cluster: LLMCallClusterItem = {
        type: "llm.call.cluster",
        id: llmCallId,
        turnId,
        status: "running",
        messageCount: payload.message_count,
        children: [],
        childIndexById: {},
        ts: now,
      };
      const newState = insertItem(stateWithoutWaiting, cluster);
      return {
        ...newState,
        activeTurn: {
          ...newState.activeTurn,
          currentLlmCallId: llmCallId,
          currentToolCallId: null,
        },
      };
    }

    case "llm.call.end": {
      const payload = event.payload as {
        llm_call_id?: string;
        elapsed_ms?: number;
        error?: string;
      };
      const llmCallId = payload.llm_call_id;
      const hasError = !!payload.error;
      const targetId = llmCallId || state.activeTurn.currentLlmCallId;
      if (!targetId) return state;

      const newState = updateItemById(state, targetId, (item) => {
        if (item.type !== "llm.call.cluster") return item;
        return {
          ...item,
          status: hasError ? "error" : "success",
          elapsedMs: payload.elapsed_ms,
          error: payload.error,
        };
      });

      return {
        ...newState,
        activeTurn: {
          ...newState.activeTurn,
          currentLlmCallId: null,
        },
      };
    }

    case "assistant.final": {
      if (!turnId) return state;
      const payload = event.payload as { content?: string };

      let newState = state;
      for (const item of state.timeline) {
        if (item.type === "llm.call.cluster" && item.turnId === turnId) {
          newState = updateItemById(newState, item.id, (cluster) => {
            if (cluster.type !== "llm.call.cluster") return cluster;
            const children = cluster.children.map((child) =>
              child.type === "reasoning" && child.isOpen
                ? { ...child, isOpen: false }
                : child
            );
            return { ...cluster, children };
          });
        }
      }

      const finalItem: FinalItem = {
        type: "final",
        id: `final:${event.seq}`,
        turnId,
        content: payload.content,
        ts: now,
      };
      newState = insertItem(newState, finalItem);

      return {
        ...newState,
        activeTurn: { ...newState.activeTurn, isStreaming: false },
      };
    }

    case "error": {
      if (!turnId) return state;
      const payload = event.payload as { message?: string };
      const item: ErrorItem = {
        type: "error",
        id: `error:${event.seq}`,
        turnId,
        message: payload.message || "未知错误",
        ts: now,
      };
      return insertItem(state, item);
    }

    case "assistant.reasoning.delta": {
      const payload = event.payload as { delta?: string };
      const delta = payload.delta;
      if (!delta) return state;

      const cluster = getCurrentLlmCluster(state);
      if (!cluster) return state;

      const lastReasoning = getLastSubItemOfType<ReasoningSubItem>(
        cluster,
        "reasoning"
      );
      if (lastReasoning) {
        return updateSubItemInCurrentCluster(state, lastReasoning.id, (sub) => {
          if (sub.type !== "reasoning") return sub;
          return { ...sub, text: sub.text + delta };
        });
      }

      const subItem: ReasoningSubItem = {
        type: "reasoning",
        id: crypto.randomUUID(),
        text: delta,
        isOpen: true,
        ts: now,
      };
      return appendSubItemToCurrentCluster(state, subItem);
    }

    case "assistant.delta": {
      const payload = event.payload as { delta?: string };
      const delta = payload.delta;
      if (!delta) return state;

      const cluster = getCurrentLlmCluster(state);
      if (!cluster) return state;

      let newState = state;
      const lastReasoning = getLastSubItemOfType<ReasoningSubItem>(
        cluster,
        "reasoning"
      );
      if (lastReasoning && lastReasoning.isOpen) {
        newState = updateSubItemInCurrentCluster(
          newState,
          lastReasoning.id,
          (sub) => {
            if (sub.type !== "reasoning") return sub;
            return { ...sub, isOpen: false };
          }
        );
      }

      const updatedCluster = getCurrentLlmCluster(newState);
      if (!updatedCluster) return newState;
      const lastContent = getLastSubItemOfType<ContentSubItem>(
        updatedCluster,
        "content"
      );
      if (lastContent) {
        return updateSubItemInCurrentCluster(newState, lastContent.id, (sub) => {
          if (sub.type !== "content") return sub;
          return { ...sub, text: sub.text + delta };
        });
      }

      const subItem: ContentSubItem = {
        type: "content",
        id: crypto.randomUUID(),
        text: delta,
        ts: now,
      };
      return appendSubItemToCurrentCluster(newState, subItem);
    }

    case "tool.start": {
      if (!turnId) return state;
      const payload = event.payload as {
        tool_call_id?: string;
        name: string;
        input?: unknown;
      };
      const toolCallId = payload.tool_call_id || crypto.randomUUID();
      const toolItem: ToolCallItem = {
        type: "tool.call",
        id: toolCallId,
        turnId,
        name: payload.name,
        label: getToolLabel(payload.name),
        status: "running",
        input: payload.input,
        startedAt: now,
        ts: now,
      };
      const newState = insertItem(state, toolItem);
      return {
        ...newState,
        activeTurn: {
          ...newState.activeTurn,
          currentToolCallId: toolCallId,
        },
      };
    }

    case "tool.end": {
      const payload = event.payload as {
        tool_call_id?: string;
        status?: string;
        count?: number;
        error?: string;
        output?: unknown;
      };
      const toolCallId = payload.tool_call_id || state.activeTurn.currentToolCallId;
      if (!toolCallId) return state;

      const newState = updateItemById(state, toolCallId, (item) => {
        if (item.type !== "tool.call") return item;
        const elapsedMs = Date.now() - item.startedAt;
        const status =
          (payload.status as ToolCallItem["status"]) ||
          (payload.error ? "error" : "success");
        return {
          ...item,
          status,
          count: payload.count,
          elapsedMs,
          error: payload.error,
          output: payload.output,
        };
      });

      return {
        ...newState,
        activeTurn: {
          ...newState.activeTurn,
          currentToolCallId: null,
        },
      };
    }

    case "skill.activated": {
      if (!turnId) return state;
      const payload = event.payload as {
        skill_id: string;
        skill_name: string;
        trigger_type: "keyword" | "intent" | "manual";
        trigger_keyword?: string;
      };
      const skillItem: SkillActivatedItem = {
        type: "skill.activated",
        id: `skill:${payload.skill_id}:${event.seq}`,
        turnId,
        skillId: payload.skill_id,
        skillName: payload.skill_name,
        triggerType: payload.trigger_type,
        triggerKeyword: payload.trigger_keyword,
        ts: now,
      };
      return insertItem(state, skillItem);
    }

    case "intent.extracted": {
      if (!turnId) return state;
      const stateWithoutWaiting = removeWaitingItem(state, turnId);
      const payload = event.payload as {
        keywords: string[];
        original_query: string;
      };
      const item: IntentExtractedItem = {
        type: "intent.extracted",
        id: `intent:${event.seq}`,
        turnId,
        keywords: payload.keywords || [],
        originalQuery: payload.original_query || "",
        ts: now,
      };
      return insertItem(stateWithoutWaiting, item);
    }

    case "search.results.found": {
      if (!turnId) return state;
      const payload = event.payload as {
        count: number;
        skills: Array<{
          id: string;
          name: string;
          description?: string;
          category?: string;
        }>;
      };
      const item: SearchResultsItem = {
        type: "search.results",
        id: `search:${event.seq}`,
        turnId,
        count: payload.count || 0,
        skills: payload.skills || [],
        ts: now,
      };
      return insertItem(state, item);
    }

    case "tools.registered": {
      if (!turnId) return state;
      const payload = event.payload as {
        base_tools: string[];
        skill_tools: Array<{
          skill_id: string;
          skill_name: string;
          tool_name: string;
          description?: string;
        }>;
        total_count: number;
      };
      const item: ToolsRegisteredItem = {
        type: "tools.registered",
        id: `tools:${event.seq}`,
        turnId,
        baseTools: payload.base_tools || [],
        skillTools: payload.skill_tools || [],
        totalCount: payload.total_count || 0,
        ts: now,
      };
      return insertItem(state, item);
    }

    case "phase.changed": {
      if (!turnId) return state;
      const payload = event.payload as {
        from_phase: string;
        to_phase: string;
        keywords?: string[];
        skill_count?: number;
        skill_ids?: string[];
      };
      const item: PhaseChangedItem = {
        type: "phase.changed",
        id: `phase:${event.seq}`,
        turnId,
        fromPhase: payload.from_phase || "",
        toPhase: payload.to_phase || "",
        keywords: payload.keywords,
        skillCount: payload.skill_count,
        skillIds: payload.skill_ids,
        ts: now,
      };
      return insertItem(state, item);
    }

    default:
      return state;
  }
}
