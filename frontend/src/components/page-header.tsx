import { useApp } from "@/lib/app-context";
import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

export function PageHeader({
  eyebrow,
  title,
  description,
  actions,
  className,
}: {
  eyebrow?: string;
  title: string;
  description?: string;
  actions?: ReactNode;
  className?: string;
}) {
  const { workspace } = useApp();
  return (
    <div
      className={cn(
        "flex flex-col gap-4 border-b border-border px-4 py-6 md:flex-row md:items-end md:justify-between md:px-8",
        className,
      )}
    >
      <div className="min-w-0">
        <div className="mb-1.5 inline-flex items-center gap-1.5 rounded-full bg-accent px-2.5 py-1 text-xs font-medium text-accent-foreground">
          <span>{workspace.flag}</span>
          {workspace.name}
          {eyebrow && (
            <>
              <span className="text-muted-foreground/50">·</span>
              <span>{eyebrow}</span>
            </>
          )}
        </div>
        <h1 className="font-serif text-3xl font-semibold tracking-tight text-balance md:text-4xl">
          {title}
        </h1>
        {description && (
          <p className="mt-2 max-w-2xl text-pretty leading-relaxed text-muted-foreground">
            {description}
          </p>
        )}
      </div>
      {actions && <div className="flex shrink-0 items-center gap-2">{actions}</div>}
    </div>
  );
}
