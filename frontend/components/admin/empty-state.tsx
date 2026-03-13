import { LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";

interface EmptyStateProps {
  icon: LucideIcon;
  title: string;
  description?: string;
  className?: string;
}

export function EmptyState({ icon: Icon, title, description, className }: EmptyStateProps) {
  return (
    <div className={cn("h-full flex flex-col items-center justify-center text-muted-foreground p-6 text-center", className)}>
      <div className="h-16 w-16 rounded-2xl bg-muted/50 flex items-center justify-center mb-4 border border-border/50">
        <Icon className="h-8 w-8 opacity-50" />
      </div>
      <p className="font-medium text-foreground text-sm mb-1">{title}</p>
      {description && <p className="text-xs">{description}</p>}
    </div>
  );
}
