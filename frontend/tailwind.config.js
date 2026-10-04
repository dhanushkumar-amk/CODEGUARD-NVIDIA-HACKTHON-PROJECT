/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['"Public Sans"', 'system-ui', '-apple-system', 'sans-serif'],
        serif: ['"Source Serif 4"', 'Georgia', 'serif'],
        mono: ['"IBM Plex Mono"', 'monospace'],
      },
      colors: {
        paper: '#FBFAF7',
        ink: '#14171F',
        line: '#E3DFD6',
        azure: '#2457C5',
        violet: '#6D4AFF',
        amber: '#F2A93C',
        emerald: '#1F9D55',
        coral: '#E0562F',

        // Semantic bindings
        background: '#FBFAF7',
        foreground: '#14171F',
        border: '#E3DFD6',
        primary: '#2457C5',
        destructive: '#E0562F',
        muted: '#6C707A',

        surface: {
          0: '#FBFAF7',
          1: '#F5F3EC',
          2: '#EAE6DC',
        },

        severity: {
          critical: '#E0562F',
          high: '#F2A93C',
          medium: '#D48B22',
          low: '#6C707A',
        },
      },
      borderRadius: {
        control: '4px',
      },
    },
  },
  plugins: [],
}
