"use client";

import { Wrench, Sparkles } from "lucide-react";
import type { ToolsRegisteredItem } from "@/lib/timeline";

interface Props {
  item: ToolsRegisteredItem;
}

export function TimelineToolsRegisteredItem({ item }: Props) {
  return (
    <div className="flex items-start gap-2 py-2 px-3 text-sm text-muted-foreground">
      <Wrench className="h-4 w-4 mt-0.5 text-violet-500" />
      <div className="flex-1">
        <span className="text-foreground/80">
          已加载 <span className="font-medium text-violet-600">{item.totalCount}</span> 个工具
        </span>
        {item.skillTools.length > 0 && (
          <div className="flex flex-wrap gap-1.5 mt-1.5">
            {item.skillTools.map((tool) => (
              <span
                key={tool.skill_id}
                className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs bg-violet-500/10 text-violet-600 dark:text-violet-400"
              >
                <Sparkles className="h-3 w-3" />
                {tool.skill_name}
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
