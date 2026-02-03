/**
 * Timeline 辅助函数
 */

import type {
  TimelineState,
  TimelineItem,
  LLMCallClusterItem,
  LLMCallSubItem,
} from "./types";

/** 工具名称映射 */
const TOOL_LABELS: Record<string, string> = {
  search_skills: "搜索技能",
  search_documents: "搜索文档",
  sql_search: "SQL 查询",
  knowledge_search: "知识检索",
};

export function getToolLabel(name: string): string {
  return TOOL_LABELS[name] || name;
}

/** 创建初始状态 */
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

/** 插入 timeline item */
export function insertItem(
  state: TimelineState,
  item: TimelineItem
): TimelineState {
  const timeline = [...state.timeline, item];
  const indexById = { ...state.indexById, [item.id]: timeline.length - 1 };
  return { ...state, timeline, indexById };
}

/** 根据 ID 更新 item */
export function updateItemById(
  state: TimelineState,
  id: string,
  updater: (item: TimelineItem) => TimelineItem
): TimelineState {
  const index = state.indexById[id];
  if (index === undefined) return state;

  const timeline = [...state.timeline];
  timeline[index] = updater(timeline[index]);
  return { ...state, timeline };
}

/** 获取当前 LLM 调用 cluster */
export function getCurrentLlmCluster(
  state: TimelineState
): LLMCallClusterItem | null {
  const id = state.activeTurn.currentLlmCallId;
  if (!id) return null;
  const index = state.indexById[id];
  if (index === undefined) return null;
  const item = state.timeline[index];
  return item.type === "llm.call.cluster" ? item : null;
}

/** 向当前 LLM cluster 添加子项 */
export function appendSubItemToCurrentCluster(
  state: TimelineState,
  subItem: LLMCallSubItem
): TimelineState {
  const cluster = getCurrentLlmCluster(state);
  if (!cluster) return state;

  const newChildren = [...cluster.children, subItem];
  const newChildIndexById = {
    ...cluster.childIndexById,
    [subItem.id]: newChildren.length - 1,
  };

  return updateItemById(state, cluster.id, (item) => ({
    ...item,
    children: newChildren,
    childIndexById: newChildIndexById,
  }));
}

/** 更新当前 cluster 中的子项 */
export function updateSubItemInCurrentCluster(
  state: TimelineState,
  subItemId: string,
  updater: (subItem: LLMCallSubItem) => LLMCallSubItem
): TimelineState {
  const cluster = getCurrentLlmCluster(state);
  if (!cluster) return state;

  const subIndex = cluster.childIndexById[subItemId];
  if (subIndex === undefined) return state;

  const newChildren = [...cluster.children];
  newChildren[subIndex] = updater(newChildren[subIndex]);

  return updateItemById(state, cluster.id, (item) => ({
    ...item,
    children: newChildren,
  }));
}

/** 获取 cluster 中最后一个指定类型的子项 */
export function getLastSubItemOfType<T extends LLMCallSubItem>(
  cluster: LLMCallClusterItem,
  type: T["type"]
): T | null {
  for (let i = cluster.children.length - 1; i >= 0; i--) {
    if (cluster.children[i].type === type) {
      return cluster.children[i] as T;
    }
  }
  return null;
}

/** 移除 waiting item */
export function removeWaitingItem(
  state: TimelineState,
  turnId: string
): TimelineState {
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
