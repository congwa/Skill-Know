/**
 * SDK 业务扩展层统一导出
 *
 * 提供 Skill-Know 特有的类型和 reducer 扩展
 */

// 业务类型
export * from "./types";

// 业务 Reducer
export { businessReducer, timelineReducer } from "./reducer";

// 重新导出 SDK 常用功能
export {
  createInitialState,
  addUserMessage,
  startAssistantTurn,
  endTurn,
  clearTurn,
  historyToTimeline,
  ChatClient,
  insertItem,
  updateItemById,
  removeWaitingItem,
} from "@embedease/chat-sdk";
