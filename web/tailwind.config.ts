import type { Config } from "tailwindcss";
import tailwindcssAnimate from "tailwindcss-animate";

const config: Config = {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        primary: {
          50: "#FFF0F3",
          100: "#FFD9E2",
          200: "#FFB3C8",
          300: "#FF8DAE",
          400: "#FF6794",
          500: "#FF5B8F",
          600: "#E84A7A",
          700: "#CC3D68",
          800: "#A83056",
          900: "#842344",
        },
        accent: {
          50: "#FFFDE7",
          100: "#FFF9C4",
          200: "#FFF59D",
          300: "#FFF176",
          400: "#FFEE58",
          500: "#FEE971",
          600: "#F5D84A",
          700: "#E0C23A",
        },
        success: {
          50: "#E8F8F0",
          500: "#2ECC71",
          600: "#27AE60",
        },
        warning: {
          50: "#FFF8E1",
          500: "#F39C12",
          600: "#E67E22",
        },
        danger: {
          50: "#FDEDED",
          500: "#E74C3C",
          600: "#C0392B",
        },
        surface: {
          DEFAULT: "#F5F5F5",
          dark: "#1A1A2E",
        },
        card: {
          DEFAULT: "#FFFFFF",
          dark: "#16213E",
        },
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
      },
      transitionTimingFunction: {
        epass: "cubic-bezier(0.16, 1, 0.3, 1)",
        "epass-in-out": "cubic-bezier(0.65, 0, 0.35, 1)",
        "epass-spring": "cubic-bezier(0.34, 1.4, 0.64, 1)",
      },
      boxShadow: {
        "epass-sm": "0 1px 2px 0 rgb(16 24 40 / 0.06), 0 1px 3px 0 rgb(16 24 40 / 0.1)",
        "epass": "0 4px 6px -1px rgb(16 24 40 / 0.07), 0 2px 4px -2px rgb(16 24 40 / 0.05)",
        "epass-md": "0 10px 20px -6px rgb(16 24 40 / 0.1), 0 4px 8px -4px rgb(16 24 40 / 0.06)",
        "epass-lg": "0 20px 32px -10px rgb(16 24 40 / 0.14), 0 8px 16px -8px rgb(16 24 40 / 0.08)",
        "epass-xl": "0 32px 56px -14px rgb(16 24 40 / 0.2), 0 12px 24px -12px rgb(16 24 40 / 0.1)",
        "epass-primary": "0 10px 30px -8px rgb(255 91 143 / 0.45)",
        "epass-primary-lg": "0 18px 44px -10px rgb(255 91 143 / 0.55)",
        "epass-inset": "inset 0 1px 0 0 rgb(255 255 255 / 0.6)",
      },
      keyframes: {
        "epass-fade-in-up": {
          from: { opacity: "0", transform: "translateY(14px)" },
          to: { opacity: "1", transform: "translateY(0)" },
        },
        "epass-fade-in-down": {
          from: { opacity: "0", transform: "translateY(-14px)" },
          to: { opacity: "1", transform: "translateY(0)" },
        },
        "epass-fade-in-left": {
          from: { opacity: "0", transform: "translateX(16px)" },
          to: { opacity: "1", transform: "translateX(0)" },
        },
        "epass-scale-in": {
          from: { opacity: "0", transform: "scale(0.94)" },
          to: { opacity: "1", transform: "scale(1)" },
        },
        "epass-shimmer": {
          "100%": { transform: "translateX(100%)" },
        },
        "epass-glow": {
          "0%, 100%": { boxShadow: "0 0 0 0 rgb(255 91 143 / 0)" },
          "50%": { boxShadow: "0 0 0 6px rgb(255 91 143 / 0.28)" },
        },
        "epass-draw": {
          from: { transform: "scaleX(0)" },
          to: { transform: "scaleX(1)" },
        },
        "epass-draw-y": {
          from: { transform: "scaleY(0)" },
          to: { transform: "scaleY(1)" },
        },
        "epass-float": {
          "0%, 100%": { transform: "translateY(0)" },
          "50%": { transform: "translateY(-6px)" },
        },
        "epass-ring": {
          "0%": { opacity: "0.6", transform: "scale(0.85)" },
          "80%, 100%": { opacity: "0", transform: "scale(1.9)" },
        },
        "epass-spin-slow": {
          to: { transform: "rotate(360deg)" },
        },
        "epass-bar": {
          "0%": { transform: "translateX(-100%) scaleX(0.4)" },
          "50%": { transform: "translateX(0%) scaleX(0.7)" },
          "100%": { transform: "translateX(100%) scaleX(0.4)" },
        },
        "epass-aurora": {
          "0%, 100%": { backgroundPosition: "0% 50%" },
          "50%": { backgroundPosition: "100% 50%" },
        },
        "epass-bounce-in": {
          "0%": { opacity: "0", transform: "scale(0.6)" },
          "60%": { opacity: "1", transform: "scale(1.08)" },
          "100%": { opacity: "1", transform: "scale(1)" },
        },
        "epass-shake": {
          "0%, 100%": { transform: "translateX(0)" },
          "20%, 60%": { transform: "translateX(-5px)" },
          "40%, 80%": { transform: "translateX(5px)" },
        },
      },
      animation: {
        "fade-in-up": "epass-fade-in-up 0.45s cubic-bezier(0.16, 1, 0.3, 1) both",
        "fade-in-down": "epass-fade-in-down 0.45s cubic-bezier(0.16, 1, 0.3, 1) both",
        "fade-in-left": "epass-fade-in-left 0.45s cubic-bezier(0.16, 1, 0.3, 1) both",
        "scale-in": "epass-scale-in 0.35s cubic-bezier(0.34, 1.4, 0.64, 1) both",
        "bounce-in": "epass-bounce-in 0.5s cubic-bezier(0.34, 1.4, 0.64, 1) both",
        "shake": "epass-shake 0.45s cubic-bezier(0.36, 0.07, 0.19, 0.97) both",
        glow: "epass-glow 1.8s cubic-bezier(0.4, 0, 0.6, 1) infinite",
        draw: "epass-draw 0.6s cubic-bezier(0.16, 1, 0.3, 1) both",
        "draw-y": "epass-draw-y 0.6s cubic-bezier(0.16, 1, 0.3, 1) both",
        float: "epass-float 4s ease-in-out infinite",
        ring: "epass-ring 2s cubic-bezier(0, 0, 0.2, 1) infinite",
        "spin-slow": "epass-spin-slow 8s linear infinite",
        bar: "epass-bar 1.4s cubic-bezier(0.4, 0, 0.2, 1) infinite",
        aurora: "epass-aurora 9s ease-in-out infinite",
      },
    },
  },
  plugins: [tailwindcssAnimate],
};

export default config;
