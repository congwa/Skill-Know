"use client";

import { useEffect, useState } from "react";
import { Settings, Save, Loader2, CheckCircle, XCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { testConnection, type TestConnectionRequest } from "@/lib/api/quick-setup";

export default function SettingsPage() {
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<{ success: boolean; message: string } | null>(null);

  const [formData, setFormData] = useState<TestConnectionRequest>({
    llm_provider: "openai",
    llm_api_key: "",
    llm_base_url: "https://api.openai.com/v1",
    llm_chat_model: "gpt-4o-mini",
  });

  const handleTest = async () => {
    setTesting(true);
    setTestResult(null);
    try {
      const result = await testConnection(formData);
      setTestResult({
        success: result.success,
        message: result.message + (result.latency_ms ? ` (${result.latency_ms}ms)` : ""),
      });
    } catch (error) {
      setTestResult({
        success: false,
        message: error instanceof Error ? error.message : "测试失败",
      });
    } finally {
      setTesting(false);
    }
  };

  return (
    <div className="h-full overflow-auto p-6 bg-background/50">
      <div className="max-w-2xl mx-auto space-y-6">
        {/* Hero 区域 */}
        <div className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-primary/10 via-primary/5 to-accent/10 border border-border/50 p-6">
          <div className="absolute top-0 right-0 w-48 h-48 bg-primary/10 rounded-full blur-3xl -translate-y-1/2 translate-x-1/2" />
          <div className="relative z-10 flex items-center gap-4">
            <div className="h-12 w-12 rounded-xl bg-gradient-to-br from-primary to-primary/80 flex items-center justify-center shadow-lg shadow-primary/25">
              <Settings className="h-6 w-6 text-white" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-foreground">系统设置</h1>
              <p className="text-muted-foreground">管理系统配置和 LLM 连接</p>
            </div>
          </div>
        </div>

        <Card className="bg-card/80 backdrop-blur-sm border-border/50">
          <CardHeader>
            <CardTitle className="text-foreground">LLM 配置</CardTitle>
            <CardDescription>配置 AI 模型连接参数</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="provider" className="text-foreground font-medium">提供商</Label>
              <Input
                id="provider"
                value={formData.llm_provider}
                onChange={(e) => setFormData({ ...formData, llm_provider: e.target.value })}
                placeholder="openai"
                className="bg-background/50 border-border/50 hover:border-primary/30 focus:border-primary/50 transition-colors"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="api_key" className="text-foreground font-medium">API Key</Label>
              <Input
                id="api_key"
                type="password"
                value={formData.llm_api_key}
                onChange={(e) => setFormData({ ...formData, llm_api_key: e.target.value })}
                placeholder="sk-..."
                className="bg-background/50 border-border/50 hover:border-primary/30 focus:border-primary/50 transition-colors"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="base_url" className="text-foreground font-medium">Base URL</Label>
              <Input
                id="base_url"
                value={formData.llm_base_url}
                onChange={(e) => setFormData({ ...formData, llm_base_url: e.target.value })}
                placeholder="https://api.openai.com/v1"
                className="bg-background/50 border-border/50 hover:border-primary/30 focus:border-primary/50 transition-colors"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="model" className="text-foreground font-medium">模型</Label>
              <Input
                id="model"
                value={formData.llm_chat_model}
                onChange={(e) => setFormData({ ...formData, llm_chat_model: e.target.value })}
                placeholder="gpt-4o-mini"
                className="bg-background/50 border-border/50 hover:border-primary/30 focus:border-primary/50 transition-colors"
              />
            </div>

            {testResult && (
              <div className={`flex items-center gap-2 p-3 rounded-xl transition-all duration-300 ${testResult.success ? "bg-emerald-500/10 text-emerald-600 border border-emerald-500/20" : "bg-destructive/10 text-destructive border border-destructive/20"}`}>
                {testResult.success ? <CheckCircle className="h-4 w-4" /> : <XCircle className="h-4 w-4" />}
                <span className="text-sm font-medium">{testResult.message}</span>
              </div>
            )}

            <div className="flex gap-2 pt-2">
              <Button variant="outline" onClick={handleTest} disabled={testing || !formData.llm_api_key} className="hover:bg-primary/10 hover:border-primary/30 hover:text-primary transition-all duration-200">
                {testing && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                测试连接
              </Button>
              <Button disabled={saving || !formData.llm_api_key} className="bg-gradient-to-r from-primary to-primary/80 hover:from-primary/90 hover:to-primary/70 shadow-md shadow-primary/20">
                {saving && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                <Save className="mr-2 h-4 w-4" />
                保存
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
