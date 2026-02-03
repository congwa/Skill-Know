"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Home,
  FileText,
  Sparkles,
  Search,
  MessageSquare,
  Settings,
  BookOpen,
} from "lucide-react";
import { cn } from "@/lib/utils";

const navItems = [
  { title: "首页", href: "/admin", icon: Home },
  { title: "技能管理", href: "/admin/skills", icon: Sparkles },
  { title: "文档管理", href: "/admin/documents", icon: FileText },
  { title: "知识搜索", href: "/admin/search", icon: Search },
  { title: "智能对话", href: "/admin/chat", icon: MessageSquare },
  { title: "提示词管理", href: "/admin/prompts", icon: BookOpen },
  { title: "设置", href: "/admin/settings", icon: Settings },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="w-52 bg-sidebar border-r border-sidebar-border flex flex-col">
      {/* Logo */}
      <div className="h-14 flex items-center px-4 border-b border-sidebar-border">
        <Link href="/admin" className="flex items-center gap-2">
          <div className="h-7 w-7 rounded-md bg-foreground flex items-center justify-center">
            <span className="text-background text-xs font-bold">S</span>
          </div>
          <span className="font-semibold text-sm text-foreground tracking-tight">Skill-Know</span>
        </Link>
      </div>

      {/* 导航菜单 */}
      <nav className="flex-1 px-2 py-3 space-y-0.5 overflow-y-auto">
        {navItems.map((item) => {
          const isActive =
            pathname === item.href ||
            (item.href !== "/admin" && pathname.startsWith(item.href));

          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center gap-2.5 px-2.5 py-2 rounded-md text-[13px] transition-colors",
                isActive
                  ? "sidebar-item-selected text-foreground font-medium"
                  : "text-sidebar-foreground list-item-hover hover:text-foreground"
              )}
            >
              <item.icon className="h-4 w-4 shrink-0" />
              <span>{item.title}</span>
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}
