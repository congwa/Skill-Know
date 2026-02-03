"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  FileText,
  Sparkles,
  Search,
  MessageSquare,
  ArrowUpRight,
  Activity,
  Cpu,
} from "lucide-react";
import { listSkills } from "@/lib/api/skills";
import { listDocuments } from "@/lib/api/documents";

interface Stats {
  skills: number;
  documents: number;
}

export default function AdminPage() {
  const [stats, setStats] = useState<Stats>({ skills: 0, documents: 0 });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadStats() {
      try {
        const [skillsRes, docsRes] = await Promise.all([
          listSkills({ page_size: 1 }),
          listDocuments({ page_size: 1 }),
        ]);
        setStats({
          skills: skillsRes.total,
          documents: docsRes.total,
        });
      } catch (error) {
        console.error("加载统计失败:", error);
      } finally {
        setLoading(false);
      }
    }
    loadStats();
  }, []);

  const features = [
    {
      title: "技能管理",
      description: "管理系统技能和文档技能",
      icon: Sparkles,
      href: "/admin/skills",
      stat: loading ? "—" : stats.skills,
      statLabel: "个技能",
    },
    {
      title: "文档管理",
      description: "上传和管理知识文档",
      icon: FileText,
      href: "/admin/documents",
      stat: loading ? "—" : stats.documents,
      statLabel: "个文档",
    },
    {
      title: "知识搜索",
      description: "自然语言或 SQL 搜索",
      icon: Search,
      href: "/admin/search",
    },
    {
      title: "智能对话",
      description: "与知识库对话",
      icon: MessageSquare,
      href: "/admin/chat",
    },
  ];

  return (
    <div className="h-full overflow-auto bg-background">
      <div className="max-w-4xl mx-auto px-6 py-8">
        {/* Header */}
        <header className="mb-8">
          <h1 className="text-xl font-semibold text-foreground mb-1">
            欢迎回来
          </h1>
          <p className="text-sm text-muted-foreground">
            Skill-Know 知识库管理系统
          </p>
        </header>

        {/* Stats Grid */}
        <section className="grid grid-cols-4 gap-4 mb-8">
          <div className="col-span-1 p-4 rounded-lg border border-border bg-card">
            <div className="flex items-center gap-2 mb-3">
              <Sparkles className="h-4 w-4 text-muted-foreground" />
              <span className="text-xs text-muted-foreground">技能</span>
            </div>
            <p className="text-2xl font-semibold text-foreground tabular-nums">
              {loading ? "—" : stats.skills}
            </p>
          </div>
          <div className="col-span-1 p-4 rounded-lg border border-border bg-card">
            <div className="flex items-center gap-2 mb-3">
              <FileText className="h-4 w-4 text-muted-foreground" />
              <span className="text-xs text-muted-foreground">文档</span>
            </div>
            <p className="text-2xl font-semibold text-foreground tabular-nums">
              {loading ? "—" : stats.documents}
            </p>
          </div>
          <div className="col-span-1 p-4 rounded-lg border border-border bg-card">
            <div className="flex items-center gap-2 mb-3">
              <Activity className="h-4 w-4 text-muted-foreground" />
              <span className="text-xs text-muted-foreground">状态</span>
            </div>
            <p className="text-sm font-medium text-foreground flex items-center gap-1.5">
              <span className="h-2 w-2 rounded-full bg-emerald-500" />
              正常运行
            </p>
          </div>
          <div className="col-span-1 p-4 rounded-lg border border-border bg-card">
            <div className="flex items-center gap-2 mb-3">
              <Cpu className="h-4 w-4 text-muted-foreground" />
              <span className="text-xs text-muted-foreground">AI</span>
            </div>
            <p className="text-sm font-medium text-foreground flex items-center gap-1.5">
              <span className="h-2 w-2 rounded-full bg-emerald-500" />
              在线
            </p>
          </div>
        </section>

        {/* Features */}
        <section className="mb-8">
          <h2 className="text-xs font-medium text-muted-foreground uppercase tracking-wider mb-3">
            快捷入口
          </h2>
          <div className="grid grid-cols-2 gap-3">
            {features.map((feature) => (
              <Link key={feature.href} href={feature.href} className="group">
                <div className="p-4 rounded-lg border border-border bg-card hover:border-foreground/20 transition-colors">
                  <div className="flex items-start justify-between mb-3">
                    <div className="h-8 w-8 rounded-md bg-muted flex items-center justify-center">
                      <feature.icon className="h-4 w-4 text-foreground" />
                    </div>
                    <ArrowUpRight className="h-4 w-4 text-muted-foreground group-hover:text-foreground transition-colors" />
                  </div>
                  <h3 className="font-medium text-foreground text-sm mb-1">
                    {feature.title}
                  </h3>
                  <p className="text-xs text-muted-foreground mb-2">
                    {feature.description}
                  </p>
                  {feature.stat !== undefined && (
                    <p className="text-lg font-semibold text-foreground tabular-nums">
                      {feature.stat}
                      <span className="text-xs font-normal text-muted-foreground ml-1">
                        {feature.statLabel}
                      </span>
                    </p>
                  )}
                </div>
              </Link>
            ))}
          </div>
        </section>

        {/* Quick Start */}
        <section>
          <h2 className="text-xs font-medium text-muted-foreground uppercase tracking-wider mb-3">
            快速开始
          </h2>
          <div className="rounded-lg border border-border bg-card divide-y divide-border">
            {[
              { step: 1, title: "上传文档", desc: "上传知识文档，系统自动提取内容", href: "/admin/documents" },
              { step: 2, title: "创建技能", desc: "将文档转换为可搜索的技能", href: "/admin/skills" },
              { step: 3, title: "开始搜索", desc: "使用自然语言搜索知识库", href: "/admin/search" },
            ].map((item) => (
              <Link key={item.step} href={item.href} className="group">
                <div className="flex items-center gap-4 p-4 hover:bg-muted/50 transition-colors">
                  <span className="flex h-6 w-6 items-center justify-center rounded text-xs font-medium bg-muted text-muted-foreground">
                    {item.step}
                  </span>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-foreground">{item.title}</p>
                    <p className="text-xs text-muted-foreground">{item.desc}</p>
                  </div>
                  <ArrowUpRight className="h-4 w-4 text-muted-foreground group-hover:text-foreground transition-colors" />
                </div>
              </Link>
            ))}
          </div>
        </section>
      </div>
    </div>
  );
}
