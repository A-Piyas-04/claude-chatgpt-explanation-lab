import type { Config } from "tailwindcss";

/**
 * Visual direction: a research workbench, not a marketing dashboard.
 * A restrained palette with one accent; information density comes from
 * typography and spacing rather than colour and decoration.
 */
const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        canvas: "#fbfbfa",
        surface: "#ffffff",
        ink: {
          DEFAULT: "#1a1a18",
          muted: "#5c5c57",
          faint: "#8a8a82",
        },
        line: {
          DEFAULT: "#e5e4e0",
          strong: "#d2d1cc",
        },
        accent: {
          DEFAULT: "#2f5d50",
          soft: "#eef3f1",
          strong: "#1f423a",
        },
        warn: { DEFAULT: "#8a5a00", soft: "#fdf6e7" },
        danger: { DEFAULT: "#9b2c25", soft: "#fdf0ef" },
        synthetic: { DEFAULT: "#6b21a8", soft: "#f6f0fc" },
      },
      fontFamily: {
        sans: [
          "ui-sans-serif",
          "system-ui",
          "-apple-system",
          "Segoe UI",
          "Inter",
          "Helvetica Neue",
          "Arial",
          "sans-serif",
        ],
        mono: ["ui-monospace", "SFMono-Regular", "Menlo", "Consolas", "monospace"],
        reading: ["Georgia", "Cambria", "Times New Roman", "serif"],
      },
      fontSize: {
        "2xs": ["0.6875rem", { lineHeight: "1rem" }],
      },
      boxShadow: {
        card: "0 1px 2px rgba(26,26,24,0.04), 0 1px 1px rgba(26,26,24,0.03)",
        pop: "0 8px 24px rgba(26,26,24,0.10)",
      },
    },
  },
  plugins: [],
};

export default config;
