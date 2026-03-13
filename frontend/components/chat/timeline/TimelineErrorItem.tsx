"use client";

import { AlertCircle } from "lucide-react";
import type { ErrorItem } from "@embedease/chat-sdk";

interface TimelineErrorItemProps {
  item: ErrorItem;
}

export function TimelineErrorItem({ item }: TimelineErrorItemProps) {
  return (
    <div className="flex items-center gap-2 rounded-lg bg-destructive/10 p-3 text-sm text-destructive">
      <AlertCircle className="h-4 w-4 shrink-0" />
      <span>{item.message}</span>
    </div>
  );
}
