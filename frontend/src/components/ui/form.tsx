import * as React from "react";
import { cn } from "@/lib/utils";

/**
 * Minimal form primitives. Full shadcn `<Form>` (with react-hook-form + zod)
 * is a bigger pull; add it via `make shadcn-add NAME=form` when a real form
 * surface needs it. These suffice for the `items` example.
 */

export const Form = React.forwardRef<HTMLFormElement, React.FormHTMLAttributes<HTMLFormElement>>(
  ({ className, ...props }, ref) => (
    <form ref={ref} className={cn("flex flex-col gap-3", className)} {...props} />
  ),
);
Form.displayName = "Form";

export const FormField = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div ref={ref} className={cn("flex flex-col gap-1", className)} {...props} />
  ),
);
FormField.displayName = "FormField";

export const FormLabel = React.forwardRef<
  HTMLLabelElement,
  React.LabelHTMLAttributes<HTMLLabelElement>
>(({ className, ...props }, ref) => (
  <label ref={ref} className={cn("text-sm font-medium", className)} {...props} />
));
FormLabel.displayName = "FormLabel";

export const FormError = React.forwardRef<HTMLSpanElement, React.HTMLAttributes<HTMLSpanElement>>(
  ({ className, ...props }, ref) => (
    <span ref={ref} className={cn("text-destructive text-sm", className)} {...props} />
  ),
);
FormError.displayName = "FormError";
