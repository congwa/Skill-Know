"use client";

import { useEffect, useState, useRef, useMemo } from "react";
import {
  Plus,
  Search,
  FileText,
  Folder,
  Upload,
  Trash2,
  FolderOpen,
  Sparkles,
  Loader2,
  CheckCircle2,
  Circle,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { uploadDocument, listDocuments } from "@/lib/api/documents";
import { useDocumentStore } from "@/lib/stores";
import { cn } from "@/lib/utils";
import { format } from "date-fns";
import { BatchUploadDialog } from "@/components/upload";

type SkillFilter = "all" | "converted" | "not_converted";

export default function DocumentsPage() {
  const {
    documents,
    folders,
    selectedDocument,
    currentFolderId,
    isLoading,
    isConverting,
    loadAll,
    selectDocument,
    setCurrentFolder,
    convertToSkill,
    deleteDocument,
  } = useDocumentStore();

  const [searchQuery, setSearchQuery] = useState("");
  const [uploading, setUploading] = useState(false);
  const [batchUploadOpen, setBatchUploadOpen] = useState(false);
  const [skillFilter, setSkillFilter] = useState<SkillFilter>("all");
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    loadAll(currentFolderId);
  }, [currentFolderId, loadAll]);

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploading(true);
    try {
      await uploadDocument(file, { folder_id: currentFolderId || undefined });
      loadAll(currentFolderId);
    } catch (error) {
      console.error("上传失败:", error);
    } finally {
      setUploading(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    }
  };

  const handleConvertToSkill = async () => {
    if (!selectedDocument) return;

    const success = await convertToSkill(selectedDocument.id);
    if (success) {
      alert("转换成功！");
    } else {
      alert("转换失败，请重试");
    }
  };

  const handleDelete = async () => {
    if (!selectedDocument) return;
    if (!confirm("确定要删除这个文档吗？")) return;

    const success = await deleteDocument(selectedDocument.id);
    if (!success) {
      alert("删除失败，请重试");
    }
  };

  const filteredDocuments = useMemo(
    () =>
      documents.filter((doc) => {
        // 搜索过滤
        const matchesSearch =
          doc.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
          doc.description?.toLowerCase().includes(searchQuery.toLowerCase());
        if (!matchesSearch) return false;

        // 技能转化状态过滤（使用文档的 is_converted 字段）
        if (skillFilter === "converted") {
          return doc.is_converted === true;
        }
        if (skillFilter === "not_converted") {
          return doc.is_converted === false;
        }
        return true;
      }),
    [documents, searchQuery, skillFilter]
  );

  const getFileIcon = (fileType: string) => {
    return FileText;
  };

  return (
    <div className="h-full flex bg-background/50">
      {/* 左侧列表 */}
      <div className="w-80 border-r border-border flex flex-col bg-card min-h-0 overflow-hidden">
        <div className="p-4 border-b border-border/50 space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="h-8 w-8 rounded-lg bg-gradient-to-br from-blue-500 to-cyan-600 flex items-center justify-center shadow-md">
                <FileText className="h-4 w-4 text-white" />
              </div>
              <h1 className="text-lg font-semibold text-foreground">文档管理</h1>
            </div>
          </div>
          <div className="flex gap-2">
            <input
              ref={fileInputRef}
              type="file"
              className="hidden"
              onChange={handleUpload}
              accept=".txt,.md,.markdown,.pdf,.docx,.doc"
            />
            <Button
              size="sm"
              variant="outline"
              onClick={() => fileInputRef.current?.click()}
              disabled={uploading}
              className="flex-1 hover:bg-primary/10 hover:border-primary/30 hover:text-primary transition-all duration-200"
            >
              <Upload className="h-4 w-4 mr-1" />
              单文件
            </Button>
            <Button
              size="sm"
              className="flex-1 bg-gradient-to-r from-primary to-primary/80 hover:from-primary/90 hover:to-primary/70 shadow-md shadow-primary/20"
              onClick={() => setBatchUploadOpen(true)}
            >
              <Plus className="h-4 w-4 mr-1" />
              批量上传
            </Button>
          </div>
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="搜索文档..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-9 bg-background/50 border-border/50 hover:border-primary/30 focus:border-primary/50 transition-colors"
            />
          </div>
          {/* 技能转化状态过滤 */}
          <div className="flex gap-1">
            <button
              onClick={() => setSkillFilter("all")}
              className={cn(
                "flex-1 px-2 py-1.5 text-xs rounded-md transition-colors",
                skillFilter === "all"
                  ? "bg-primary text-primary-foreground"
                  : "bg-muted text-muted-foreground hover:text-foreground"
              )}
            >
              全部
            </button>
            <button
              onClick={() => setSkillFilter("converted")}
              className={cn(
                "flex-1 px-2 py-1.5 text-xs rounded-md transition-colors flex items-center justify-center gap-1",
                skillFilter === "converted"
                  ? "bg-emerald-500 text-white"
                  : "bg-muted text-muted-foreground hover:text-foreground"
              )}
            >
              <CheckCircle2 className="h-3 w-3" />
              已转化
            </button>
            <button
              onClick={() => setSkillFilter("not_converted")}
              className={cn(
                "flex-1 px-2 py-1.5 text-xs rounded-md transition-colors flex items-center justify-center gap-1",
                skillFilter === "not_converted"
                  ? "bg-amber-500 text-white"
                  : "bg-muted text-muted-foreground hover:text-foreground"
              )}
            >
              <Circle className="h-3 w-3" />
              未转化
            </button>
          </div>
        </div>

        <ScrollArea className="flex-1 min-h-0">
          <div className="p-4 overflow-hidden">
          {isLoading ? (
            <div className="text-center py-8 text-muted-foreground">
              <Loader2 className="h-5 w-5 animate-spin mx-auto mb-2" />
              加载中...
            </div>
          ) : (
            <div className="space-y-2 overflow-hidden">
              {/* 返回上级 */}
              {currentFolderId && (
                <div
                  onClick={() => setCurrentFolder(null)}
                  className="p-3 rounded-xl border border-border/50 cursor-pointer hover:bg-muted/50 hover:border-primary/20 transition-all duration-200 flex items-center gap-3"
                >
                  <FolderOpen className="h-4 w-4 text-muted-foreground" />
                  <span className="text-sm text-foreground">返回上级</span>
                </div>
              )}

              {/* 文件夹 */}
              {folders.map((folder) => (
                <div
                  key={folder.id}
                  onClick={() => setCurrentFolder(folder.id)}
                  className="p-3 rounded-xl border border-border/50 cursor-pointer hover:bg-muted/50 hover:border-amber-500/30 transition-all duration-200 flex items-center gap-3 group"
                >
                  <div className="h-8 w-8 rounded-lg bg-amber-500/10 flex items-center justify-center group-hover:bg-amber-500/20 transition-colors">
                    <Folder className="h-4 w-4 text-amber-500" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="font-medium text-sm truncate text-foreground">
                      {folder.name}
                    </div>
                    {folder.description && (
                      <div className="text-xs text-muted-foreground truncate">
                        {folder.description}
                      </div>
                    )}
                  </div>
                </div>
              ))}

              {/* 文档 */}
              {filteredDocuments.length === 0 && folders.length === 0 ? (
                <div className="text-center py-8 text-muted-foreground">
                  <FileText className="h-8 w-8 mx-auto mb-2 opacity-50" />
                  暂无文档
                </div>
              ) : (
                filteredDocuments.map((doc) => {
                  const FileIcon = getFileIcon(doc.file_type);
                  const isSelected = selectedDocument?.id === doc.id;
                  return (
                    <div
                      key={doc.id}
                      onClick={() => selectDocument(doc)}
                      className={cn(
                        "p-3 rounded-lg cursor-pointer transition-colors",
                        isSelected
                          ? "list-item-selected"
                          : "list-item-hover"
                      )}
                    >
                      <div className="flex items-start gap-3">
                        <div className="h-8 w-8 rounded-lg bg-blue-500/10 flex items-center justify-center shrink-0">
                          <FileIcon className="h-4 w-4 text-blue-500" />
                        </div>
                        <div className="flex-1 min-w-0">
                          <p className="font-medium text-sm truncate text-foreground">
                            {doc.title}
                          </p>
                          <p className="text-xs text-muted-foreground">
                            {doc.file_type.toUpperCase()} · {(doc.file_size / 1024).toFixed(1)} KB
                          </p>
                          <div className="flex items-center gap-1.5 mt-1.5">
                            <span
                              className={cn(
                                "text-[10px] px-1.5 py-0.5 rounded",
                                doc.status === "completed"
                                  ? "bg-emerald-500/10 text-emerald-600"
                                  : doc.status === "failed"
                                  ? "bg-destructive/10 text-destructive"
                                  : "bg-amber-500/10 text-amber-600"
                              )}
                            >
                              {doc.status === "completed"
                                ? "已处理"
                                : doc.status === "failed"
                                ? "处理失败"
                                : "处理中"}
                            </span>
                            {doc.category && (
                              <span className="text-[10px] px-1.5 py-0.5 rounded bg-muted text-muted-foreground">
                                {doc.category}
                              </span>
                            )}
                            {doc.is_converted && (
                              <span className="text-[10px] px-1.5 py-0.5 rounded bg-violet-500/10 text-violet-600 flex items-center gap-0.5">
                                <Sparkles className="h-2.5 w-2.5" />
                                已转技能
                              </span>
                            )}
                          </div>
                        </div>
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          )}
          </div>
        </ScrollArea>
      </div>

      {/* 右侧详情 */}
      <div className="flex-1 min-w-0 overflow-auto p-6 bg-background/50">
        {selectedDocument ? (
          <div className="max-w-3xl space-y-6">
            <div className="flex items-start justify-between">
              <div>
                <h2 className="text-2xl font-bold text-foreground">{selectedDocument.title}</h2>
                <p className="text-muted-foreground mt-1">
                  {selectedDocument.description || "暂无描述"}
                </p>
              </div>
              <div className="flex gap-2">
                <Button
                  size="sm"
                  onClick={handleConvertToSkill}
                  disabled={isConverting}
                  className="bg-gradient-to-r from-violet-500 to-purple-600 hover:from-violet-600 hover:to-purple-700 shadow-md shadow-violet-500/20"
                >
                  {isConverting ? (
                    <Loader2 className="h-4 w-4 mr-1 animate-spin" />
                  ) : (
                    <Sparkles className="h-4 w-4 mr-1" />
                  )}
                  {isConverting ? "转换中..." : "转为 Skill"}
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  className="text-destructive hover:bg-destructive/10 hover:border-destructive/30"
                  onClick={handleDelete}
                >
                  <Trash2 className="h-4 w-4 mr-1" />
                  删除
                </Button>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <Card className="bg-card/80 backdrop-blur-sm border-border/50">
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm text-foreground">文件信息</CardTitle>
                </CardHeader>
                <CardContent className="text-sm space-y-1 text-muted-foreground">
                  <div>文件名: <span className="text-foreground">{selectedDocument.filename}</span></div>
                  <div>类型: <span className="text-foreground">{selectedDocument.file_type.toUpperCase()}</span></div>
                  <div>大小: <span className="text-foreground">{(selectedDocument.file_size / 1024).toFixed(1)} KB</span></div>
                </CardContent>
              </Card>
              <Card className="bg-card/80 backdrop-blur-sm border-border/50">
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm text-foreground">时间</CardTitle>
                </CardHeader>
                <CardContent className="text-sm space-y-1 text-muted-foreground">
                  <div>
                    创建: <span className="text-foreground">{format(new Date(selectedDocument.created_at), "yyyy-MM-dd HH:mm")}</span>
                  </div>
                  <div>
                    更新: <span className="text-foreground">{format(new Date(selectedDocument.updated_at), "yyyy-MM-dd HH:mm")}</span>
                  </div>
                </CardContent>
              </Card>
            </div>

            {selectedDocument.tags.length > 0 && (
              <Card className="bg-card/80 backdrop-blur-sm border-border/50">
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm text-foreground">标签</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="flex flex-wrap gap-2">
                    {selectedDocument.tags.map((tag, i) => (
                      <span
                        key={i}
                        className="px-3 py-1 text-xs rounded-full bg-primary/10 text-primary font-medium"
                      >
                        {tag}
                      </span>
                    ))}
                  </div>
                </CardContent>
              </Card>
            )}

            {selectedDocument.content && (
              <Card className="bg-card/80 backdrop-blur-sm border-border/50">
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm text-foreground">文档内容</CardTitle>
                </CardHeader>
                <CardContent>
                  <pre className="text-sm whitespace-pre-wrap bg-muted/50 p-4 rounded-xl overflow-auto max-h-96 border border-border/50 text-foreground">
                    {selectedDocument.content}
                  </pre>
                </CardContent>
              </Card>
            )}
          </div>
        ) : (
          <div className="h-full flex flex-col items-center justify-center text-muted-foreground">
            <div className="h-16 w-16 rounded-2xl bg-muted/50 flex items-center justify-center mb-4">
              <FileText className="h-8 w-8 opacity-50" />
            </div>
            <p>选择一个文档查看详情</p>
          </div>
        )}
      </div>

      {/* 批量上传对话框 */}
      <BatchUploadDialog
        open={batchUploadOpen}
        onOpenChange={setBatchUploadOpen}
        folderId={currentFolderId || undefined}
        onComplete={() => {
          loadAll(currentFolderId);
        }}
      />
    </div>
  );
}
