"use client";

import { Bot, ChevronDown, ChevronRight, Loader2 } from "lucide-react";
import { useState } from "react";
import { cn } from "@/lib/utils";
import type { LLMCallClusterItem } from "@/lib/timeline";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

interface LLMCallClusterProps {
  item: LLMCallClusterItem;
  isStreaming?: boolean;
}

export function LLMCallCluster({ item, isStreaming }: LLMCallClusterProps) {
  const [expandedReasoning, setExpandedReasoning] = useState<Set<string>>(
    new Set()
  );

  const toggleReasoning = (id: string) => {
    setExpandedReasoning((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

  const isRunning = item.status === "running";

  return (
    <div className="flex gap-3 w-full">
      <div className="h-8 w-8 rounded-full bg-primary/10 flex items-center justify-center shrink-0">
        {isRunning && isStreaming ? (
          <Loader2 className="h-4 w-4 text-primary animate-spin" />
        ) : (
          <Bot className="h-4 w-4 text-primary" />
        )}
      </div>
      <div className="flex-1 min-w-0 space-y-2">
        {item.children.map((child) => {
          if (child.type === "reasoning") {
            const isExpanded = expandedReasoning.has(child.id) || child.isOpen;
            return (
              <div
                key={child.id}
                className="bg-amber-50 dark:bg-amber-900/20 rounded-lg overflow-hidden"
              >
                <button
                  onClick={() => toggleReasoning(child.id)}
                  className="w-full px-3 py-2 flex items-center gap-2 text-sm text-amber-700 dark:text-amber-300 hover:bg-amber-100/50 dark:hover:bg-amber-900/30 transition-colors"
                >
                  {isExpanded ? (
                    <ChevronDown className="h-4 w-4" />
                  ) : (
                    <ChevronRight className="h-4 w-4" />
                  )}
                  <span className="font-medium">思考过程</span>
                  {child.isOpen && (
                    <Loader2 className="h-3 w-3 animate-spin ml-auto" />
                  )}
                </button>
                {isExpanded && (
                  <div className="px-3 pb-3 text-sm text-amber-800 dark:text-amber-200 whitespace-pre-wrap">
                    {child.text}
                  </div>
                )}
              </div>
            );
          }

          if (child.type === "content") {
            return (
              <div
                key={child.id}
                className="prose prose-sm dark:prose-invert max-w-none"
              >
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                  {child.text || (isRunning ? "思考中..." : "")}
                </ReactMarkdown>
              </div>
            );
          }

          return null;
        })}

        {item.children.length === 0 && isRunning && (
          <div className="text-sm text-muted-foreground">思考中...</div>
        )}

        {item.error && (
          <div className="text-sm text-red-500 mt-2">错误: {item.error}</div>
        )}
      </div>
    </div>
  );
}
