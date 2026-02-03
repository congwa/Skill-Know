"use client";

import { useEffect } from "react";
import { Search, Sparkles, FileText, Database, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { ScrollArea } from "@/components/ui/scroll-area";
import { useSearchStore } from "@/lib/stores";

export default function SearchPage() {
  const {
    query,
    sqlQuery,
    results: searchResult,
    sqlResults: sqlResult,
    isSearching: loading,
    tables,
    setQuery,
    setSqlQuery,
    search: handleSearch,
    executeSql: handleSqlSearch,
    loadTables,
  } = useSearchStore();

  useEffect(() => {
    loadTables();
  }, [loadTables]);

  return (
    <div className="h-full overflow-auto p-6 bg-background/50">
      <div className="max-w-4xl mx-auto space-y-6">
        {/* Hero 区域 */}
        <div className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-emerald-500/10 via-teal-500/5 to-cyan-500/10 border border-border/50 p-6">
          <div className="absolute top-0 right-0 w-48 h-48 bg-emerald-500/10 rounded-full blur-3xl -translate-y-1/2 translate-x-1/2" />
          <div className="relative z-10 flex items-center gap-4">
            <div className="h-12 w-12 rounded-xl bg-gradient-to-br from-emerald-500 to-teal-600 flex items-center justify-center shadow-lg shadow-emerald-500/25">
              <Search className="h-6 w-6 text-white" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-foreground">知识搜索</h1>
              <p className="text-muted-foreground">
                搜索技能和文档，支持自然语言和 SQL 查询
              </p>
            </div>
          </div>
        </div>

        <Tabs defaultValue="unified" className="space-y-4">
          <TabsList className="bg-muted/50 p-1">
            <TabsTrigger value="unified" className="data-[state=active]:bg-background data-[state=active]:shadow-sm">
              <Search className="h-4 w-4 mr-2" />
              智能搜索
            </TabsTrigger>
            <TabsTrigger value="sql" onClick={loadTables} className="data-[state=active]:bg-background data-[state=active]:shadow-sm">
              <Database className="h-4 w-4 mr-2" />
              SQL 搜索
            </TabsTrigger>
          </TabsList>

          <TabsContent value="unified" className="space-y-4">
            <div className="flex gap-2">
              <div className="relative flex-1">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="输入搜索关键词..."
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && handleSearch()}
                  className="pl-9 bg-background/50 border-border/50 hover:border-primary/30 focus:border-primary/50 transition-colors"
                />
              </div>
              <Button onClick={handleSearch} disabled={loading || !query.trim()} className="bg-gradient-to-r from-primary to-primary/80 hover:from-primary/90 hover:to-primary/70 shadow-md shadow-primary/20">
                {loading ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  "搜索"
                )}
              </Button>
            </div>

            {searchResult && (
              <div className="space-y-4">
                <div className="text-sm text-muted-foreground">
                  找到 <span className="font-semibold text-foreground">{searchResult.total}</span> 个结果
                </div>

                {searchResult.skills.length > 0 && (
                  <div>
                    <h3 className="font-medium mb-3 flex items-center gap-2 text-foreground">
                      <div className="h-6 w-6 rounded-lg bg-violet-500/10 flex items-center justify-center">
                        <Sparkles className="h-3.5 w-3.5 text-violet-500" />
                      </div>
                      技能 ({searchResult.skills.length})
                    </h3>
                    <div className="space-y-2">
                      {searchResult.skills.map((skill) => (
                        <Card key={skill.id} className="bg-card/80 backdrop-blur-sm border-border/50 hover:shadow-lg hover:border-primary/20 transition-all duration-200 cursor-pointer">
                          <CardHeader className="py-3">
                            <div className="flex items-start justify-between">
                              <div>
                                <CardTitle className="text-base text-foreground">
                                  {skill.name}
                                </CardTitle>
                                <CardDescription>
                                  {skill.description}
                                </CardDescription>
                              </div>
                              <span className="text-xs px-2 py-1 rounded-full bg-violet-500/10 text-violet-600 font-medium">
                                {skill.type}
                              </span>
                            </div>
                          </CardHeader>
                          <CardContent className="py-2">
                            <p className="text-sm text-muted-foreground line-clamp-2">
                              {skill.content_preview}
                            </p>
                          </CardContent>
                        </Card>
                      ))}
                    </div>
                  </div>
                )}

                {searchResult.documents.length > 0 && (
                  <div>
                    <h3 className="font-medium mb-3 flex items-center gap-2 text-foreground">
                      <div className="h-6 w-6 rounded-lg bg-blue-500/10 flex items-center justify-center">
                        <FileText className="h-3.5 w-3.5 text-blue-500" />
                      </div>
                      文档 ({searchResult.documents.length})
                    </h3>
                    <div className="space-y-2">
                      {searchResult.documents.map((doc) => (
                        <Card key={doc.id} className="bg-card/80 backdrop-blur-sm border-border/50 hover:shadow-lg hover:border-primary/20 transition-all duration-200 cursor-pointer">
                          <CardHeader className="py-3">
                            <div className="flex items-start justify-between">
                              <div>
                                <CardTitle className="text-base text-foreground">
                                  {doc.title}
                                </CardTitle>
                                <CardDescription>
                                  {doc.description || "暂无描述"}
                                </CardDescription>
                              </div>
                              {doc.category && (
                                <span className="text-xs px-2 py-1 rounded-full bg-blue-500/10 text-blue-600 font-medium">
                                  {doc.category}
                                </span>
                              )}
                            </div>
                          </CardHeader>
                          {doc.content_preview && (
                            <CardContent className="py-2">
                              <p className="text-sm text-muted-foreground line-clamp-2">
                                {doc.content_preview}
                              </p>
                            </CardContent>
                          )}
                        </Card>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </TabsContent>

          <TabsContent value="sql" className="space-y-4">
            {tables.length > 0 && (
              <Card className="bg-card/80 backdrop-blur-sm border-border/50">
                <CardHeader className="py-3">
                  <CardTitle className="text-sm text-foreground flex items-center gap-2">
                    <Database className="h-4 w-4 text-primary" />
                    可用表
                  </CardTitle>
                </CardHeader>
                <CardContent className="py-2">
                  <div className="space-y-3 text-sm">
                    {tables.map((table) => (
                      <div key={table.name} className="p-3 rounded-xl bg-muted/50 border border-border/50">
                        <span className="font-mono font-semibold text-primary">
                          {table.name}
                        </span>
                        <span className="text-muted-foreground ml-2">
                          - {table.description}
                        </span>
                        <div className="text-xs text-muted-foreground mt-2 font-mono">
                          字段: {table.columns.join(", ")}
                        </div>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            )}

            <div className="space-y-3">
              <textarea
                placeholder="输入 SQL 查询语句（仅支持 SELECT）..."
                value={sqlQuery}
                onChange={(e) => setSqlQuery(e.target.value)}
                className="w-full h-32 p-4 rounded-xl border border-border/50 bg-background/50 text-foreground font-mono text-sm resize-none focus:outline-none focus:border-primary/50 hover:border-primary/30 transition-colors"
              />
              <Button
                onClick={handleSqlSearch}
                disabled={loading || !sqlQuery.trim()}
                className="bg-gradient-to-r from-primary to-primary/80 hover:from-primary/90 hover:to-primary/70 shadow-md shadow-primary/20"
              >
                {loading ? (
                  <Loader2 className="h-4 w-4 animate-spin mr-2" />
                ) : (
                  <Database className="h-4 w-4 mr-2" />
                )}
                执行查询
              </Button>
            </div>

            {sqlResult && (
              <Card className="bg-card/80 backdrop-blur-sm border-border/50">
                <CardHeader className="py-3">
                  <CardTitle className="text-sm text-foreground">
                    查询结果 (<span className="text-primary">{sqlResult.count}</span> 条)
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  {sqlResult.error ? (
                    <div className="text-destructive text-sm p-3 rounded-xl bg-destructive/10 border border-destructive/20">{sqlResult.error}</div>
                  ) : sqlResult.results.length === 0 ? (
                    <div className="text-muted-foreground text-sm text-center py-4">
                      无结果
                    </div>
                  ) : (
                    <ScrollArea className="max-h-96">
                      <div className="overflow-x-auto">
                        <table className="w-full text-sm">
                          <thead>
                            <tr className="border-b border-border/50 bg-muted/30">
                              {Object.keys(sqlResult.results[0]).map((key) => (
                                <th
                                  key={key}
                                  className="text-left p-3 font-semibold text-foreground"
                                >
                                  {key}
                                </th>
                              ))}
                            </tr>
                          </thead>
                          <tbody>
                            {sqlResult.results.map((row, i) => (
                              <tr key={i} className="border-b border-border/50 hover:bg-muted/30 transition-colors">
                                {Object.values(row).map((value, j) => (
                                  <td key={j} className="p-3 text-foreground">
                                    {String(value)}
                                  </td>
                                ))}
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </ScrollArea>
                  )}
                </CardContent>
              </Card>
            )}
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}
