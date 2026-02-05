"use client";

import { ArrowRight, Brain, Database, Wrench, MessageSquare } from "lucide-react";
import type { PhaseChangedItem } from "@/lib/sdk-extensions";

interface Props {
  item: PhaseChangedItem;
}

const PHASE_LABELS: Record<string, { label: string; icon: typeof Brain; color: string }> = {
  init: { label: "初始化", icon: Brain, color: "text-gray-500" },
  intent_analysis: { label: "意图分析", icon: Brain, color: "text-blue-500" },
  skill_retrieval: { label: "知识检索", icon: Database, color: "text-emerald-500" },
  tool_preparation: { label: "工具准备", icon: Wrench, color: "text-violet-500" },
  execution: { label: "生成回答", icon: MessageSquare, color: "text-orange-500" },
  completed: { label: "完成", icon: MessageSquare, color: "text-green-500" },
};

export function TimelinePhaseChangedItem({ item }: Props) {
  const fromPhase = PHASE_LABELS[item.fromPhase] || { label: item.fromPhase, icon: Brain, color: "text-gray-500" };
  const toPhase = PHASE_LABELS[item.toPhase] || { label: item.toPhase, icon: Brain, color: "text-gray-500" };
  const ToIcon = toPhase.icon;

  return (
    <div className="flex items-center gap-2 py-1.5 px-3 text-xs text-muted-foreground">
      <ToIcon className={`h-3.5 w-3.5 ${toPhase.color}`} />
      <span className="text-muted-foreground/70">{fromPhase.label}</span>
      <ArrowRight className="h-3 w-3 text-muted-foreground/50" />
      <span className={`font-medium ${toPhase.color}`}>{toPhase.label}</span>
      {item.keywords && item.keywords.length > 0 && (
        <span className="text-muted-foreground/60">
          · 关键词: {item.keywords.slice(0, 3).join(", ")}
        </span>
      )}
      {item.skillCount !== undefined && item.skillCount > 0 && (
        <span className="text-muted-foreground/60">
          · 找到 {item.skillCount} 个技能
        </span>
      )}
    </div>
  );
}
