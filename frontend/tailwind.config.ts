import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./features/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        base: "#0e1117",
        panel: "#161b22",
        border: "#26303d",
        accent: "#ff3b30",
        muted: "#8b98a9",
        ink: "#080D18",
        ink2: "#0D1422",
        card: "#111C2D",
        mint: "#27E08A",
        sky: "#36A3FF",
        mist: "#929DB0",
      },
      fontFamily: {
        sans: ["var(--font-inter)", "Inter", "ui-sans-serif", "system-ui", "sans-serif"],
        mono: ["ui-monospace", "SFMono-Regular", "Menlo", "monospace"],
      },
      keyframes: {
        "fade-up": {
          "0%": { opacity: "0", transform: "translateY(18px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        "line-draw": {
          "0%": { strokeDashoffset: "1200" },
          "100%": { strokeDashoffset: "0" },
        },
        "soft-float": {
          "0%,100%": { transform: "translateY(0)" },
          "50%": { transform: "translateY(-8px)" },
        },
      },
      animation: {
        "fade-up": "fade-up 0.7s cubic-bezier(0.22,1,0.36,1) both",
        "line-draw": "line-draw 2.2s ease-out forwards",
        "soft-float": "soft-float 7s ease-in-out infinite",
      },
    },
  },
  plugins: [],
};

export default config;
