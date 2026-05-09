/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx,ts,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        ink: {
          900: "#0b1220",
          800: "#0f172a",
          700: "#1e293b",
          600: "#334155",
        },
        accent: {
          DEFAULT: "#38bdf8",
          dark: "#0284c7",
        },
        sev: {
          critical: "#dc2626",
          high: "#ea580c",
          medium: "#f59e0b",
          low: "#22c55e",
          info: "#64748b",
        },
      },
      fontFamily: {
        mono: ["ui-monospace", "SFMono-Regular", "Menlo", "monospace"],
      },
    },
  },
  plugins: [],
};
