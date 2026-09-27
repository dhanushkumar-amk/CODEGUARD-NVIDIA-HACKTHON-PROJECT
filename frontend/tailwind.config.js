/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        background: {
          primary: "#0a0c14",
          secondary: "#101423",
          card: "rgba(22, 27, 46, 0.7)",
        },
        border: {
          subtle: "rgba(255, 255, 255, 0.08)",
          active: "rgba(99, 102, 241, 0.3)",
        },
        accent: {
          cyan: "#06b6d4",
          indigo: "#6366f1",
          emerald: "#10b981",
          rose: "#f43f5e",
          amber: "#f59e0b",
        },
      },
    },
  },
  plugins: [],
}
