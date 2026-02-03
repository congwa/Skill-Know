"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Loader2 } from "lucide-react";
import { getSetupState } from "@/lib/api/quick-setup";

export default function Home() {
  const router = useRouter();
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function checkSetup() {
      try {
        const state = await getSetupState();
        if (state.essential_completed) {
          router.replace("/admin");
        } else {
          router.replace("/admin/quick-setup");
        }
      } catch (error) {
        console.error("检查设置状态失败:", error);
        router.replace("/admin/quick-setup");
      } finally {
        setLoading(false);
      }
    }
    checkSetup();
  }, [router]);

  if (loading) {
    return (
      <div className="flex h-screen w-full items-center justify-center">
        <div className="text-center space-y-4">
          <Loader2 className="h-8 w-8 animate-spin mx-auto text-zinc-400" />
          <p className="text-sm text-zinc-500">正在加载...</p>
        </div>
      </div>
    );
  }

  return null;
}
