"use client";

import { Database, Sparkles } from "lucide-react";
import type { SearchResultsItem } from "@/lib/sdk-extensions";

interface Props {
  item: SearchResultsItem;
}

export function TimelineSearchResultsItem({ item }: Props) {
  return (
    <div className="flex items-start gap-2 py-2 px-3 text-sm text-muted-foreground">
      <Database className="h-4 w-4 mt-0.5 text-emerald-500" />
      <div className="flex-1">
        <span className="text-foreground/80">
          检索到 <span className="font-medium text-emerald-600">{item.count}</span> 个相关知识
        </span>
        {item.skills.length > 0 && (
          <div className="flex flex-wrap gap-1.5 mt-1.5">
            {item.skills.map((skill) => (
              <span
                key={skill.id}
                className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs bg-emerald-500/10 text-emerald-600 dark:text-emerald-400"
              >
                <Sparkles className="h-3 w-3" />
                {skill.name}
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
