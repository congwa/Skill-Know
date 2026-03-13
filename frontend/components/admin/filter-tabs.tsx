import { cn } from "@/lib/utils";

export interface FilterTab {
  value: string;
  label: string;
  icon?: React.ReactNode;
}

interface FilterTabsProps<T extends string> {
  tabs: readonly FilterTab[] | FilterTab[];
  value: T;
  onChange: (value: T) => void;
  className?: string;
}

export function FilterTabs<T extends string>({ tabs, value, onChange, className }: FilterTabsProps<T>) {
  return (
    <div className={cn("flex gap-1", className)}>
      {tabs.map((tab) => {
        const isActive = value === tab.value;
        return (
          <button
            key={tab.value}
            onClick={() => onChange(tab.value as T)}
            className={cn(
              "flex-1 px-2.5 py-1.5 text-xs rounded-md transition-colors flex items-center justify-center gap-1.5",
              isActive
                ? "bg-primary text-primary-foreground font-medium shadow-sm"
                : "bg-muted/50 text-muted-foreground hover:text-foreground hover:bg-muted"
            )}
          >
            {tab.icon}
            {tab.label}
          </button>
        );
      })}
    </div>
  );
}
