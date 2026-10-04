/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['"IBM Plex Sans"', 'system-ui', '-apple-system', 'sans-serif'],
        mono: ['"IBM Plex Mono"', 'monospace'],
      },
      colors: {
        background: '#FAFAF8',
        foreground: '#1C1D21',
        border: '#E4E2DD',
        primary: '#2F5DA8',
        destructive: '#B5472A',
        severity: {
          critical: '#B5472A',
          high: '#C77D3F',
          medium: '#A68B3D',
          low: '#6B7280',
        },
        surface: {
          0: '#FAFAF8',
          1: '#F5F4F1',
          2: '#EEEDEA',
        },
        muted: '#71726E',
      },
      borderRadius: {
        control: '4px',
      },
    },
  },
  plugins: [],
}
