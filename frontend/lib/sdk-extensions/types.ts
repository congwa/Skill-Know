/**
 * 业务扩展类型定义
 *
 * 扩展 SDK 的 TimelineItem 类型，添加 Skill-Know 特有的事件类型
 */

import type { TimelineItem as SDKTimelineItem, TimelineState } from "@embedease/chat-sdk";

// ==================== 业务特有事件类型 ====================

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

// ==================== 扩展 TimelineItem ====================

/** 业务扩展的 TimelineItem 类型 */
export type BusinessTimelineItem =
  | SDKTimelineItem
  | IntentExtractedItem
  | SearchResultsItem
  | ToolsRegisteredItem
  | PhaseChangedItem;

// ==================== 重新导出 SDK 类型 ====================

export type { TimelineState, ChatEvent, ImageAttachment, HistoryMessage } from "@embedease/chat-sdk";

// 为了类型兼容，也导出 SDK 的原始类型
export type {
  UserMessageItem,
  LLMCallClusterItem,
  ToolCallItem,
  ErrorItem,
  FinalItem,
  WaitingItem,
  SkillActivatedItem,
  ItemStatus,
  LLMCallSubItem,
  ReasoningSubItem,
  ContentSubItem,
} from "@embedease/chat-sdk";
