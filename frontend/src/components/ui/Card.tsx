import React from "react";
import { cn } from "../../lib/utils";

interface Props extends React.HTMLAttributes<HTMLDivElement> {
  bordered?: boolean;
  highlighted?: boolean;
  accentTop?: boolean;
}

/**
 * Minimal container. Depth comes from a hairline border and optional accent
 * top-bar, never shadows. Sharp corners only.
 */
export function Card({
  bordered = true,
  highlighted = false,
  accentTop = false,
  className,
  children,
  ...rest
}: Props) {
  return (
    <div
      className={cn(
        "relative rounded-none bg-transparent p-6 transition-colors duration-150 ease-crisp md:p-8",
        bordered && "border border-border hover:border-border-hover",
        highlighted && "border-2 border-accent",
        className,
      )}
      {...rest}
    >
      {accentTop && (
        <span className="absolute -top-px left-0 h-1 w-16 bg-accent" />
      )}
      {children}
    </div>
  );
}

export function Badge({
  children,
  tone = "muted",
  className,
}: {
  children: React.ReactNode;
  tone?: "muted" | "accent" | "support" | "contradict";
  className?: string;
}) {
  const tones: Record<string, string> = {
    muted: "border-border text-muted-foreground",
    accent: "border-accent text-accent",
    support: "border-support text-support",
    contradict: "border-contradict text-contradict",
  };
  return (
    <span
      className={cn(
        "inline-flex items-center border px-2 py-0.5 font-mono text-[10px] uppercase tracking-widest",
        tones[tone],
        className,
      )}
    >
      {children}
    </span>
  );
}
