import type { Config } from "tailwindcss";
export default {
  darkMode: "class",
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        primary: "#078a70",
        ink: "var(--color-ink)",
        muted: "var(--color-muted)",
        line: "var(--color-line)",
      },
      boxShadow: { card: "0 3px 20px -8px rgba(30, 50, 55, .10)" },
    },
  },
  plugins: [],
} satisfies Config;
