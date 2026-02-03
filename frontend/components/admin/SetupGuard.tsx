"use client";

import { useEffect } from "react";
import { useRouter, usePathname } from "next/navigation";
import { Loader2 } from "lucide-react";
import { useAppStore } from "@/lib/stores";

interface SetupGuardProps {
  children: React.ReactNode;
}

export function SetupGuard({ children }: SetupGuardProps) {
  const router = useRouter();
  const pathname = usePathname();
  const { isSetupComplete, isCheckingSetup, checkSetupStatus } = useAppStore();

  useEffect(() => {
    // 快速设置页面不需要检查
    if (pathname === "/admin/quick-setup") {
      return;
    }

    checkSetupStatus().then((complete) => {
      if (!complete) {
        router.replace("/admin/quick-setup");
      }
    });
  }, [pathname, router, checkSetupStatus]);

  if (isCheckingSetup && pathname !== "/admin/quick-setup") {
    return (
      <div className="flex h-full items-center justify-center bg-zinc-950">
        <div className="flex flex-col items-center gap-4">
          <Loader2 className="h-8 w-8 animate-spin text-zinc-400" />
          <p className="text-sm text-zinc-500">检查配置状态...</p>
        </div>
      </div>
    );
  }

  if (!isSetupComplete && pathname !== "/admin/quick-setup") {
    return null;
  }

  return <>{children}</>;
}
