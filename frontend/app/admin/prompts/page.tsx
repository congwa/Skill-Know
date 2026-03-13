"use client";

import { useEffect, useState, useRef, useCallback } from "react";
import { Search, BookOpen, RotateCcw, Save, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { listPrompts, updatePrompt, resetPrompt, type Prompt } from "@/lib/api/prompts";
import { cn } from "@/lib/utils";
import { RichEditor, type RichEditorRef } from "@/components/rich-editor";
import { PageHeader } from "@/components/admin/page-header";
import { EmptyState } from "@/components/admin/empty-state";

export default function PromptsPage() {
  const [prompts, setPrompts] = useState<Prompt[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedPrompt, setSelectedPrompt] = useState<Prompt | null>(null);
  const [editedContent, setEditedContent] = useState("");
  const editorRef = useRef<RichEditorRef>(null);

  useEffect(() => {
    loadPrompts();
  }, []);

  const handleMarkdownChange = useCallback((content: string) => {
    setEditedContent(content);
  }, []);

  async function loadPrompts() {
    setLoading(true);
    try {
      const res = await listPrompts();
      setPrompts(res.items);
    } catch (error) {
      console.error("加载提示词失败:", error);
    } finally {
      setLoading(false);
    }
  }

  const handleSelect = (prompt: Prompt) => {
    setSelectedPrompt(prompt);
    setEditedContent(prompt.content);
    // 延迟设置编辑器内容，确保组件已渲染
    setTimeout(() => {
      editorRef.current?.setMarkdown(prompt.content);
    }, 100);
  };

  const handleSave = async () => {
    if (!selectedPrompt) return;
    setSaving(true);
    try {
      const updated = await updatePrompt(selectedPrompt.key, {
        content: editedContent,
      });
      setPrompts((prev) =>
        prev.map((p) => (p.key === updated.key ? updated : p))
      );
      setSelectedPrompt(updated);
    } catch (error) {
      console.error("保存失败:", error);
    } finally {
      setSaving(false);
    }
  };

  const handleReset = async () => {
    if (!selectedPrompt) return;
    setSaving(true);
    try {
      const reset = await resetPrompt(selectedPrompt.key);
      setPrompts((prev) =>
        prev.map((p) => (p.key === reset.key ? reset : p))
      );
      setSelectedPrompt(reset);
      setEditedContent(reset.content);
    } catch (error) {
      console.error("重置失败:", error);
    } finally {
      setSaving(false);
    }
  };

  const filteredPrompts = prompts.filter(
    (prompt) =>
      prompt.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      prompt.key.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const hasChanges =
    selectedPrompt && editedContent !== selectedPrompt.content;

  return (
    <div className="h-full flex bg-background/50">
      {/* 左侧列表 */}
      <div className="w-80 border-r border-border flex flex-col bg-card min-h-0 overflow-hidden">
        <PageHeader 
          icon={BookOpen} 
          title="提示词管理" 
        />
        <div className="p-3 border-b border-border/50 space-y-4">
          <div className="relative">
            <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
            <Input
              placeholder="搜索提示词..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="h-8 pl-8 text-sm bg-background/50 border-border/50 hover:border-primary/30 focus:border-primary/50 transition-colors"
            />
          </div>
        </div>

        <ScrollArea className="flex-1 min-h-0">
          <div className="p-3 overflow-hidden">
          {loading ? (
            <div className="text-center py-12 text-muted-foreground text-sm">
              <Loader2 className="h-5 w-5 animate-spin mx-auto mb-2" />
              加载中...
            </div>
          ) : filteredPrompts.length === 0 ? (
            <EmptyState icon={BookOpen} title="暂无提示词" />
          ) : (
            <div className="space-y-1">
              {filteredPrompts.map((prompt) => {
                const isSelected = selectedPrompt?.key === prompt.key;
                return (
                  <div
                    key={prompt.key}
                    onClick={() => handleSelect(prompt)}
                    className={cn(
                      "p-2.5 rounded-md cursor-pointer transition-colors",
                      isSelected
                        ? "list-item-selected"
                        : "list-item-hover"
                    )}
                  >
                    <div className="flex items-start gap-2.5">
                      <div className="h-7 w-7 rounded-md bg-amber-500/10 flex items-center justify-center shrink-0">
                        <BookOpen className="h-3.5 w-3.5 text-amber-500" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="font-medium text-sm truncate text-foreground">
                          {prompt.name}
                        </p>
                        <p className="text-xs text-muted-foreground truncate mt-0.5">
                          {prompt.key}
                        </p>
                        <div className="flex items-center gap-1.5 mt-1.5">
                          <span className="text-[10px] px-1.5 py-0.5 rounded bg-muted text-muted-foreground">
                            {prompt.category}
                          </span>
                          <span className={cn(
                            "text-[10px] px-1.5 py-0.5 rounded",
                            prompt.source === "custom"
                              ? "bg-amber-500/10 text-amber-600"
                              : "bg-muted text-muted-foreground"
                          )}>
                            {prompt.source === "custom" ? "已修改" : "默认"}
                          </span>
                        </div>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
          </div>
        </ScrollArea>
      </div>

      {/* 右侧编辑器 */}
      <div className="flex-1 min-w-0 flex flex-col bg-background/50">
        {selectedPrompt ? (
          <>
            <div className="p-6 border-b border-border/50 bg-card">
              <div className="flex items-start justify-between">
                <div>
                  <h2 className="text-xl font-bold text-foreground">{selectedPrompt.name}</h2>
                  <p className="text-muted-foreground text-sm mt-1">
                    {selectedPrompt.description || selectedPrompt.key}
                  </p>
                </div>
                <div className="flex gap-2">
                  {selectedPrompt.source === "custom" && (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={handleReset}
                      disabled={saving}
                      className="hover:bg-accent/10 hover:border-accent/30 hover:text-accent transition-all duration-200"
                    >
                      <RotateCcw className="h-4 w-4 mr-1" />
                      恢复默认
                    </Button>
                  )}
                  <Button
                    size="sm"
                    variant="default"
                    onClick={handleSave}
                    disabled={saving || !hasChanges}
                  >
                    {saving ? (
                      <Loader2 className="h-4 w-4 mr-1 animate-spin" />
                    ) : (
                      <Save className="h-4 w-4 mr-1" />
                    )}
                    保存
                  </Button>
                </div>
              </div>

              {selectedPrompt.variables.length > 0 && (
                <div className="mt-4">
                  <span className="text-sm text-muted-foreground">
                    可用变量：
                  </span>
                  {selectedPrompt.variables.map((v) => (
                    <code
                      key={v}
                      className="text-xs mx-1 px-2 py-1 rounded-full bg-primary/10 text-primary font-medium"
                    >
                      {`{${v}}`}
                    </code>
                  ))}
                </div>
              )}
            </div>

            <div className="flex-1 p-6 overflow-hidden">
              <RichEditor
                ref={editorRef}
                initialContent={editedContent}
                placeholder="输入提示词内容（支持 Markdown 格式）..."
                onMarkdownChange={handleMarkdownChange}
                showToolbar={true}
                minHeight={400}
                editable={!saving}
              />
            </div>
          </>
        ) : (
          <EmptyState icon={BookOpen} title="未选择提示词" description="请从左侧列表中选择一个提示词进行编辑" />
        )}
      </div>
    </div>
  );
}
