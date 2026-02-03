/**
 * 聊天 API
 */

import { apiPost, getApiBaseUrl } from "@/lib/api/client";

export interface ChatRequest {
  message: string;
  conversation_id?: string | null;
}

export interface ChatResponse {
  conversation_id: string;
  message_id: string;
  content: string;
  tool_calls?: unknown[] | null;
  latency_ms?: number | null;
}

export interface StreamEvent {
  seq: number;
  type: string;
  conversation_id: string;
  message_id: string;
  payload: Record<string, unknown>;
}

export function chat(data: ChatRequest): Promise<ChatResponse> {
  return apiPost<ChatResponse>("/chat", data);
}

export async function* chatStream(data: ChatRequest): AsyncGenerator<StreamEvent> {
  const response = await fetch(`${getApiBaseUrl()}/chat/stream`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(data),
  });

  if (!response.ok) {
    throw new Error("聊天请求失败");
  }

  const reader = response.body?.getReader();
  if (!reader) {
    throw new Error("无法读取响应流");
  }

  const decoder = new TextDecoder();
  let buffer = "";

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() || "";

      for (const line of lines) {
        if (line.startsWith("data: ")) {
          const data = line.slice(6);
          if (data.trim()) {
            try {
              const event: StreamEvent = JSON.parse(data);
              yield event;
            } catch {
              console.error("解析事件失败:", data);
            }
          }
        }
      }
    }
  } finally {
    reader.releaseLock();
  }
}
