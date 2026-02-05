"use client";

import { Wrench, CheckCircle2, XCircle, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";
import type { ToolCallItem } from "@embedease/chat-sdk";

interface TimelineToolCallItemProps {
  item: ToolCallItem;
}

export function TimelineToolCallItem({ item }: TimelineToolCallItemProps) {
  const statusIcon = {
    running: <Loader2 className="h-4 w-4 animate-spin text-blue-500" />,
    success: <CheckCircle2 className="h-4 w-4 text-emerald-500" />,
    error: <XCircle className="h-4 w-4 text-red-500" />,
    empty: <CheckCircle2 className="h-4 w-4 text-zinc-400" />,
  };

  return (
    <div className="flex gap-3 w-full">
      <div className="h-8 w-8 rounded-full bg-blue-100 dark:bg-blue-900/30 flex items-center justify-center shrink-0">
        <Wrench className="h-4 w-4 text-blue-600 dark:text-blue-400" />
      </div>
      <div className="flex-1 min-w-0">
        <div
          className={cn(
            "inline-flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm",
            "bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300"
          )}
        >
          {statusIcon[item.status]}
          <span className="font-medium">{item.label}</span>
          {item.elapsedMs !== undefined && item.status !== "running" && (
            <span className="text-xs text-blue-500/70">
              {item.elapsedMs}ms
            </span>
          )}
        </div>
        {item.error && (
          <div className="mt-1 text-sm text-red-500">{item.error}</div>
        )}
      </div>
    </div>
  );
}
