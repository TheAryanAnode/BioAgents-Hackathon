import React from "react";
import { cn } from "../../lib/utils";

type Variant = "primary" | "outline" | "ghost";
type Size = "sm" | "default" | "lg";

interface Props extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: Size;
}

const sizePad: Record<Size, string> = {
  sm: "py-2 text-xs gap-2",
  default: "py-3 text-sm gap-2.5",
  lg: "py-4 text-base gap-3",
};

/**
 * Bold Typography buttons. Primary is text-only with an animated accent
 * underline; outline inverts on hover; ghost reveals a thin underline.
 */
export function Button({
  variant = "primary",
  size = "default",
  className,
  children,
  ...rest
}: Props) {
  if (variant === "outline") {
    return (
      <button
        className={cn(
          "group inline-flex items-center justify-center whitespace-nowrap border border-foreground px-6 font-semibold uppercase tracking-wider text-foreground transition-colors duration-150 ease-crisp hover:bg-foreground hover:text-background active:translate-y-px disabled:pointer-events-none disabled:opacity-50",
          sizePad[size],
          className,
        )}
        {...rest}
      >
        {children}
      </button>
    );
  }

  if (variant === "ghost") {
    return (
      <button
        className={cn(
          "group relative inline-flex items-center justify-center whitespace-nowrap px-4 font-semibold uppercase tracking-wider text-muted-foreground transition-colors duration-150 ease-crisp hover:text-foreground active:translate-y-px disabled:pointer-events-none disabled:opacity-50",
          sizePad[size],
          className,
        )}
        {...rest}
      >
        {children}
        <span className="pointer-events-none absolute bottom-1 left-4 right-4 h-px origin-left scale-x-0 bg-foreground transition-transform duration-150 ease-crisp group-hover:scale-x-100" />
      </button>
    );
  }

  return (
    <button
      className={cn(
        "group relative inline-flex items-center justify-center whitespace-nowrap px-0 font-semibold uppercase tracking-wider text-accent transition-colors duration-150 ease-crisp active:translate-y-px disabled:pointer-events-none disabled:opacity-50",
        sizePad[size],
        className,
      )}
      {...rest}
    >
      {children}
      <span className="pointer-events-none absolute bottom-1 left-0 right-0 h-0.5 origin-center scale-x-100 bg-accent transition-transform duration-150 ease-crisp group-hover:scale-x-110" />
    </button>
  );
}
