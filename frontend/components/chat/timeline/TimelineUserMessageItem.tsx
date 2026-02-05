"use client";

import { User } from "lucide-react";
import type { UserMessageItem } from "@embedease/chat-sdk";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

interface TimelineUserMessageItemProps {
  item: UserMessageItem;
}

export function TimelineUserMessageItem({ item }: TimelineUserMessageItemProps) {
  return (
    <div className="flex gap-3 justify-end w-full">
      <div className="bg-primary text-primary-foreground rounded-lg p-3 max-w-[80%]">
        <div className="prose prose-sm prose-invert max-w-none">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>
            {item.content}
          </ReactMarkdown>
        </div>
      </div>
      <div className="h-8 w-8 rounded-full bg-primary flex items-center justify-center shrink-0">
        <User className="h-4 w-4 text-primary-foreground" />
      </div>
    </div>
  );
}
