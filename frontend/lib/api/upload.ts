/**
 * 批量上传 API
 */

import { getApiBaseUrl } from "@/lib/api/client";

export type UploadStep =
  | "queued"
  | "uploading"
  | "parsing"
  | "analyzing"
  | "generating"
  | "saving"
  | "completed"
  | "failed";

export type StepStatus = "pending" | "running" | "completed" | "failed";

export interface FileProgress {
  file_id: string;
  filename: string;
  step: UploadStep;
  status: StepStatus;
  progress: number;
  message: string;
  error?: string;
  result?: {
    document_id: string;
    skill_id: string;
    skill_name: string;
  };
}

export interface TaskState {
  task_id: string;
  status: string;
  total: number;
  completed: number;
  failed: number;
  files: FileProgress[];
}

export interface BatchUploadResponse {
  task_id: string;
  file_count: number;
  stream_url: string;
}

export interface ProgressEvent {
  task_id: string;
  file_id: string;
  filename: string;
  step: UploadStep;
  status: StepStatus;
  progress: number;
  message: string;
  error?: string;
  result?: {
    document_id: string;
    skill_id: string;
    skill_name: string;
  };
}

export interface TaskCompletedEvent {
  task_id: string;
  total: number;
  completed: number;
  failed: number;
  status: string;
}

/**
 * 批量上传文件
 */
export async function batchUpload(
  files: File[],
  options?: { folder_id?: string; use_llm?: boolean }
): Promise<BatchUploadResponse> {
  const formData = new FormData();
  files.forEach((file) => formData.append("files", file));
  if (options?.folder_id) formData.append("folder_id", options.folder_id);
  if (options?.use_llm !== undefined)
    formData.append("use_llm", String(options.use_llm));

  const response = await fetch(`${getApiBaseUrl()}/upload/batch`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "上传失败" }));
    throw new Error(error.detail || "上传失败");
  }

  return response.json();
}

/**
 * 获取任务状态
 */
export async function getTaskStatus(taskId: string): Promise<TaskState> {
  const response = await fetch(`${getApiBaseUrl()}/upload/tasks/${taskId}`);

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "获取任务状态失败" }));
    throw new Error(error.detail || "获取任务状态失败");
  }

  return response.json();
}

/**
 * 订阅任务进度（SSE）
 */
export function subscribeTaskProgress(
  taskId: string,
  callbacks: {
    onProgress?: (event: ProgressEvent) => void;
    onCompleted?: (event: TaskCompletedEvent) => void;
    onError?: (error: Error) => void;
  }
): () => void {
  const eventSource = new EventSource(
    `${getApiBaseUrl()}/upload/tasks/${taskId}/stream`
  );

  eventSource.addEventListener("file.progress", (e) => {
    try {
      const data = JSON.parse(e.data) as ProgressEvent;
      callbacks.onProgress?.(data);
    } catch (err) {
      console.error("解析进度事件失败:", err);
    }
  });

  eventSource.addEventListener("task.completed", (e) => {
    try {
      const data = JSON.parse(e.data) as TaskCompletedEvent;
      callbacks.onCompleted?.(data);
      eventSource.close();
    } catch (err) {
      console.error("解析完成事件失败:", err);
    }
  });

  eventSource.onerror = (e) => {
    callbacks.onError?.(new Error("SSE 连接错误"));
    eventSource.close();
  };

  // 返回取消订阅函数
  return () => {
    eventSource.close();
  };
}

/**
 * 清理任务
 */
export async function cleanupTask(taskId: string): Promise<void> {
  const response = await fetch(`${getApiBaseUrl()}/upload/tasks/${taskId}`, {
    method: "DELETE",
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "清理任务失败" }));
    throw new Error(error.detail || "清理任务失败");
  }
}

/**
 * 步骤显示名称
 */
export const STEP_LABELS: Record<UploadStep, string> = {
  queued: "排队中",
  uploading: "上传中",
  parsing: "解析中",
  analyzing: "分析中",
  generating: "生成Skill",
  saving: "保存中",
  completed: "完成",
  failed: "失败",
};

/**
 * 步骤顺序
 */
export const STEP_ORDER: UploadStep[] = [
  "uploading",
  "parsing",
  "analyzing",
  "generating",
  "saving",
  "completed",
];

/**
 * 计算总进度百分比
 */
export function calculateOverallProgress(files: FileProgress[]): number {
  if (files.length === 0) return 0;

  const stepWeights: Record<UploadStep, number> = {
    queued: 0,
    uploading: 10,
    parsing: 25,
    analyzing: 45,
    generating: 70,
    saving: 90,
    completed: 100,
    failed: 0,
  };

  const totalProgress = files.reduce((sum, file) => {
    if (file.step === "failed") return sum;
    return sum + stepWeights[file.step];
  }, 0);

  return Math.round(totalProgress / files.length);
}
