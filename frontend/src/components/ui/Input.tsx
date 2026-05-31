import React from "react";
import { cn } from "../../lib/utils";

export const Input = React.forwardRef<
  HTMLInputElement,
  React.InputHTMLAttributes<HTMLInputElement>
>(({ className, ...rest }, ref) => {
  return (
    <input
      ref={ref}
      className={cn(
        "h-12 w-full rounded-none border border-border bg-input px-4 text-base text-foreground placeholder:text-muted-foreground transition-colors duration-150 ease-crisp outline-none focus:border-accent disabled:cursor-not-allowed disabled:opacity-50 md:h-14",
        className,
      )}
      {...rest}
    />
  );
});
Input.displayName = "Input";
