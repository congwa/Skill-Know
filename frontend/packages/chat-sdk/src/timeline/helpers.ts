/**
 * Timeline 内部辅助函数
 */

import type {
  TimelineState,
  TimelineItem,
  TimelineItemBase,
  LLMCallSubItem,
  ToolCallSubItem,
  LLMCallClusterItem,
} from "./types";

let toolLabelMap: Record<string, string> = {};

export function registerToolLabels(labels: Record<string, string>): void {
  toolLabelMap = { ...toolLabelMap, ...labels };
}

export function getToolLabel(name: string): string {
  return toolLabelMap[name] || name;
}

export function createInitialState(): TimelineState {
  return {
    timeline: [],
    indexById: {},
    activeTurn: {
      turnId: null,
      currentLlmCallId: null,
      currentToolCallId: null,
      isStreaming: false,
    },
  };
}

export function insertItem<T extends TimelineItemBase = TimelineItem>(
  state: TimelineState<T>,
  item: T
): TimelineState<T> {
  const timeline = [...state.timeline, item];
  const indexById = { ...state.indexById, [item.id]: timeline.length - 1 };
  return { ...state, timeline, indexById };
}

export function updateItemById<T extends TimelineItemBase = TimelineItem>(
  state: TimelineState<T>,
  id: string,
  updater: (item: T) => T
): TimelineState<T> {
  const index = state.indexById[id];
  if (index === undefined) return state;

  const timeline = [...state.timeline];
  timeline[index] = updater(timeline[index]);
  return { ...state, timeline };
}

export function getCurrentLlmCluster(
  state: TimelineState
): LLMCallClusterItem | undefined {
  const llmCallId = state.activeTurn.currentLlmCallId;
  if (!llmCallId) return undefined;
  const index = state.indexById[llmCallId];
  if (index === undefined) return undefined;
  const item = state.timeline[index];
  if (item.type === "llm.call.cluster") return item;
  return undefined;
}

export function appendSubItemToCurrentCluster(
  state: TimelineState,
  subItem: LLMCallSubItem
): TimelineState {
  const llmCallId = state.activeTurn.currentLlmCallId;
  if (!llmCallId) return state;

  return updateItemById(state, llmCallId, (item) => {
    if (item.type !== "llm.call.cluster") return item;
    const children = [...item.children, subItem];
    const childIndexById = {
      ...item.childIndexById,
      [subItem.id]: children.length - 1,
    };
    return { ...item, children, childIndexById };
  });
}

export function updateSubItemInCurrentCluster(
  state: TimelineState,
  subItemId: string,
  updater: (subItem: LLMCallSubItem) => LLMCallSubItem
): TimelineState {
  const llmCallId = state.activeTurn.currentLlmCallId;
  if (!llmCallId) return state;

  return updateItemById(state, llmCallId, (item) => {
    if (item.type !== "llm.call.cluster") return item;
    const subIndex = item.childIndexById[subItemId];
    if (subIndex === undefined) return item;
    const children = [...item.children];
    children[subIndex] = updater(children[subIndex]);
    return { ...item, children };
  });
}

export function appendSubItemToCurrentToolCall(
  state: TimelineState,
  subItem: ToolCallSubItem
): TimelineState {
  const toolCallId = state.activeTurn.currentToolCallId;
  if (!toolCallId) return state;

  return updateItemById(state, toolCallId, (item) => {
    if (item.type !== "tool.call") return item;
    const children = [...item.children, subItem];
    const childIndexById = {
      ...item.childIndexById,
      [subItem.id]: children.length - 1,
    };
    return { ...item, children, childIndexById };
  });
}

export function getLastSubItemOfType<T extends LLMCallSubItem>(
  cluster: LLMCallClusterItem,
  type: T["type"]
): T | undefined {
  for (let i = cluster.children.length - 1; i >= 0; i--) {
    const child = cluster.children[i];
    if (child.type === type) return child as T;
  }
  return undefined;
}

export function removeWaitingItem<T extends TimelineItemBase = TimelineItem>(
  state: TimelineState<T>,
  turnId: string
): TimelineState<T> {
  const waitingId = `waiting-${turnId}`;
  const index = state.indexById[waitingId];
  if (index === undefined) return state;

  const timeline = state.timeline.filter((_, i) => i !== index);
  const indexById: Record<string, number> = {};
  timeline.forEach((item, i) => {
    indexById[item.id] = i;
  });
  return { ...state, timeline, indexById };
}
