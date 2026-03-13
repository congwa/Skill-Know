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
import { PageHeader } from "@/components/admin/page-header";
import { EmptyState } from "@/components/admin/empty-state";
import { FilterTabs } from "@/components/admin/filter-tabs";

type SkillFilter = "all" | "converted" | "not_converted";

const FILTER_TABS = [
  { value: "all", label: "全部" },
  { value: "converted", label: "已转化", icon: <CheckCircle2 className="h-3 w-3" /> },
  { value: "not_converted", label: "未转化", icon: <Circle className="h-3 w-3" /> },
] as const;

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
        <PageHeader 
          icon={FileText} 
          title="文档管理" 
        />
        
        <div className="p-3 border-b border-border/50 space-y-3">
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
              className="flex-1 hover:bg-accent/10 hover:border-accent/30 hover:text-accent transition-all duration-200"
            >
              <Upload className="h-4 w-4 mr-1" />
              单文件
            </Button>
            <Button
              size="sm"
              className="flex-1"
              onClick={() => setBatchUploadOpen(true)}
            >
              <Plus className="h-4 w-4 mr-1" />
              批量上传
            </Button>
          </div>
          <div className="relative">
            <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
            <Input
              placeholder="搜索文档..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="h-8 pl-8 text-sm bg-background/50 border-border/50 hover:border-primary/30 focus:border-primary/50 transition-colors"
            />
          </div>
          <FilterTabs 
            tabs={FILTER_TABS} 
            value={skillFilter} 
            onChange={(val) => setSkillFilter(val as SkillFilter)} 
          />
        </div>

        <ScrollArea className="flex-1 min-h-0">
          <div className="p-3 overflow-hidden">
          {isLoading ? (
            <div className="text-center py-12 text-muted-foreground text-sm">
              <Loader2 className="h-5 w-5 animate-spin mx-auto mb-2" />
              加载中...
            </div>
          ) : (
            <div className="space-y-1 overflow-hidden">
              {/* 返回上级 */}
              {currentFolderId && (
                <div
                  onClick={() => setCurrentFolder(null)}
                  className="p-2.5 rounded-md border border-border/50 cursor-pointer hover:bg-muted/50 hover:border-primary/20 transition-all duration-200 flex items-center gap-3"
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
                  className="p-2.5 rounded-md border border-border/50 cursor-pointer hover:bg-muted/50 hover:border-amber-500/30 transition-all duration-200 flex items-center gap-3 group"
                >
                  <div className="h-7 w-7 rounded-md bg-amber-500/10 flex items-center justify-center group-hover:bg-amber-500/20 transition-colors">
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
                <EmptyState icon={FileText} title="暂无文档" />
              ) : (
                filteredDocuments.map((doc) => {
                  const FileIcon = getFileIcon(doc.file_type);
                  const isSelected = selectedDocument?.id === doc.id;
                  return (
                    <div
                      key={doc.id}
                      onClick={() => selectDocument(doc)}
                      className={cn(
                        "p-2.5 rounded-md cursor-pointer transition-colors",
                        isSelected
                          ? "list-item-selected"
                          : "list-item-hover"
                      )}
                    >
                      <div className="flex items-start gap-2.5">
                        <div className="h-7 w-7 rounded-md bg-blue-500/10 flex items-center justify-center shrink-0">
                          <FileIcon className="h-3.5 w-3.5 text-blue-500" />
                        </div>
                        <div className="flex-1 min-w-0">
                          <p className="font-medium text-sm truncate text-foreground">
                            {doc.title}
                          </p>
                          <p className="text-xs text-muted-foreground mt-0.5">
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
          <div className="max-w-3xl mx-auto space-y-6">
            <div className="flex items-start justify-between">
              <div>
                <h2 className="text-xl font-bold text-foreground">{selectedDocument.title}</h2>
                <p className="text-sm text-muted-foreground mt-1">
                  {selectedDocument.description || "暂无描述"}
                </p>
              </div>
              <div className="flex gap-2">
                <Button
                  size="sm"
                  variant="default"
                  onClick={handleConvertToSkill}
                  disabled={isConverting}
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
              <Card className="bg-card border-border/50 rounded-xl">
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm text-foreground">文件信息</CardTitle>
                </CardHeader>
                <CardContent className="text-sm space-y-1 text-muted-foreground">
                  <div>文件名: <span className="text-foreground">{selectedDocument.filename}</span></div>
                  <div>类型: <span className="text-foreground">{selectedDocument.file_type.toUpperCase()}</span></div>
                  <div>大小: <span className="text-foreground">{(selectedDocument.file_size / 1024).toFixed(1)} KB</span></div>
                </CardContent>
              </Card>
              <Card className="bg-card border-border/50 rounded-xl">
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
              <Card className="bg-card border-border/50 rounded-xl">
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
              <Card className="bg-card border-border/50 rounded-xl">
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
          <EmptyState icon={FileText} title="未选择文档" description="请从左侧列表中选择一个文档查看详情" />
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
