"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { Loader2, CheckCircle, XCircle, Sparkles, Zap } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useSetupStore } from "@/lib/stores";

export default function QuickSetupPage() {
  const router = useRouter();
  const {
    providers,
    selectedProvider,
    isLoadingProviders,
    formData,
    testResult,
    isTesting,
    isSubmitting,
    loadProviders,
    selectProvider,
    selectModel,
    setApiKey,
    setBaseUrl,
    testConnectionAction,
    submitSetup,
  } = useSetupStore();

  useEffect(() => {
    loadProviders();
  }, [loadProviders]);

  const handleSubmit = async () => {
    const success = await submitSetup();
    if (success) {
      router.push("/admin");
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-6 relative overflow-hidden">
      {/* 背景装饰 */}
      <div className="absolute inset-0 bg-gradient-to-br from-background via-background to-primary/10" />
      <div className="absolute top-1/4 -right-32 w-96 h-96 bg-primary/20 rounded-full blur-3xl" />
      <div className="absolute bottom-1/4 -left-32 w-96 h-96 bg-accent/20 rounded-full blur-3xl" />
      
      {/* 步骤指示器 */}
      <div className="absolute top-8 left-1/2 -translate-x-1/2 flex items-center gap-3">
        <div className="flex items-center gap-2">
          <div className="h-8 w-8 rounded-full bg-primary text-primary-foreground flex items-center justify-center text-sm font-semibold shadow-lg shadow-primary/30">
            1
          </div>
          <span className="text-sm font-medium text-foreground">配置 API</span>
        </div>
        <div className="w-12 h-0.5 bg-border" />
        <div className="flex items-center gap-2">
          <div className="h-8 w-8 rounded-full bg-muted text-muted-foreground flex items-center justify-center text-sm font-semibold">
            2
          </div>
          <span className="text-sm text-muted-foreground">开始使用</span>
        </div>
      </div>

      <Card className="w-full max-w-lg border-border/50 bg-card/80 backdrop-blur-xl shadow-2xl shadow-primary/10 relative z-10">
        <CardHeader className="text-center pb-2">
          <div className="mx-auto mb-4 h-14 w-14 rounded-2xl bg-gradient-to-br from-primary via-primary/80 to-accent flex items-center justify-center shadow-lg shadow-primary/30">
            <Sparkles className="h-7 w-7 text-white" />
          </div>
          <CardTitle className="text-2xl font-bold text-foreground">欢迎使用 Skill-Know</CardTitle>
          <CardDescription className="text-muted-foreground">
            配置 LLM API 以开始使用知识库系统
          </CardDescription>
        </CardHeader>

        <CardContent className="space-y-5 pt-4">
          {isLoadingProviders ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="h-6 w-6 animate-spin text-primary" />
              <span className="ml-2 text-muted-foreground">加载提供商列表...</span>
            </div>
          ) : (
            <>
              <div className="space-y-2">
                <Label className="text-foreground font-medium">
                  LLM 提供商
                </Label>
                <Select
                  value={formData.llm_provider}
                  onValueChange={(value) => selectProvider(value)}
                >
                  <SelectTrigger className="bg-background/50 border-border hover:border-primary/50 transition-colors">
                    <SelectValue placeholder="选择提供商" />
                  </SelectTrigger>
                  <SelectContent className="bg-card/95 backdrop-blur-xl border-border">
                    {providers.map((provider) => (
                      <SelectItem
                        key={provider.id}
                        value={provider.id}
                        className="cursor-pointer"
                      >
                        {provider.name}
                        <span className="ml-2 text-xs text-muted-foreground">
                          ({provider.models.length} 模型)
                        </span>
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <p className="text-xs text-muted-foreground">
                  只显示支持工具调用 (Tool Calling) 的模型
                </p>
              </div>

              <div className="space-y-2">
                <Label className="text-foreground font-medium">
                  模型
                </Label>
                <Select
                  value={formData.llm_chat_model}
                  onValueChange={(value) => selectModel(value)}
                  disabled={!selectedProvider || selectedProvider.models.length === 0}
                >
                  <SelectTrigger className="bg-background/50 border-border hover:border-primary/50 transition-colors">
                    <SelectValue placeholder="选择模型" />
                  </SelectTrigger>
                  <SelectContent className="bg-card/95 backdrop-blur-xl border-border max-h-60">
                    {selectedProvider?.models.map((model) => (
                      <SelectItem
                        key={model.id}
                        value={model.id}
                        className="cursor-pointer"
                      >
                        <div className="flex items-center gap-2">
                          <span>{model.name}</span>
                          {model.reasoning && (
                            <span className="text-xs px-1.5 py-0.5 rounded-full bg-primary/10 text-primary font-medium">
                              推理
                            </span>
                          )}
                        </div>
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label htmlFor="api_key" className="text-foreground font-medium">
                  API Key <span className="text-destructive">*</span>
                </Label>
                <Input
                  id="api_key"
                  type="password"
                  value={formData.llm_api_key}
                  onChange={(e) => setApiKey(e.target.value)}
                  placeholder="sk-..."
                  className="bg-background/50 border-border hover:border-primary/50 focus:border-primary transition-colors"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="base_url" className="text-foreground font-medium">
                  Base URL
                </Label>
                <Input
                  id="base_url"
                  value={formData.llm_base_url}
                  onChange={(e) => setBaseUrl(e.target.value)}
                  placeholder="https://api.openai.com/v1"
                  className="bg-background/50 border-border hover:border-primary/50 focus:border-primary transition-colors"
                />
                <p className="text-xs text-muted-foreground">
                  切换提供商时会自动填充，可手动修改
                </p>
              </div>
            </>
          )}

          {testResult && (
            <div
              className={`flex items-center gap-2 p-3 rounded-xl transition-all duration-300 ${
                testResult.success
                  ? "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20"
                  : "bg-destructive/10 text-destructive border border-destructive/20"
              }`}
            >
              {testResult.success ? (
                <CheckCircle className="h-4 w-4" />
              ) : (
                <XCircle className="h-4 w-4" />
              )}
              <span className="text-sm font-medium">{testResult.message}</span>
            </div>
          )}
        </CardContent>

        <CardFooter className="flex gap-3 pt-2">
          <Button
            variant="outline"
            onClick={testConnectionAction}
            disabled={isTesting || !formData.llm_api_key}
            className="flex-1 border-border hover:bg-muted hover:border-primary/30 transition-all duration-200"
          >
            {isTesting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            <Zap className="mr-2 h-4 w-4" />
            测试连接
          </Button>
          <Button
            onClick={handleSubmit}
            disabled={isSubmitting || !testResult?.success}
            className="flex-1 bg-gradient-to-r from-primary to-primary/80 hover:from-primary/90 hover:to-primary/70 shadow-lg shadow-primary/25 hover:shadow-xl hover:shadow-primary/30 transition-all duration-200"
          >
            {isSubmitting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            开始使用
          </Button>
        </CardFooter>
      </Card>
    </div>
  );
}
