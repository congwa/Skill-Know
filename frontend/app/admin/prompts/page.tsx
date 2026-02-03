"use client";

import { useEffect, useState, useRef, useCallback } from "react";
import { Search, BookOpen, RotateCcw, Save, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { listPrompts, updatePrompt, resetPrompt, type Prompt } from "@/lib/api/prompts";
import { cn } from "@/lib/utils";
import { RichEditor, type RichEditorRef } from "@/components/rich-editor";

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
        <div className="p-4 border-b border-border/50 space-y-4">
          <div className="flex items-center gap-2">
            <div className="h-8 w-8 rounded-lg bg-gradient-to-br from-amber-500 to-orange-600 flex items-center justify-center shadow-md">
              <BookOpen className="h-4 w-4 text-white" />
            </div>
            <h1 className="text-lg font-semibold text-foreground">提示词管理</h1>
          </div>
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="搜索提示词..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-9 bg-background/50 border-border/50 hover:border-primary/30 focus:border-primary/50 transition-colors"
            />
          </div>
        </div>

        <ScrollArea className="flex-1 min-h-0">
          <div className="p-4 overflow-hidden">
          {loading ? (
            <div className="text-center py-8 text-muted-foreground">
              <div className="h-5 w-5 border-2 border-primary/30 border-t-primary rounded-full animate-spin mx-auto mb-2" />
              加载中...
            </div>
          ) : filteredPrompts.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              <BookOpen className="h-8 w-8 mx-auto mb-2 opacity-50" />
              暂无提示词
            </div>
          ) : (
            <div className="space-y-1">
              {filteredPrompts.map((prompt) => {
                const isSelected = selectedPrompt?.key === prompt.key;
                return (
                  <div
                    key={prompt.key}
                    onClick={() => handleSelect(prompt)}
                    className={cn(
                      "p-3 rounded-lg cursor-pointer transition-colors",
                      isSelected
                        ? "list-item-selected"
                        : "list-item-hover"
                    )}
                  >
                    <div className="flex items-start gap-3">
                      <div className="h-8 w-8 rounded-lg bg-amber-500/10 flex items-center justify-center shrink-0">
                        <BookOpen className="h-4 w-4 text-amber-500" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="font-medium text-sm truncate text-foreground">
                          {prompt.name}
                        </p>
                        <p className="text-xs text-muted-foreground truncate">
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
            <div className="p-6 border-b border-border/50 bg-card/80 backdrop-blur-xl">
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
                      className="hover:bg-primary/10 hover:border-primary/30 hover:text-primary transition-all duration-200"
                    >
                      <RotateCcw className="h-4 w-4 mr-1" />
                      恢复默认
                    </Button>
                  )}
                  <Button
                    size="sm"
                    onClick={handleSave}
                    disabled={saving || !hasChanges}
                    className="bg-gradient-to-r from-primary to-primary/80 hover:from-primary/90 hover:to-primary/70 shadow-md shadow-primary/20"
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
          <div className="h-full flex flex-col items-center justify-center text-muted-foreground">
            <div className="h-16 w-16 rounded-2xl bg-muted/50 flex items-center justify-center mb-4">
              <BookOpen className="h-8 w-8 opacity-50" />
            </div>
            <p>选择一个提示词进行编辑</p>
          </div>
        )}
      </div>
    </div>
  );
}
