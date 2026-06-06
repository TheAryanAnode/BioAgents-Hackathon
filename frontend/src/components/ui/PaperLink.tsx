import { cn } from "../../lib/utils";
import { ExternalLink } from "lucide-react";

/** Clickable paper title when a public URL is available. */
export function PaperLink({
  title,
  url,
  className,
  showIcon = true,
}: {
  title: string;
  url?: string | null;
  className?: string;
  showIcon?: boolean;
}) {
  if (url) {
    return (
      <a
        href={url}
        target="_blank"
        rel="noopener noreferrer"
        className={cn(
          "inline-flex items-start gap-1.5 text-accent underline decoration-accent/60 underline-offset-2 transition-opacity hover:opacity-80",
          className,
        )}
        onClick={(e) => e.stopPropagation()}
      >
        <span>{title}</span>
        {showIcon && <ExternalLink size={14} strokeWidth={1.5} className="mt-0.5 shrink-0" />}
      </a>
    );
  }
  return <span className={className}>{title}</span>;
}
