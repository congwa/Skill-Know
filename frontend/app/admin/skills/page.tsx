"use client";

import { useEffect, useState, useMemo } from "react";
import { Plus, Search, Sparkles, FileText, Settings2, Pencil, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { type SkillType } from "@/lib/api/skills";
import { useSkillStore } from "@/lib/stores";
import { cn } from "@/lib/utils";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

const TYPE_LABELS: Record<SkillType, { label: string; icon: typeof Sparkles }> = {
  system: { label: "系统", icon: Settings2 },
  document: { label: "文档", icon: FileText },
  user: { label: "用户", icon: Sparkles },
};

const FILTER_TABS = [
  { value: "all", label: "全部" },
  { value: "system", label: "系统" },
  { value: "document", label: "文档" },
  { value: "user", label: "用户" },
] as const;

export default function SkillsPage() {
  const {
    skills,
    selectedSkill,
    filterType,
    isLoading,
    loadSkills,
    selectSkill,
    setFilterType,
  } = useSkillStore();

  const [searchQuery, setSearchQuery] = useState("");

  useEffect(() => {
    loadSkills();
  }, [loadSkills]);

  const filteredSkills = useMemo(
    () =>
      skills.filter(
        (skill) =>
          skill.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
          skill.description.toLowerCase().includes(searchQuery.toLowerCase())
      ),
    [skills, searchQuery]
  );

  return (
    <div className="h-full flex bg-background">
      {/* 左侧列表 */}
      <div className="w-72 border-r border-border flex flex-col bg-card">
        {/* 头部 */}
        <div className="h-14 px-4 flex items-center justify-between border-b border-border">
          <h1 className="font-semibold text-foreground">技能管理</h1>
          <Button size="sm" variant="default" className="h-7 text-xs">
            <Plus className="h-3.5 w-3.5 mr-1" />
            新建
          </Button>
        </div>

        {/* 搜索 */}
        <div className="p-3 border-b border-border">
          <div className="relative">
            <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
            <Input
              placeholder="搜索技能..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="h-8 pl-8 text-sm bg-muted/50 border-0"
            />
          </div>
        </div>

        {/* 过滤标签 */}
        <div className="px-3 py-2 flex gap-1 border-b border-border">
          {FILTER_TABS.map((tab) => (
            <button
              key={tab.value}
              onClick={() => setFilterType(tab.value as typeof filterType)}
              className={cn(
                "px-2.5 py-1 text-xs rounded-md transition-colors",
                filterType === tab.value
                  ? "bg-foreground text-background font-medium"
                  : "text-muted-foreground hover:text-foreground hover:bg-muted"
              )}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* 列表 */}
        <div className="flex-1 overflow-y-auto">
          {isLoading ? (
            <div className="flex items-center justify-center py-12 text-muted-foreground text-sm">
              加载中...
            </div>
          ) : filteredSkills.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
              <Sparkles className="h-6 w-6 mb-2 opacity-40" />
              <span className="text-sm">暂无技能</span>
            </div>
          ) : (
            <div className="p-2 space-y-0.5">
              {filteredSkills.map((skill) => {
                const typeConfig = TYPE_LABELS[skill.type];
                const TypeIcon = typeConfig?.icon || Sparkles;
                const isSelected = selectedSkill?.id === skill.id;

                return (
                  <div
                    key={skill.id}
                    onClick={() => selectSkill(skill)}
                    className={cn(
                      "p-2.5 rounded-md cursor-pointer transition-colors",
                      isSelected 
                        ? "list-item-selected" 
                        : "list-item-hover"
                    )}
                  >
                    <div className="flex items-start gap-2.5">
                      <div className="h-7 w-7 rounded-md bg-muted flex items-center justify-center shrink-0">
                        <TypeIcon className="h-3.5 w-3.5 text-muted-foreground" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-foreground truncate">
                          {skill.name}
                        </p>
                        <p className="text-xs text-muted-foreground truncate mt-0.5">
                          {skill.description}
                        </p>
                        <div className="flex items-center gap-1.5 mt-1.5">
                          <span className="text-[10px] px-1.5 py-0.5 rounded bg-muted text-muted-foreground">
                            {typeConfig?.label}
                          </span>
                          {skill.always_apply && (
                            <span className="text-[10px] px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-600">
                              始终应用
                            </span>
                          )}
                        </div>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>

      {/* 右侧详情 */}
      <div className="flex-1 min-w-0 overflow-auto bg-background">
        {selectedSkill ? (
          <div className="max-w-3xl mx-auto p-6 space-y-6">
            {/* 头部 */}
            <div className="flex items-start justify-between">
              <div>
                <h2 className="text-xl font-semibold text-foreground">{selectedSkill.name}</h2>
                <p className="text-sm text-muted-foreground mt-1">{selectedSkill.description}</p>
              </div>
              {selectedSkill.is_editable && (
                <div className="flex gap-2">
                  <Button variant="outline" size="sm" className="h-8 text-xs">
                    <Pencil className="h-3.5 w-3.5 mr-1" />
                    编辑
                  </Button>
                  {selectedSkill.is_deletable && (
                    <Button variant="outline" size="sm" className="h-8 text-xs text-destructive hover:text-destructive">
                      <Trash2 className="h-3.5 w-3.5 mr-1" />
                      删除
                    </Button>
                  )}
                </div>
              )}
            </div>

            {/* 属性网格 */}
            <div className="grid grid-cols-4 gap-3">
              <div className="p-3 rounded-lg border border-border bg-card">
                <p className="text-xs text-muted-foreground mb-1">类型</p>
                <p className="text-sm font-medium text-foreground">{TYPE_LABELS[selectedSkill.type]?.label}</p>
              </div>
              <div className="p-3 rounded-lg border border-border bg-card">
                <p className="text-xs text-muted-foreground mb-1">分类</p>
                <p className="text-sm font-medium text-foreground">{selectedSkill.category}</p>
              </div>
              <div className="p-3 rounded-lg border border-border bg-card">
                <p className="text-xs text-muted-foreground mb-1">优先级</p>
                <p className="text-sm font-medium text-foreground">{selectedSkill.priority}</p>
              </div>
              <div className="p-3 rounded-lg border border-border bg-card">
                <p className="text-xs text-muted-foreground mb-1">状态</p>
                <p className="text-sm font-medium text-foreground flex items-center gap-1.5">
                  <span className={cn(
                    "h-1.5 w-1.5 rounded-full",
                    selectedSkill.is_active ? "bg-emerald-500" : "bg-muted-foreground"
                  )} />
                  {selectedSkill.is_active ? "已启用" : "已禁用"}
                </p>
              </div>
            </div>

            {/* 关键词 */}
            {selectedSkill.trigger_keywords.length > 0 && (
              <div className="p-4 rounded-lg border border-border bg-card">
                <p className="text-xs text-muted-foreground mb-2">触发关键词</p>
                <div className="flex flex-wrap gap-1.5">
                  {selectedSkill.trigger_keywords.map((keyword, i) => (
                    <span key={i} className="px-2 py-0.5 text-xs rounded-md bg-muted text-foreground">
                      {keyword}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* 内容 */}
            <div className="p-4 rounded-lg border border-border bg-card">
              <p className="text-xs text-muted-foreground mb-3">技能内容</p>
              <div className="prose prose-sm dark:prose-invert max-w-none text-sm">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                  {selectedSkill.content}
                </ReactMarkdown>
              </div>
            </div>
          </div>
        ) : (
          <div className="h-full flex flex-col items-center justify-center text-muted-foreground">
            <Sparkles className="h-8 w-8 mb-3 opacity-30" />
            <p className="text-sm">选择一个技能查看详情</p>
          </div>
        )}
      </div>
    </div>
  );
}
