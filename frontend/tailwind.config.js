/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        base: {
          900: "#0a0f1f",
          800: "#0f172a",
          700: "#111c3b",
          600: "#152450"
        },
        accent: {
          cyan: "#37e4ff",
          lime: "#9dff75",
          amber: "#ffd166",
          pink: "#ff5c8a",
          violet: "#8b5cf6"
        }
      },
      fontFamily: {
        display: ["Space Grotesk", "ui-sans-serif", "system-ui"],
        mono: ["IBM Plex Mono", "ui-monospace", "SFMono-Regular"]
      },
      boxShadow: {
        glow: "0 0 30px rgba(55, 228, 255, 0.25)"
      }
    }
  },
  plugins: []
};
