"use client";

import { useState, useCallback, useRef, useEffect } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { ScrollArea } from "@/components/ui/scroll-area";
import { cn } from "@/lib/utils";
import {
  Upload,
  FileText,
  CheckCircle2,
  XCircle,
  Loader2,
  Plus,
  X,
} from "lucide-react";
import {
  batchUpload,
  subscribeTaskProgress,
  FileProgress,
  ProgressEvent,
  TaskCompletedEvent,
  STEP_LABELS,
  STEP_ORDER,
  calculateOverallProgress,
  UploadStep,
} from "@/lib/api/upload";

interface BatchUploadDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  folderId?: string;
  onComplete?: () => void;
}

type FileState = FileProgress & { file?: File };

export function BatchUploadDialog({
  open,
  onOpenChange,
  folderId,
  onComplete,
}: BatchUploadDialogProps) {
  const [files, setFiles] = useState<File[]>([]);
  const [fileStates, setFileStates] = useState<Map<string, FileState>>(new Map());
  const [isUploading, setIsUploading] = useState(false);
  const [taskId, setTaskId] = useState<string | null>(null);
  const [overallProgress, setOverallProgress] = useState(0);
  const [completed, setCompleted] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const unsubscribeRef = useRef<(() => void) | null>(null);

  // 清理函数
  useEffect(() => {
    return () => {
      if (unsubscribeRef.current) {
        unsubscribeRef.current();
      }
    };
  }, []);

  // 重置状态
  const resetState = useCallback(() => {
    setFiles([]);
    setFileStates(new Map());
    setIsUploading(false);
    setTaskId(null);
    setOverallProgress(0);
    setCompleted(false);
    if (unsubscribeRef.current) {
      unsubscribeRef.current();
      unsubscribeRef.current = null;
    }
  }, []);

  // 关闭对话框
  const handleClose = useCallback(() => {
    if (isUploading && !completed) {
      if (!confirm("上传进行中，确定要关闭吗？")) {
        return;
      }
    }
    resetState();
    onOpenChange(false);
  }, [isUploading, completed, resetState, onOpenChange]);

  // 添加文件
  const handleFilesSelected = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const selectedFiles = Array.from(e.target.files || []);
      setFiles((prev) => [...prev, ...selectedFiles]);
      e.target.value = "";
    },
    []
  );

  // 移除文件
  const handleRemoveFile = useCallback((index: number) => {
    setFiles((prev) => prev.filter((_, i) => i !== index));
  }, []);

  // 开始上传
  const handleStartUpload = useCallback(async () => {
    if (files.length === 0) return;

    setIsUploading(true);

    // 初始化文件状态
    const initialStates = new Map<string, FileState>();
    files.forEach((file, index) => {
      const tempId = `temp-${index}`;
      initialStates.set(tempId, {
        file_id: tempId,
        filename: file.name,
        step: "queued",
        status: "pending",
        progress: 0,
        message: "等待上传...",
        file,
      });
    });
    setFileStates(initialStates);

    try {
      // 调用批量上传 API
      const response = await batchUpload(files, { folder_id: folderId });
      setTaskId(response.task_id);

      // 订阅进度
      unsubscribeRef.current = subscribeTaskProgress(response.task_id, {
        onProgress: (event: ProgressEvent) => {
          setFileStates((prev) => {
            const newStates = new Map(prev);
            
            // 查找匹配的文件（通过文件名）
            let found = false;
            newStates.forEach((state, key) => {
              if (state.filename === event.filename) {
                newStates.set(key, {
                  ...state,
                  file_id: event.file_id,
                  step: event.step,
                  status: event.status,
                  progress: event.progress,
                  message: event.message,
                  error: event.error,
                  result: event.result,
                });
                found = true;
              }
            });

            // 如果没找到，添加新的
            if (!found) {
              newStates.set(event.file_id, {
                file_id: event.file_id,
                filename: event.filename,
                step: event.step,
                status: event.status,
                progress: event.progress,
                message: event.message,
                error: event.error,
                result: event.result,
              });
            }

            return newStates;
          });
        },
        onCompleted: (event: TaskCompletedEvent) => {
          setCompleted(true);
          setOverallProgress(100);
          onComplete?.();
        },
        onError: (error: Error) => {
          console.error("SSE 错误:", error);
        },
      });
    } catch (error) {
      console.error("上传失败:", error);
      setIsUploading(false);
    }
  }, [files, folderId, onComplete]);

  // 计算总进度
  useEffect(() => {
    const states = Array.from(fileStates.values());
    if (states.length > 0) {
      setOverallProgress(calculateOverallProgress(states));
    }
  }, [fileStates]);

  // 渲染步骤指示器
  const renderStepIndicator = (currentStep: UploadStep) => {
    return (
      <div className="flex items-center gap-1 text-xs">
        {STEP_ORDER.slice(0, -1).map((step, index) => {
          const stepIndex = STEP_ORDER.indexOf(step);
          const currentIndex = STEP_ORDER.indexOf(currentStep);
          const isCompleted = currentIndex > stepIndex;
          const isCurrent = step === currentStep;

          return (
            <div key={step} className="flex items-center gap-1">
              <div
                className={cn(
                  "w-2 h-2 rounded-full transition-colors",
                  isCompleted
                    ? "bg-green-500"
                    : isCurrent
                    ? "bg-blue-500 animate-pulse"
                    : "bg-gray-300"
                )}
              />
              {index < STEP_ORDER.length - 2 && (
                <div
                  className={cn(
                    "w-4 h-0.5",
                    isCompleted ? "bg-green-500" : "bg-gray-300"
                  )}
                />
              )}
            </div>
          );
        })}
      </div>
    );
  };

  // 渲染文件项
  const renderFileItem = (state: FileState, index: number) => {
    const isCompleted = state.step === "completed";
    const isFailed = state.step === "failed";
    const isProcessing = !isCompleted && !isFailed && state.status === "running";

    return (
      <div
        key={state.file_id}
        className="p-4 border rounded-lg bg-card space-y-3"
      >
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-2">
            <FileText className="h-5 w-5 text-muted-foreground" />
            <div>
              <p className="font-medium text-sm truncate max-w-[200px]">
                {state.filename}
              </p>
              <p className="text-xs text-muted-foreground">{state.message}</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {isCompleted && <CheckCircle2 className="h-5 w-5 text-green-500" />}
            {isFailed && <XCircle className="h-5 w-5 text-red-500" />}
            {isProcessing && <Loader2 className="h-5 w-5 animate-spin text-blue-500" />}
          </div>
        </div>

        {/* 进度条 */}
        <Progress
          value={isCompleted ? 100 : state.step === "failed" ? 0 : (STEP_ORDER.indexOf(state.step) / (STEP_ORDER.length - 1)) * 100}
          className="h-1.5"
        />

        {/* 步骤指示器 */}
        <div className="flex items-center justify-between">
          {renderStepIndicator(state.step)}
          <span className="text-xs text-muted-foreground">
            {STEP_LABELS[state.step]}
          </span>
        </div>

        {/* 错误信息 */}
        {state.error && (
          <p className="text-xs text-red-500">{state.error}</p>
        )}

        {/* 结果信息 */}
        {state.result && (
          <p className="text-xs text-green-600">
            已生成 Skill: {state.result.skill_name}
          </p>
        )}
      </div>
    );
  };

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-[600px]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Upload className="h-5 w-5" />
            批量上传文档
          </DialogTitle>
          <DialogDescription>
            上传文档并自动转换为 Skill。支持 txt, md, pdf, docx 格式。
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          {/* 文件选择区域 */}
          {!isUploading && (
            <div className="space-y-4">
              <input
                ref={fileInputRef}
                type="file"
                multiple
                accept=".txt,.md,.markdown,.pdf,.docx,.doc"
                onChange={handleFilesSelected}
                className="hidden"
              />

              <div
                onClick={() => fileInputRef.current?.click()}
                className="border-2 border-dashed rounded-lg p-8 text-center cursor-pointer hover:border-primary transition-colors"
              >
                <Plus className="h-8 w-8 mx-auto mb-2 text-muted-foreground" />
                <p className="text-sm text-muted-foreground">
                  点击选择文件或拖放到此处
                </p>
              </div>

              {/* 已选文件列表 */}
              {files.length > 0 && (
                <div className="space-y-2">
                  <p className="text-sm font-medium">已选择 {files.length} 个文件</p>
                  <ScrollArea className="h-[200px]">
                    <div className="space-y-2">
                      {files.map((file, index) => (
                        <div
                          key={index}
                          className="flex items-center justify-between p-2 border rounded"
                        >
                          <div className="flex items-center gap-2">
                            <FileText className="h-4 w-4 text-muted-foreground" />
                            <span className="text-sm truncate max-w-[300px]">
                              {file.name}
                            </span>
                            <span className="text-xs text-muted-foreground">
                              ({(file.size / 1024).toFixed(1)} KB)
                            </span>
                          </div>
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => handleRemoveFile(index)}
                          >
                            <X className="h-4 w-4" />
                          </Button>
                        </div>
                      ))}
                    </div>
                  </ScrollArea>
                </div>
              )}
            </div>
          )}

          {/* 上传进度区域 */}
          {isUploading && (
            <div className="space-y-4">
              {/* 总进度 */}
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium">总进度</span>
                  <span className="text-sm text-muted-foreground">
                    {overallProgress}%
                  </span>
                </div>
                <Progress value={overallProgress} className="h-2" />
              </div>

              {/* 文件列表 */}
              <ScrollArea className="h-[300px]">
                <div className="space-y-3 pr-4">
                  {Array.from(fileStates.values()).map((state, index) =>
                    renderFileItem(state, index)
                  )}
                </div>
              </ScrollArea>
            </div>
          )}

          {/* 操作按钮 */}
          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={handleClose}>
              {completed ? "关闭" : "取消"}
            </Button>
            {!isUploading && (
              <Button
                onClick={handleStartUpload}
                disabled={files.length === 0}
              >
                开始上传 ({files.length})
              </Button>
            )}
            {completed && (
              <Button onClick={resetState}>继续上传</Button>
            )}
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
