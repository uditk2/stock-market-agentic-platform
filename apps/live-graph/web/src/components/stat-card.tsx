import type { ReactNode } from "react";

import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";

export function StatCard({
  label,
  value,
  hint,
  icon,
  className,
}: {
  label: string;
  value: ReactNode;
  hint?: ReactNode;
  icon?: ReactNode;
  className?: string;
}) {
  return (
    <Card className={cn("gap-0 py-4", className)}>
      <CardContent className="px-4">
        <div className="text-muted-foreground flex items-center gap-1.5 text-xs font-medium">
          {icon}
          {label}
        </div>
        <div className="mt-1.5 text-2xl font-semibold tabular-nums tracking-tight">
          {value}
        </div>
        {hint && <div className="text-muted-foreground mt-0.5 text-xs">{hint}</div>}
      </CardContent>
    </Card>
  );
}
