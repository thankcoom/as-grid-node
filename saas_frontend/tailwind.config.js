/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        bg: {
          dark: "#0a0a0a",
          primary: "#0d0d0d",
          secondary: "#141414",
          tertiary: "#1a1a1a",
          elevated: "#1e1e1e",
        },
        text: {
          primary: "#ffffff",
          secondary: "#e0e0e0",
          muted: "#808080",
          disabled: "#505050",
        },
        border: {
          DEFAULT: "#2a2a2a",
          light: "#333333",
        },
        status: {
          profit: "#e0e0e0", // Bright White-ish
          loss: "#707070",   // Dark Gray
          on: "#a0a0a0",
          off: "#404040",
        },
        accent: {
          DEFAULT: "#ffffff",
          hover: "#e0e0e0",
        }
      },
      fontFamily: {
        mono: ['Menlo', 'Monaco', 'Consolas', '"Liberation Mono"', '"Courier New"', 'monospace'],
        sans: ['Inter', 'system-ui', 'sans-serif'],
      }
    },
  },
  plugins: [],
}