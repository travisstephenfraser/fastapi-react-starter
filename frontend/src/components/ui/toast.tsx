import * as React from "react";
import { cn } from "@/lib/utils";

/**
 * Minimal toast. Full shadcn toast stack is heavier; swap in via
 * `make shadcn-add NAME=sonner` when you need queues, positioning, etc.
 */

type ToastVariant = "default" | "destructive";

interface ToastProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: ToastVariant;
  title?: string;
  description?: string;
}

export const Toast = React.forwardRef<HTMLDivElement, ToastProps>(
  ({ className, variant = "default", title, description, ...props }, ref) => (
    <div
      ref={ref}
      role="status"
      className={cn(
        "fixed bottom-4 right-4 z-50 flex max-w-sm flex-col gap-1 rounded-md border p-4 shadow-md",
        variant === "default" && "border-border bg-background text-foreground",
        variant === "destructive" && "border-destructive bg-destructive text-destructive-foreground",
        className,
      )}
      {...props}
    >
      {title ? <div className="text-sm font-semibold">{title}</div> : null}
      {description ? <div className="text-sm opacity-90">{description}</div> : null}
    </div>
  ),
);
Toast.displayName = "Toast";
