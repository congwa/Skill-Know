"use client";

import { usePathname } from "next/navigation";
import { Sidebar } from "@/components/admin/sidebar";
import { SetupGuard } from "@/components/admin/SetupGuard";

export default function AdminLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  const isQuickSetupPage = pathname === "/admin/quick-setup";

  // 快速设置页面不显示侧边栏
  if (isQuickSetupPage) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-background via-background to-primary/5">
        {children}
      </div>
    );
  }

  return (
    <SetupGuard>
      <div className="flex h-screen bg-background">
        <Sidebar />
        <main className="flex-1 overflow-hidden">{children}</main>
      </div>
    </SetupGuard>
  );
}
