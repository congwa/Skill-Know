/**
 * Timeline 类型定义
 */

/** 状态类型 */
export type ItemStatus = "running" | "success" | "error" | "empty";

// ==================== LLM 调用内部子事件类型 ====================

export interface ReasoningSubItem {
  type: "reasoning";
  id: string;
  text: string;
  isOpen: boolean;
  ts: number;
}

export interface ContentSubItem {
  type: "content";
  id: string;
  text: string;
  ts: number;
}

export interface SearchResultSubItem {
  type: "search_result";
  id: string;
  results: Array<{
    type: "skill" | "document";
    id: string;
    title: string;
    preview: string;
  }>;
  ts: number;
}

export type LLMCallSubItem = ReasoningSubItem | ContentSubItem | SearchResultSubItem;

// ==================== 时间线顶层 Item 类型 ====================

export interface UserMessageItem {
  type: "user.message";
  id: string;
  turnId: string;
  content: string;
  ts: number;
}

export interface LLMCallClusterItem {
  type: "llm.call.cluster";
  id: string;
  turnId: string;
  status: ItemStatus;
  messageCount?: number;
  elapsedMs?: number;
  error?: string;
  children: LLMCallSubItem[];
  childIndexById: Record<string, number>;
  ts: number;
}

export interface ToolCallItem {
  type: "tool.call";
  id: string;
  turnId: string;
  name: string;
  label: string;
  status: ItemStatus;
  count?: number;
  elapsedMs?: number;
  error?: string;
  input?: unknown;
  output?: unknown;
  startedAt: number;
  ts: number;
}

export interface ErrorItem {
  type: "error";
  id: string;
  turnId: string;
  message: string;
  ts: number;
}

export interface FinalItem {
  type: "final";
  id: string;
  turnId: string;
  content?: string;
  ts: number;
}

export interface SkillActivatedItem {
  type: "skill.activated";
  id: string;
  turnId: string;
  skillId: string;
  skillName: string;
  triggerType: "keyword" | "intent" | "manual";
  triggerKeyword?: string;
  ts: number;
}

/** 关键词提取事件 */
export interface IntentExtractedItem {
  type: "intent.extracted";
  id: string;
  turnId: string;
  keywords: string[];
  originalQuery: string;
  ts: number;
}

/** 检索结果事件 */
export interface SearchResultsItem {
  type: "search.results";
  id: string;
  turnId: string;
  count: number;
  skills: Array<{
    id: string;
    name: string;
    description?: string;
    category?: string;
  }>;
  ts: number;
}

/** 工具注册事件 */
export interface ToolsRegisteredItem {
  type: "tools.registered";
  id: string;
  turnId: string;
  baseTools: string[];
  skillTools: Array<{
    skill_id: string;
    skill_name: string;
    tool_name: string;
    description?: string;
  }>;
  totalCount: number;
  ts: number;
}

/** 阶段变化事件 */
export interface PhaseChangedItem {
  type: "phase.changed";
  id: string;
  turnId: string;
  fromPhase: string;
  toPhase: string;
  keywords?: string[];
  skillCount?: number;
  skillIds?: string[];
  ts: number;
}

export interface WaitingItem {
  type: "waiting";
  id: string;
  turnId: string;
  ts: number;
}

export type TimelineItem =
  | UserMessageItem
  | LLMCallClusterItem
  | ToolCallItem
  | ErrorItem
  | FinalItem
  | SkillActivatedItem
  | IntentExtractedItem
  | SearchResultsItem
  | ToolsRegisteredItem
  | PhaseChangedItem
  | WaitingItem;

export interface TimelineState {
  timeline: TimelineItem[];
  indexById: Record<string, number>;
  activeTurn: {
    turnId: string | null;
    currentLlmCallId: string | null;
    currentToolCallId: string | null;
    isStreaming: boolean;
  };
}

// ==================== Chat Event 类型 ====================

export interface ChatEvent {
  seq: number;
  type: string;
  conversation_id: string;
  message_id: string;
  payload: Record<string, unknown>;
}
