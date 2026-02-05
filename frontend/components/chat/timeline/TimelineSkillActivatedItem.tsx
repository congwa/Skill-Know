"use client";

import { Sparkles } from "lucide-react";
import type { SkillActivatedItem } from "@embedease/chat-sdk";

interface TimelineSkillActivatedItemProps {
  item: SkillActivatedItem;
}

export function TimelineSkillActivatedItem({
  item,
}: TimelineSkillActivatedItemProps) {
  return (
    <div className="mx-auto max-w-3xl px-6">
      <div className="flex items-center justify-center gap-2 text-xs text-muted-foreground">
        <div className="h-px flex-1 bg-border" />
        <div className="flex items-center gap-1.5 px-2 py-1 rounded-full bg-violet-50 dark:bg-violet-900/20 text-violet-600 dark:text-violet-400">
          <Sparkles className="h-3 w-3" />
          <span>技能激活: {item.skillName}</span>
          {item.triggerKeyword && (
            <span className="text-violet-400 dark:text-violet-500">
              ({item.triggerKeyword})
            </span>
          )}
        </div>
        <div className="h-px flex-1 bg-border" />
      </div>
    </div>
  );
}
