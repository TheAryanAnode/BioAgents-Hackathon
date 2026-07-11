/** SynthesisOS wordmark — accent bar + molecular node motif. */
export function SynthesisLogo({
  size = "md",
  showText = true,
  className = "",
}: {
  size?: "sm" | "md" | "lg" | "hero";
  showText?: boolean;
  className?: string;
}) {
  const iconSize = { sm: 28, md: 36, lg: 48, hero: 64 }[size];
  const textClass = {
    sm: "text-sm",
    md: "text-lg",
    lg: "text-2xl",
    hero: "text-3xl md:text-4xl",
  }[size];

  return (
    <div className={`flex items-center gap-3 ${className}`}>
      <svg
        width={iconSize}
        height={iconSize}
        viewBox="0 0 64 64"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        aria-hidden
      >
        <defs>
          <radialGradient id="sos-glow" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor="#FF3D00" stopOpacity="0.45" />
            <stop offset="100%" stopColor="#FF3D00" stopOpacity="0" />
          </radialGradient>
          <filter id="sos-blur" x="-50%" y="-50%" width="200%" height="200%">
            <feGaussianBlur stdDeviation="2" />
          </filter>
        </defs>
        <circle cx="32" cy="32" r="28" fill="url(#sos-glow)" filter="url(#sos-blur)" />
        <circle cx="32" cy="14" r="6" fill="#FF3D00" />
        <circle cx="16" cy="42" r="5" fill="#FAFAFA" fillOpacity="0.9" />
        <circle cx="48" cy="42" r="5" fill="#FAFAFA" fillOpacity="0.9" />
        <line x1="32" y1="20" x2="19" y2="38" stroke="#FF3D00" strokeWidth="1.5" strokeOpacity="0.6" />
        <line x1="32" y1="20" x2="45" y2="38" stroke="#FF3D00" strokeWidth="1.5" strokeOpacity="0.6" />
        <line x1="21" y1="42" x2="43" y2="42" stroke="#737373" strokeWidth="1" strokeDasharray="3 2" />
        <circle cx="32" cy="32" r="3" fill="#FF3D00" />
      </svg>
      {showText && (
        <span className={`font-sans font-extrabold tracking-tight ${textClass}`}>
          SYNTHESIS<span className="text-accent">OS</span>
        </span>
      )}
    </div>
  );
}
