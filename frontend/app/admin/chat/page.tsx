"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { Send, Loader2, Bot, RotateCcw, AlertCircle, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { RichEditor, type RichEditorRef } from "@/components/rich-editor";
import { useChatStore } from "@/lib/stores";
import type { TimelineItem } from "@/lib/timeline";
import {
  LLMCallCluster,
  TimelineUserMessageItem,
  TimelineToolCallItem,
  TimelineErrorItem,
  TimelineSkillActivatedItem,
  TimelineWaitingItem,
  TimelineIntentExtractedItem,
  TimelineSearchResultsItem,
  TimelineToolsRegisteredItem,
  TimelinePhaseChangedItem,
} from "@/components/chat/timeline";

export default function ChatPage() {
  const timeline = useChatStore((s) => s.timeline());
  const isStreaming = useChatStore((s) => s.isStreaming);
  const error = useChatStore((s) => s.error);
  const sendMessage = useChatStore((s) => s.sendMessage);
  const abortStream = useChatStore((s) => s.abortStream);
  const clearMessages = useChatStore((s) => s.clearMessages);

  const [markdown, setMarkdown] = useState("");
  const [dismissedError, setDismissedError] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const editorRef = useRef<RichEditorRef>(null);

  const isErrorVisible = Boolean(error) && dismissedError !== error;

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [timeline]);

  const handleSend = useCallback(() => {
    if (!markdown.trim() || isStreaming) return;
    sendMessage(markdown.trim());
    setMarkdown("");
    editorRef.current?.clear();
  }, [markdown, isStreaming, sendMessage]);

  const handleMarkdownChange = useCallback((content: string) => {
    setMarkdown(content);
  }, []);

  const handleButtonClick = () => {
    if (isStreaming) {
      abortStream();
    } else {
      handleSend();
    }
  };

  const renderTimelineItem = (item: TimelineItem) => {
    switch (item.type) {
      case "user.message":
        return (
          <div key={item.id} className="mx-auto max-w-3xl px-6">
            <TimelineUserMessageItem item={item} />
          </div>
        );

      case "llm.call.cluster":
        return (
          <div key={item.id} className="mx-auto max-w-3xl px-6">
            <LLMCallCluster item={item} isStreaming={isStreaming} />
          </div>
        );

      case "tool.call":
        return (
          <div key={item.id} className="mx-auto max-w-3xl px-6">
            <TimelineToolCallItem item={item} />
          </div>
        );

      case "error":
        return (
          <div key={item.id} className="mx-auto max-w-3xl px-6">
            <TimelineErrorItem item={item} />
          </div>
        );

      case "skill.activated":
        return <TimelineSkillActivatedItem key={item.id} item={item} />;

      case "intent.extracted":
        return (
          <div key={item.id} className="mx-auto max-w-3xl px-6">
            <TimelineIntentExtractedItem item={item} />
          </div>
        );

      case "search.results":
        return (
          <div key={item.id} className="mx-auto max-w-3xl px-6">
            <TimelineSearchResultsItem item={item} />
          </div>
        );

      case "tools.registered":
        return (
          <div key={item.id} className="mx-auto max-w-3xl px-6">
            <TimelineToolsRegisteredItem item={item} />
          </div>
        );

      case "phase.changed":
        return (
          <div key={item.id} className="mx-auto max-w-3xl px-6">
            <TimelinePhaseChangedItem item={item} />
          </div>
        );

      case "waiting":
        return (
          <div key={item.id} className="mx-auto max-w-3xl px-6">
            <TimelineWaitingItem />
          </div>
        );

      case "final":
        return null;

      default:
        return null;
    }
  };

  return (
    <div className="h-full flex flex-col bg-background/50">
      {/* 头部 */}
      <div className="h-14 border-b border-border/50 bg-card/80 backdrop-blur-xl flex items-center justify-between px-6">
        <div className="flex items-center gap-3">
          <div className="h-8 w-8 rounded-lg bg-gradient-to-br from-orange-500 to-amber-600 flex items-center justify-center shadow-md">
            <Bot className="h-4 w-4 text-white" />
          </div>
          <div>
            <h1 className="font-semibold text-foreground">智能对话</h1>
            <p className="text-xs text-muted-foreground">基于知识库的 AI 助手</p>
          </div>
        </div>
        {timeline.length > 0 && (
          <Button
            variant="outline"
            size="sm"
            onClick={clearMessages}
            disabled={isStreaming}
            className="hover:bg-primary/10 hover:border-primary/30 hover:text-primary transition-all duration-200"
          >
            <RotateCcw className="h-4 w-4 mr-1" />
            新对话
          </Button>
        )}
      </div>

      {/* 消息区域 */}
      <ScrollArea ref={scrollRef} className="flex-1">
        <div className="py-6 space-y-4">
          {timeline.length === 0 ? (
            <div className="text-center py-20">
              <div className="mx-auto mb-6 h-20 w-20 rounded-2xl bg-gradient-to-br from-primary/10 via-primary/5 to-accent/10 border border-border/50 flex items-center justify-center">
                <Bot className="h-10 w-10 text-primary" />
              </div>
              <h2 className="text-xl font-semibold text-foreground mb-2">开始对话</h2>
              <p className="text-muted-foreground text-sm max-w-md mx-auto">
                向我提问关于知识库的任何问题，我会根据已有的技能和文档为您解答
              </p>
              <div className="mt-6 flex flex-wrap justify-center gap-2">
                {["如何上传文档？", "有哪些技能可用？", "帮我搜索..."].map((suggestion) => (
                  <button
                    key={suggestion}
                    onClick={() => {
                      setMarkdown(suggestion);
                      editorRef.current?.setContent(suggestion);
                    }}
                    className="px-4 py-2 text-sm rounded-full bg-muted/50 hover:bg-muted text-muted-foreground hover:text-foreground border border-border/50 hover:border-primary/30 transition-all duration-200 cursor-pointer"
                  >
                    {suggestion}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            timeline.map((item) => renderTimelineItem(item))
          )}
        </div>
      </ScrollArea>

      {/* 输入区域 */}
      <div className="border-t border-border/50 bg-card/80 backdrop-blur-xl p-4">
        <div className="max-w-3xl mx-auto">
          {/* 错误提示 */}
          {error && isErrorVisible && (
            <div className="mb-3 flex items-center gap-2 rounded-xl bg-destructive/10 border border-destructive/20 p-3 text-sm text-destructive">
              <AlertCircle className="h-4 w-4 shrink-0" />
              <span className="flex-1">{error}</span>
              <button
                onClick={() => setDismissedError(error)}
                className="shrink-0 rounded-lg p-1 hover:bg-destructive/20 transition-colors cursor-pointer"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
          )}
          <div className="flex gap-3 items-end">
            <div className="flex-1 rounded-xl border border-border/50 bg-background/50 overflow-hidden hover:border-primary/30 focus-within:border-primary/50 transition-colors duration-200">
              <RichEditor
                ref={editorRef}
                initialContent=""
                placeholder="输入消息，支持 Markdown 格式..."
                onMarkdownChange={handleMarkdownChange}
                showToolbar={false}
                minHeight={60}
                maxHeight={150}
                editable={!isStreaming}
                className="border-0"
              />
            </div>
            <Button
              onClick={handleButtonClick}
              disabled={!isStreaming && !markdown.trim()}
              size="icon"
              className={`h-[60px] w-[60px] rounded-xl shadow-lg transition-all duration-200 ${
                isStreaming 
                  ? "bg-destructive hover:bg-destructive/90 shadow-destructive/25" 
                  : "bg-gradient-to-br from-primary to-primary/80 hover:from-primary/90 hover:to-primary/70 shadow-primary/25 hover:shadow-xl hover:shadow-primary/30"
              }`}
              variant={isStreaming ? "destructive" : "default"}
            >
              {isStreaming ? (
                <X className="h-5 w-5" />
              ) : (
                <Send className="h-5 w-5" />
              )}
            </Button>
          </div>
          <p className="text-xs text-muted-foreground mt-2 text-center">
            支持 Markdown 格式输入，AI 回答仅供参考
          </p>
        </div>
      </div>
    </div>
  );
}
