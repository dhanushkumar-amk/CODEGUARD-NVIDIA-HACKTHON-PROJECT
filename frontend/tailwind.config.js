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
        mono: ['"IBM Plex Mono"', 'monospace'],
      },
      colors: {
        paper: '#FDFCF9',
        ink: '#15171C',
        muted: '#6B7280',
        line: '#E7E3DC',
        primary: {
          DEFAULT: '#8069FF',
          hover: '#7057F5',
        },

        // Legacy semantic mappings mapped to primary
        azure: '#8069FF',
        violet: '#8069FF',

        // Functional severity & status colors for Report page only
        coral: '#E0562F',
        emerald: '#1F9D55',
        amber: '#F2A93C',

        // Semantic bindings
        background: '#FDFCF9',
        foreground: '#15171C',
        border: '#E7E3DC',

        surface: {
          0: '#FDFCF9',
          1: '#F7F6F1',
          2: '#EEEAE1',
        },

        severity: {
          critical: '#E0562F',
          high: '#F2A93C',
          medium: '#D48B22',
          low: '#6B7280',
        },
      },
      borderRadius: {
        control: '6px',
      },
      letterSpacing: {
        tracked: '0.08em',
      },
    },
  },
  plugins: [],
}
