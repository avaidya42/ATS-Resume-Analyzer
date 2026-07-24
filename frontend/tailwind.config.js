/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        base: "#0B0F14",
        surface: "#121821",
        surface2: "#1A222E",
        border: "#232C3A",
        accent: "#4FD1C5",
        accent2: "#F2A65A",
        muted: "#8494A8",
      },
      fontFamily: {
        mono: ["JetBrains Mono", "ui-monospace", "monospace"],
        sans: ["Inter", "ui-sans-serif", "sans-serif"],
      },
    },
  },
  plugins: [],
}
