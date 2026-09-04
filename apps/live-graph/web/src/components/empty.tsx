import type { ReactNode } from "react";

/** Says why something is empty, which is usually "not yet", not "broken". */
export function Empty({
  title,
  hint,
  icon,
}: {
  title: string;
  hint?: string;
  icon?: ReactNode;
}) {
  return (
    <div className="text-muted-foreground flex flex-col items-center justify-center gap-2 px-6 py-14 text-center">
      {icon}
      <p className="text-sm font-medium">{title}</p>
      {hint && <p className="max-w-sm text-xs leading-relaxed">{hint}</p>}
    </div>
  );
}
