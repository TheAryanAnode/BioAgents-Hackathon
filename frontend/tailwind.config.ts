import type { Config } from "tailwindcss";

/**
 * Bold Typography design system tokens.
 * Type is the hero: sharp edges, restrained palette, extreme scale contrast.
 */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        background: "#0A0A0A",
        foreground: "#FAFAFA",
        muted: "#1A1A1A",
        "muted-foreground": "#737373",
        accent: "#FF3D00",
        "accent-foreground": "#0A0A0A",
        border: "#262626",
        "border-hover": "#404040",
        input: "#1A1A1A",
        card: "#0F0F0F",
        ring: "#FF3D00",
        support: "#34D399",
        contradict: "#F87171",
      },
      fontFamily: {
        sans: ['"Inter Tight"', '"Inter"', "system-ui", "sans-serif"],
        display: ['"Playfair Display"', "Georgia", "serif"],
        mono: ['"JetBrains Mono"', '"Fira Code"', "monospace"],
      },
      fontSize: {
        xs: "0.75rem",
        sm: "0.875rem",
        base: "1rem",
        lg: "1.125rem",
        xl: "1.25rem",
        "2xl": "1.5rem",
        "3xl": "2rem",
        "4xl": "2.5rem",
        "5xl": "3.5rem",
        "6xl": "4.5rem",
        "7xl": "6rem",
        "8xl": "8rem",
        "9xl": "10rem",
      },
      letterSpacing: {
        tighter: "-0.06em",
        tight: "-0.04em",
        normal: "-0.01em",
        wide: "0.05em",
        wider: "0.1em",
        widest: "0.2em",
      },
      lineHeight: {
        none: "1",
        tight: "1.1",
        snug: "1.25",
        normal: "1.6",
        relaxed: "1.75",
      },
      borderRadius: {
        none: "0px",
        DEFAULT: "0px",
      },
      maxWidth: {
        container: "1200px",
      },
      transitionTimingFunction: {
        crisp: "cubic-bezier(0.25, 0, 0, 1)",
      },
      keyframes: {
        "fade-up": {
          "0%": { opacity: "0", transform: "translateY(20px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        "scan-line": {
          "0%": { transform: "translateY(-100%)" },
          "100%": { transform: "translateY(100%)" },
        },
      },
      animation: {
        "fade-up": "fade-up 500ms cubic-bezier(0.25, 0, 0, 1) both",
      },
    },
  },
  plugins: [],
} satisfies Config;
