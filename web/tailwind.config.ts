import type { Config } from "tailwindcss";

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
    },
  },
  plugins: [],
};

export default config;
