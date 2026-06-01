import type { Config } from 'tailwindcss'

export default {
  content: [
    './components/**/*.vue',
    './layouts/**/*.vue',
    './pages/**/*.vue',
    './composables/**/*.ts',
    './server/**/*.ts',
  ],
  theme: {
    extend: {
      colors: {
        surface: {
          DEFAULT: '#ffffff',
          secondary: '#f8f7f4',
        },
        border: {
          DEFAULT: '#e5e2db',
          strong: '#c9c4bc',
        },
        text: {
          primary: '#1a1814',
          secondary: '#6b6560',
          muted: '#9b958e',
        },
        accent: {
          DEFAULT: '#2563eb',
          hover: '#1d4ed8',
        },
        grounded: {
          DEFAULT: '#16a34a',
          light: '#f0fdf4',
        },
        warning: {
          DEFAULT: '#d97706',
          light: '#fffbeb',
        },
      },
      fontFamily: {
        sans: ['Inter Variable', 'Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono Variable', 'JetBrains Mono', 'monospace'],
        prose: ['Lora Variable', 'Lora', 'Georgia', 'serif'],
      },
    },
  },
  plugins: [],
} satisfies Config
