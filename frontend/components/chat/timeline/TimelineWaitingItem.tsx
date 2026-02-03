"use client";

import { Bot, Loader2 } from "lucide-react";

export function TimelineWaitingItem() {
  return (
    <div className="flex gap-3 w-full">
      <div className="h-8 w-8 rounded-full bg-primary/10 flex items-center justify-center shrink-0">
        <Bot className="h-4 w-4 text-primary" />
      </div>
      <div className="flex items-center gap-2 text-sm text-muted-foreground">
        <Loader2 className="h-4 w-4 animate-spin" />
        <span>正在思考...</span>
      </div>
    </div>
  );
}
