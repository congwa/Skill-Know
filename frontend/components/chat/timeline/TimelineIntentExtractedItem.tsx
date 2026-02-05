"use client";

import { Search } from "lucide-react";
import type { IntentExtractedItem } from "@/lib/sdk-extensions";

interface Props {
  item: IntentExtractedItem;
}

export function TimelineIntentExtractedItem({ item }: Props) {
  return (
    <div className="flex items-start gap-2 py-2 px-3 text-sm text-muted-foreground">
      <Search className="h-4 w-4 mt-0.5 text-blue-500" />
      <div className="flex-1">
        <span className="text-foreground/80">正在分析意图...</span>
        {item.keywords.length > 0 && (
          <div className="flex flex-wrap gap-1.5 mt-1.5">
            {item.keywords.map((kw, i) => (
              <span
                key={i}
                className="inline-flex items-center px-2 py-0.5 rounded-full text-xs bg-blue-500/10 text-blue-600 dark:text-blue-400"
              >
                {kw}
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
